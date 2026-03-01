"""Database and S3 backup tasks."""
from __future__ import annotations

import gzip
import io
import os
import subprocess
from datetime import datetime, timedelta, timezone

import boto3
import structlog
from celery import shared_task

from app.core.config import settings

logger = structlog.get_logger()


def _parse_db_url(url: str) -> dict:
    """Parse DATABASE_URL into pg_dump parameters."""
    # postgresql+asyncpg://user:pass@host:port/dbname
    url = url.replace("postgresql+asyncpg://", "").replace("postgresql://", "")
    if "@" in url:
        creds, host_db = url.split("@", 1)
        user, password = creds.split(":", 1) if ":" in creds else (creds, "")
    else:
        user, password, host_db = "", "", url
    if "/" in host_db:
        host_port, dbname = host_db.rsplit("/", 1)
    else:
        host_port, dbname = host_db, "postgres"
    if ":" in host_port:
        host, port = host_port.split(":", 1)
    else:
        host, port = host_port, "5432"
    return {"user": user, "password": password, "host": host, "port": port, "dbname": dbname}


@shared_task(name="tasks.backup_database", bind=True, max_retries=2)
def backup_database_task(self) -> dict:
    """
    Dump PostgreSQL database and upload to S3.

    Scheduled daily at 03:00 UTC.
    Retention: 30 days (managed by S3 lifecycle policy).
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_key = f"backups/db/{timestamp}_scr_platform.sql.gz"

    db_url = getattr(settings, "DATABASE_URL", "")
    if not db_url:
        logger.error("backup.no_db_url")
        return {"status": "skipped", "reason": "DATABASE_URL not set"}

    s3_bucket = getattr(settings, "AWS_S3_BUCKET", "scr-documents")

    params = _parse_db_url(db_url)

    env = os.environ.copy()
    if params["password"]:
        env["PGPASSWORD"] = params["password"]

    pg_dump_cmd = [
        "pg_dump",
        "-h", params["host"],
        "-p", params["port"],
        "-U", params["user"],
        "-d", params["dbname"],
        "--no-password",
        "--format=plain",
        "--no-owner",
        "--no-acl",
    ]

    try:
        result = subprocess.run(
            pg_dump_cmd,
            capture_output=True,
            env=env,
            timeout=600,  # 10 minute timeout
        )
        if result.returncode != 0:
            error_msg = result.stderr.decode("utf-8", errors="replace")[:500]
            logger.error("backup.pg_dump_failed", error=error_msg)
            raise RuntimeError(f"pg_dump failed: {error_msg}")

        sql_bytes = result.stdout

        # Gzip compress
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(sql_bytes)
        compressed = buf.getvalue()

        # Upload to S3
        s3 = boto3.client(
            "s3",
            endpoint_url=getattr(settings, "AWS_S3_ENDPOINT_URL", None),
            aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
            aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
            region_name=getattr(settings, "AWS_S3_REGION", "us-east-1"),
        )
        s3.put_object(
            Bucket=s3_bucket,
            Key=backup_key,
            Body=compressed,
            ContentType="application/gzip",
            Metadata={
                "backup_timestamp": timestamp,
                "db_name": params["dbname"],
                "uncompressed_bytes": str(len(sql_bytes)),
            },
        )

        size_mb = len(compressed) / (1024 * 1024)
        logger.info(
            "backup.completed",
            key=backup_key,
            size_mb=round(size_mb, 2),
            uncompressed_mb=round(len(sql_bytes) / (1024 * 1024), 2),
        )
        return {
            "status": "success",
            "key": backup_key,
            "size_mb": round(size_mb, 2),
            "timestamp": timestamp,
        }

    except subprocess.TimeoutExpired:
        logger.error("backup.timeout")
        raise self.retry(countdown=300, exc=RuntimeError("pg_dump timed out"))
    except Exception as exc:
        logger.error("backup.failed", error=str(exc))
        raise self.retry(countdown=300, exc=exc)


@shared_task(name="tasks.prune_old_backups")
def prune_old_backups_task(retention_days: int = 30) -> dict:
    """
    Delete backups older than retention_days from S3.

    Scheduled weekly on Sunday at 04:00 UTC.
    """
    s3_bucket = getattr(settings, "AWS_S3_BUCKET", "scr-documents")

    s3 = boto3.client(
        "s3",
        endpoint_url=getattr(settings, "AWS_S3_ENDPOINT_URL", None),
        aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
        aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
        region_name=getattr(settings, "AWS_S3_REGION", "us-east-1"),
    )

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

    deleted = 0
    try:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=s3_bucket, Prefix="backups/db/"):
            for obj in page.get("Contents", []):
                last_modified = obj["LastModified"]
                # Ensure timezone-aware for comparison
                if last_modified.tzinfo is None:
                    last_modified = last_modified.replace(tzinfo=timezone.utc)
                if last_modified < cutoff:
                    s3.delete_object(Bucket=s3_bucket, Key=obj["Key"])
                    deleted += 1
                    logger.info("backup.pruned", key=obj["Key"])
    except Exception as exc:
        logger.error("backup.prune_failed", error=str(exc))
        return {"status": "error", "error": str(exc)}

    logger.info("backup.prune_complete", deleted=deleted, retention_days=retention_days)
    return {"status": "success", "deleted": deleted}
