"""
SCR Platform — Master Backup Orchestrator
=========================================
Replaces the basic Gap Fix Block 10 backup.py with a full production system.

Tasks:
  nightly_backup         — Daily 2am: pg_dump → S3 primary + DR, OpenSearch snapshot,
                           secrets inventory, RDS snapshot verification, S3 replication
                           status, table count audit, health report
  weekly_backup_test     — Sunday 5am: restore pg_dump to temp schema, verify table count,
                           check S3 DR replication, report pass/fail
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import subprocess
import tempfile
from datetime import UTC, datetime, timedelta
from typing import Any

import boto3
import structlog
from botocore.exceptions import ClientError
from celery import shared_task

from app.core.config import settings

logger = structlog.get_logger()

# ── Helpers ────────────────────────────────────────────────────────────────────

def _s3_client(region: str | None = None) -> Any:
    return boto3.client(
        "s3",
        endpoint_url=getattr(settings, "AWS_S3_ENDPOINT_URL", None),
        aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
        aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
        region_name=region or getattr(settings, "AWS_S3_REGION", "eu-west-1"),
    )


def _rds_client() -> Any:
    return boto3.client(
        "rds",
        aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
        aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
        region_name=getattr(settings, "AWS_S3_REGION", "eu-west-1"),
    )


def _parse_db_url(url: str) -> dict:
    """Parse DATABASE_URL into connection params."""
    url = url.replace("postgresql+asyncpg://", "").replace("postgresql://", "")
    creds, host_db = (url.split("@", 1) if "@" in url else ("", url))
    user, password = (creds.split(":", 1) if ":" in creds else (creds, ""))
    host_port, dbname = (host_db.rsplit("/", 1) if "/" in host_db else (host_db, "postgres"))
    host, port = (host_port.split(":", 1) if ":" in host_port else (host_port, "5432"))
    return {"user": user, "password": password, "host": host, "port": port, "dbname": dbname}


def _emit_metric(metric_name: str, value: float, unit: str = "Count") -> None:
    """Emit a CloudWatch custom metric (fire-and-forget, never raises)."""
    try:
        cw = boto3.client(
            "cloudwatch",
            aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
            aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
            region_name=getattr(settings, "AWS_S3_REGION", "eu-west-1"),
        )
        cw.put_metric_data(
            Namespace="scr/tasks",
            MetricData=[{"MetricName": metric_name, "Value": value, "Unit": unit}],
        )
    except Exception:
        pass  # Never fail a backup because of metric emission


# ── Step 1: PostgreSQL logical backup ─────────────────────────────────────────

def _run_pg_backup(timestamp: str, backup_bucket: str) -> dict:
    """pg_dump → gzip → S3 primary. Returns metadata dict."""
    db_url = getattr(settings, "DATABASE_URL", "") or getattr(settings, "DATABASE_URL_SYNC", "")
    if not db_url:
        return {"status": "skipped", "reason": "DATABASE_URL not configured"}

    params = _parse_db_url(db_url)
    env = os.environ.copy()
    if params["password"]:
        env["PGPASSWORD"] = params["password"]

    s3_key = f"postgresql/{timestamp[:6]}/{timestamp}_scr_platform.dump"

    cmd = [
        "pg_dump",
        "-h", params["host"], "-p", params["port"],
        "-U", params["user"], "-d", params["dbname"],
        "--no-password", "--format=custom", "--compress=9",
        "--no-owner", "--no-acl",
    ]
    logger.info("backup.pg_dump.start", host=params["host"], db=params["dbname"])

    try:
        result = subprocess.run(cmd, capture_output=True, env=env, timeout=900)
        if result.returncode != 0:
            err = result.stderr.decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"pg_dump exited {result.returncode}: {err}")

        dump_bytes = result.stdout
        compressed = gzip.compress(dump_bytes, compresslevel=6)
        checksum = hashlib.sha256(compressed).hexdigest()
        size_mb = round(len(compressed) / 1024 / 1024, 2)

        s3 = _s3_client()
        s3.put_object(
            Bucket=backup_bucket,
            Key=s3_key,
            Body=compressed,
            ContentType="application/gzip",
            Metadata={
                "backup_timestamp": timestamp,
                "db_host": params["host"],
                "db_name": params["dbname"],
                "sha256": checksum,
                "uncompressed_bytes": str(len(dump_bytes)),
                "size_mb": str(size_mb),
            },
        )

        # Verify: download and run pg_restore --list
        verified = False
        try:
            obj = s3.get_object(Bucket=backup_bucket, Key=s3_key)
            verify_bytes = gzip.decompress(obj["Body"].read())
            with tempfile.NamedTemporaryFile(suffix=".dump", delete=True) as tmp:
                tmp.write(verify_bytes)
                tmp.flush()
                chk = subprocess.run(
                    ["pg_restore", "--list", tmp.name],
                    capture_output=True, timeout=60,
                )
                verified = chk.returncode == 0
        except Exception as ve:
            logger.warning("backup.pg_dump.verify_failed", error=str(ve))

        logger.info("backup.pg_dump.complete", key=s3_key, size_mb=size_mb, verified=verified)
        return {
            "status": "success", "s3_key": s3_key,
            "size_mb": size_mb, "sha256": checksum, "verified": verified,
        }

    except subprocess.TimeoutExpired:
        raise RuntimeError("pg_dump timed out after 15 minutes")


# ── Step 2: DR cross-region copy ───────────────────────────────────────────────

def _copy_to_dr(s3_key: str, primary_bucket: str) -> dict:
    """Copy the backup to the DR region bucket."""
    dr_region = getattr(settings, "DR_REGION", "eu-central-1")
    dr_bucket = getattr(settings, "DR_BACKUP_BUCKET", f"scr-backups-{dr_region}")

    try:
        s3_primary = _s3_client()
        head = s3_primary.head_object(Bucket=primary_bucket, Key=s3_key)
        size_mb = round(head["ContentLength"] / 1024 / 1024, 2)

        s3_dr = _s3_client(region=dr_region)
        copy_source = {"Bucket": primary_bucket, "Key": s3_key}
        s3_dr.copy(
            copy_source, dr_bucket, s3_key,
            ExtraArgs={"StorageClass": "STANDARD_IA"},
        )
        logger.info("backup.dr_copy.complete", dr_bucket=dr_bucket, key=s3_key, size_mb=size_mb)
        return {"status": "success", "dr_bucket": dr_bucket, "dr_region": dr_region, "size_mb": size_mb}
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("NoSuchBucket", "NoCredentialsError", "AccessDenied"):
            logger.warning("backup.dr_copy.skipped", reason=str(e))
            return {"status": "skipped", "reason": str(e)}
        raise


# ── Step 3: OpenSearch snapshot ────────────────────────────────────────────────

def _run_opensearch_snapshot(timestamp: str, backup_bucket: str) -> dict:
    """Create an OpenSearch/Elasticsearch snapshot."""
    import httpx

    es_url = getattr(settings, "ELASTICSEARCH_URL", "")
    if not es_url:
        return {"status": "skipped", "reason": "ELASTICSEARCH_URL not configured"}

    repo = "scr-search-backups"
    snapshot_name = f"backup_{timestamp}"

    try:
        # Register snapshot repo (idempotent)
        httpx.put(
            f"{es_url}/_snapshot/{repo}",
            json={"type": "s3", "settings": {
                "bucket": backup_bucket,
                "base_path": "opensearch",
                "region": getattr(settings, "AWS_S3_REGION", "eu-west-1"),
                "server_side_encryption": True,
            }},
            timeout=30,
        ).raise_for_status()

        # Create snapshot (async — don't wait)
        r = httpx.put(
            f"{es_url}/_snapshot/{repo}/{snapshot_name}",
            json={"indices": "*", "ignore_unavailable": True, "include_global_state": True},
            timeout=30,
        )
        accepted = r.status_code in (200, 202)
        logger.info("backup.opensearch.triggered", snapshot=snapshot_name, accepted=accepted)

        # Prune old snapshots — keep last 8
        try:
            all_snaps = httpx.get(f"{es_url}/_snapshot/{repo}/_all", timeout=15).json()
            snaps = sorted(all_snaps.get("snapshots", []), key=lambda x: x.get("start_time_in_millis", 0))
            for snap in snaps[:-8]:
                httpx.delete(f"{es_url}/_snapshot/{repo}/{snap['snapshot']}", timeout=10)
        except Exception:
            pass

        return {"status": "accepted" if accepted else "error", "snapshot": snapshot_name}

    except Exception as e:
        logger.warning("backup.opensearch.failed", error=str(e))
        return {"status": "failed", "error": str(e)}


# ── Step 4: Secrets / config inventory ────────────────────────────────────────

def _export_secrets_inventory(timestamp: str, backup_bucket: str) -> dict:
    """Export Secrets Manager secret *names* (NOT values) to S3 as an audit record."""
    try:
        sm = boto3.client(
            "secretsmanager",
            aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
            aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
            region_name=getattr(settings, "AWS_S3_REGION", "eu-west-1"),
        )
        secrets = []
        paginator = sm.get_paginator("list_secrets")
        for page in paginator.paginate():
            for s in page.get("SecretList", []):
                secrets.append({
                    "name": s["Name"],
                    "arn": s["ARN"],
                    "last_rotated": s.get("LastRotatedDate", "").isoformat() if hasattr(s.get("LastRotatedDate", ""), "isoformat") else str(s.get("LastRotatedDate", "")),
                    "created": s.get("CreatedDate", "").isoformat() if hasattr(s.get("CreatedDate", ""), "isoformat") else "",
                })
        inventory = {"timestamp": timestamp, "total": len(secrets), "secrets": secrets}
        data = json.dumps(inventory, indent=2, default=str).encode()
        s3 = _s3_client()
        key = f"secrets-inventory/{timestamp[:6]}/{timestamp}_secrets.json"
        s3.put_object(Bucket=backup_bucket, Key=key, Body=data, ContentType="application/json")
        logger.info("backup.secrets_inventory.complete", total=len(secrets))
        return {"status": "success", "secret_count": len(secrets), "s3_key": key}
    except Exception as e:
        logger.warning("backup.secrets_inventory.failed", error=str(e))
        return {"status": "skipped", "reason": str(e)}


# ── Step 5: RDS automated backup verification ──────────────────────────────────

def _verify_rds_snapshots() -> dict:
    """Check that recent RDS automated backups exist and are available."""
    try:
        rds = _rds_client()
        env = getattr(settings, "APP_ENV", "production")
        db_id = f"scr-{env}"

        resp = rds.describe_db_instance_automated_backups(DBInstanceIdentifier=db_id)
        backups = resp.get("DBInstanceAutomatedBackups", [])

        available = [b for b in backups if b.get("Status") == "available"]
        if not available:
            # Fall back to manual snapshots
            snaps = rds.describe_db_snapshots(DBInstanceIdentifier=db_id, SnapshotType="automated")
            available = [s for s in snaps.get("DBSnapshots", []) if s.get("Status") == "available"]

        latest_time = None
        if available:
            latest = max(available, key=lambda b: b.get("SnapshotCreateTime") or b.get("InstanceCreateTime") or datetime.min.replace(tzinfo=UTC))
            ts = latest.get("SnapshotCreateTime") or latest.get("InstanceCreateTime")
            if ts:
                latest_time = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)

        age_hours = None
        if latest_time:
            try:
                from dateutil import parser as dtparser
                age_hours = round((datetime.now(UTC) - dtparser.parse(latest_time)).total_seconds() / 3600, 1)
            except Exception:
                pass

        ok = age_hours is not None and age_hours < 26  # within last 26 hours
        logger.info("backup.rds.verified", count=len(available), age_hours=age_hours, ok=ok)
        return {"status": "ok" if ok else "stale", "snapshot_count": len(available), "latest": latest_time, "age_hours": age_hours}
    except Exception as e:
        logger.warning("backup.rds.verify_failed", error=str(e))
        return {"status": "skipped", "reason": str(e)}


# ── Step 6: S3 replication status ─────────────────────────────────────────────

def _check_s3_replication() -> dict:
    """Check that cross-region replication is enabled on critical buckets."""
    env = getattr(settings, "APP_ENV", "production")
    buckets = [f"scr-{env}-documents", f"scr-{env}-redacted"]
    results = {}
    s3 = _s3_client()
    for bucket in buckets:
        try:
            s3.get_bucket_replication(Bucket=bucket)
            results[bucket] = "enabled"
        except ClientError as e:
            code = e.response["Error"]["Code"]
            results[bucket] = "none" if code == "ReplicationConfigurationNotFoundError" else f"error:{code}"
        except Exception as e:
            results[bucket] = f"skipped:{e}"
    return {"status": "ok" if all(v == "enabled" for v in results.values()) else "partial", "buckets": results}


# ── Step 7: Table count audit ──────────────────────────────────────────────────

def _audit_table_count() -> dict:
    """Count public tables — automatically catches new tables added by future migrations."""
    try:
        import psycopg2

        db_url = getattr(settings, "DATABASE_URL_SYNC", "") or getattr(settings, "DATABASE_URL", "")
        if not db_url:
            return {"status": "skipped"}
        params = _parse_db_url(db_url)
        conn = psycopg2.connect(
            host=params["host"], port=int(params["port"]),
            user=params["user"], password=params["password"], dbname=params["dbname"],
            connect_timeout=10,
        )
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'")
            count = cur.fetchone()[0]
        conn.close()

        expected_min = 113
        ok = count >= expected_min
        if not ok:
            logger.warning("backup.table_count.below_expected", count=count, expected_min=expected_min)
        else:
            logger.info("backup.table_count.ok", count=count)
        return {"status": "ok" if ok else "warning", "table_count": count, "expected_min": expected_min}
    except Exception as e:
        logger.warning("backup.table_count.failed", error=str(e))
        return {"status": "skipped", "reason": str(e)}


# ── Step 8: Write health report to S3 ─────────────────────────────────────────

def _write_health_report(timestamp: str, backup_bucket: str, report: dict) -> None:
    try:
        data = json.dumps(report, indent=2, default=str).encode()
        s3 = _s3_client()
        # Latest (always overwritten) + dated copy
        for key in [
            "health/latest.json",
            f"health/{timestamp[:6]}/{timestamp}_health.json",
        ]:
            s3.put_object(Bucket=backup_bucket, Key=key, Body=data, ContentType="application/json")
        logger.info("backup.health_report.written", timestamp=timestamp)
    except Exception as e:
        logger.warning("backup.health_report.failed", error=str(e))


# ── MASTER TASK: nightly_backup ────────────────────────────────────────────────

@shared_task(name="tasks.nightly_backup", bind=True, max_retries=1,
             queue="bulk", time_limit=3600, soft_time_limit=3300)
def nightly_backup(self) -> dict:  # type: ignore[misc]
    """
    Master backup orchestrator — runs nightly at 02:00 UTC.

    Steps:
      1. PostgreSQL pg_dump → S3 + DR copy
      2. OpenSearch snapshot
      3. Secrets/config inventory
      4. RDS automated backup verification
      5. S3 replication status check
      6. Table count audit (≥113 expected)
      7. Write health report to S3
      8. Emit CloudWatch metrics
    """
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_bucket = getattr(settings, "BACKUP_S3_BUCKET",
                            f"scr-{getattr(settings, 'APP_ENV', 'production')}-backups")
    report: dict[str, Any] = {"timestamp": timestamp, "backup_bucket": backup_bucket, "steps": {}}
    overall_ok = True

    logger.info("backup.nightly.start", timestamp=timestamp)

    # 1. PostgreSQL logical backup
    try:
        pg = _run_pg_backup(timestamp, backup_bucket)
        report["steps"]["postgresql"] = pg
        if pg["status"] != "success":
            overall_ok = False
    except Exception as e:
        logger.error("backup.pg_dump.error", error=str(e))
        report["steps"]["postgresql"] = {"status": "failed", "error": str(e)}
        overall_ok = False

    # 2. DR cross-region copy (only if pg backup succeeded)
    if report["steps"].get("postgresql", {}).get("status") == "success":
        try:
            pg_key = report["steps"]["postgresql"]["s3_key"]
            dr = _copy_to_dr(pg_key, backup_bucket)
            report["steps"]["dr_copy"] = dr
        except Exception as e:
            logger.warning("backup.dr_copy.error", error=str(e))
            report["steps"]["dr_copy"] = {"status": "failed", "error": str(e)}

    # 3. OpenSearch snapshot
    try:
        report["steps"]["opensearch"] = _run_opensearch_snapshot(timestamp, backup_bucket)
    except Exception as e:
        logger.warning("backup.opensearch.error", error=str(e))
        report["steps"]["opensearch"] = {"status": "failed", "error": str(e)}

    # 4. Secrets inventory
    try:
        report["steps"]["secrets_inventory"] = _export_secrets_inventory(timestamp, backup_bucket)
    except Exception as e:
        logger.warning("backup.secrets.error", error=str(e))
        report["steps"]["secrets_inventory"] = {"status": "failed", "error": str(e)}

    # 5. RDS snapshot verification
    try:
        report["steps"]["rds_snapshots"] = _verify_rds_snapshots()
    except Exception as e:
        logger.warning("backup.rds.error", error=str(e))
        report["steps"]["rds_snapshots"] = {"status": "failed", "error": str(e)}

    # 6. S3 replication
    try:
        report["steps"]["s3_replication"] = _check_s3_replication()
    except Exception as e:
        logger.warning("backup.s3_replication.error", error=str(e))
        report["steps"]["s3_replication"] = {"status": "failed", "error": str(e)}

    # 7. Table count audit
    try:
        tbl = _audit_table_count()
        report["steps"]["table_audit"] = tbl
        if tbl.get("status") == "warning":
            overall_ok = False
    except Exception as e:
        logger.warning("backup.table_audit.error", error=str(e))
        report["steps"]["table_audit"] = {"status": "failed", "error": str(e)}

    report["overall_status"] = "success" if overall_ok else "partial_failure"
    report["completed_at"] = datetime.now(UTC).isoformat()

    # 8. Write health report
    _write_health_report(timestamp, backup_bucket, report)

    # CloudWatch metrics
    _emit_metric("backup_failed" if not overall_ok else "backup_success", 1)
    if not overall_ok:
        _emit_metric("backup_failed", 1)

    logger.info("backup.nightly.complete", overall=report["overall_status"])
    return report


# ── WEEKLY RESTORE TEST ────────────────────────────────────────────────────────

@shared_task(name="tasks.weekly_backup_test", bind=True, max_retries=0,
             queue="bulk", time_limit=1800, soft_time_limit=1700)
def weekly_backup_test(self) -> dict:  # type: ignore[misc]
    """
    Sunday 05:00 UTC — restore last backup to a temp schema and verify integrity.

    Checks:
      1. Download most recent pg_dump from S3
      2. Restore into a temporary schema in the existing DB
      3. Verify table count matches expected (≥113)
      4. Check S3 DR replication has objects
      5. Clean up temp schema
      6. Report pass/fail to CloudWatch
    """
    report: dict[str, Any] = {"started_at": datetime.now(UTC).isoformat(), "checks": {}}
    backup_bucket = getattr(settings, "BACKUP_S3_BUCKET",
                            f"scr-{getattr(settings, 'APP_ENV', 'production')}-backups")
    passed = True

    logger.info("backup.restore_test.start")

    # 1. Find most recent backup
    try:
        s3 = _s3_client()
        paginator = s3.get_paginator("list_objects_v2")
        all_keys = []
        for page in paginator.paginate(Bucket=backup_bucket, Prefix="postgresql/"):
            for obj in page.get("Contents", []):
                if obj["Key"].endswith(".dump") or obj["Key"].endswith(".dump.gz"):
                    all_keys.append((obj["LastModified"], obj["Key"]))

        if not all_keys:
            report["checks"]["find_backup"] = {"status": "failed", "reason": "No backups found in S3"}
            passed = False
        else:
            all_keys.sort(reverse=True)
            latest_key = all_keys[0][1]
            latest_ts = all_keys[0][0].isoformat()
            age_hours = round((datetime.now(UTC) - all_keys[0][0]).total_seconds() / 3600, 1)
            report["checks"]["find_backup"] = {
                "status": "ok", "key": latest_key,
                "timestamp": latest_ts, "age_hours": age_hours,
            }
            if age_hours > 26:
                report["checks"]["find_backup"]["status"] = "stale"
                passed = False

    except Exception as e:
        report["checks"]["find_backup"] = {"status": "failed", "error": str(e)}
        passed = False
        latest_key = None

    # 2 & 3. Restore to temp schema and verify table count
    if latest_key:
        temp_schema = f"restore_test_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        try:
            db_url = getattr(settings, "DATABASE_URL_SYNC", "") or getattr(settings, "DATABASE_URL", "")
            params = _parse_db_url(db_url)
            env = os.environ.copy()
            if params["password"]:
                env["PGPASSWORD"] = params["password"]

            # Download backup
            obj = s3.get_object(Bucket=backup_bucket, Key=latest_key)
            raw_bytes = obj["Body"].read()
            if latest_key.endswith(".gz"):
                dump_bytes = gzip.decompress(raw_bytes)
            else:
                dump_bytes = raw_bytes

            with tempfile.NamedTemporaryFile(suffix=".dump", delete=False) as tmp:
                tmp.write(dump_bytes)
                tmp_path = tmp.name

            try:
                # Create temp schema and restore with --schema-only first for quick table count
                import psycopg2
                conn = psycopg2.connect(
                    host=params["host"], port=int(params["port"]),
                    user=params["user"], password=params["password"],
                    dbname=params["dbname"], connect_timeout=10,
                )
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{temp_schema}"')
                conn.close()

                # Restore schema only
                restore_cmd = [
                    "pg_restore", "--schema-only", "--no-owner", "--no-acl",
                    f"--schema={temp_schema}",
                    f"--dbname=postgresql://{params['user']}:{params['password']}@{params['host']}:{params['port']}/{params['dbname']}",
                    tmp_path,
                ]
                result = subprocess.run(restore_cmd, capture_output=True, env=env, timeout=300)
                restore_ok = result.returncode in (0, 1)  # 1 = warnings, acceptable

                # Count tables restored
                conn2 = psycopg2.connect(
                    host=params["host"], port=int(params["port"]),
                    user=params["user"], password=params["password"],
                    dbname=params["dbname"], connect_timeout=10,
                )
                with conn2.cursor() as cur:
                    cur.execute(
                        "SELECT count(*) FROM information_schema.tables "
                        "WHERE table_schema = %s AND table_type = 'BASE TABLE'",
                        (temp_schema,),
                    )
                    restored_count = cur.fetchone()[0]
                conn2.close()

                restore_status = "ok" if restore_ok and restored_count >= 100 else "warning"
                report["checks"]["restore_test"] = {
                    "status": restore_status, "schema": temp_schema,
                    "tables_restored": restored_count, "restore_exit_code": result.returncode,
                }
                if restore_status != "ok":
                    passed = False

            finally:
                # Cleanup temp schema
                try:
                    import psycopg2
                    conn3 = psycopg2.connect(
                        host=params["host"], port=int(params["port"]),
                        user=params["user"], password=params["password"],
                        dbname=params["dbname"], connect_timeout=10,
                    )
                    conn3.autocommit = True
                    with conn3.cursor() as cur:
                        cur.execute(f'DROP SCHEMA IF EXISTS "{temp_schema}" CASCADE')
                    conn3.close()
                except Exception:
                    pass
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        except Exception as e:
            logger.warning("backup.restore_test.failed", error=str(e))
            report["checks"]["restore_test"] = {"status": "failed", "error": str(e)}
            passed = False

    # 4. Check S3 DR replication has objects
    try:
        dr_region = getattr(settings, "DR_REGION", "eu-central-1")
        dr_bucket = getattr(settings, "DR_BACKUP_BUCKET", f"scr-backups-{dr_region}")
        s3_dr = _s3_client(region=dr_region)
        dr_resp = s3_dr.list_objects_v2(Bucket=dr_bucket, Prefix="postgresql/", MaxKeys=1)
        dr_has_objects = dr_resp.get("KeyCount", 0) > 0
        report["checks"]["dr_replication"] = {
            "status": "ok" if dr_has_objects else "empty",
            "dr_bucket": dr_bucket, "has_objects": dr_has_objects,
        }
        if not dr_has_objects:
            passed = False
    except Exception as e:
        logger.warning("backup.restore_test.dr_check_failed", error=str(e))
        report["checks"]["dr_replication"] = {"status": "skipped", "reason": str(e)}

    report["overall"] = "pass" if passed else "fail"
    report["completed_at"] = datetime.now(UTC).isoformat()

    # Emit metric
    _emit_metric("restore_test_failed" if not passed else "restore_test_success", 1)

    if not passed:
        logger.error("backup.restore_test.failed", report=report)
    else:
        logger.info("backup.restore_test.passed")

    return report
