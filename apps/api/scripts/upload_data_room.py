#!/usr/bin/env python3
"""Bulk upload script for the SCR Platform data room.

Uploads a local folder of documents directly to S3 and creates the corresponding
Document records in the database. Useful for seeding test data without needing
a running API server.

Usage:
    # Upload all files as unassigned documents
    poetry run python scripts/upload_data_room.py ./sample-docs/

    # Assign to a specific project (fuzzy name match)
    poetry run python scripts/upload_data_room.py ./sample-docs/ --project helios

    # Preview without uploading
    poetry run python scripts/upload_data_room.py ./sample-docs/ --dry-run

    # Specify org and user explicitly
    poetry run python scripts/upload_data_room.py ./sample-docs/ \\
        --org-id 9dc0f325-2526-45b6-b59e-2cdc6e5eeadd \\
        --user-id <user-uuid>

Required env vars (reads from .env in apps/api/):
    DATABASE_URL          PostgreSQL connection string
    AWS_ACCESS_KEY_ID     AWS / MinIO access key
    AWS_SECRET_ACCESS_KEY AWS / MinIO secret key
    AWS_S3_BUCKET         Target bucket (default: scr-staging-documents)
    AWS_S3_REGION         Region (default: eu-north-1)
    AWS_S3_ENDPOINT_URL   Optional: MinIO endpoint for local dev
"""

import argparse
import hashlib
import os
import sys
import uuid
from pathlib import Path

import boto3
import psycopg2
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

# ── Constants ─────────────────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".pptx", ".csv", ".jpg", ".png"}

MIME_TYPE_MAP = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "csv": "text/csv",
    "jpg": "image/jpeg",
    "png": "image/png",
}


# ── Helpers ───────────────────────────────────────────────────────────────────


def load_env():
    """Load .env from apps/api/ directory."""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def get_file_type(path: Path) -> str:
    return path.suffix.lower().lstrip(".")


def format_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    load_env()

    parser = argparse.ArgumentParser(
        description="Bulk upload documents to the SCR Platform data room.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("folder", help="Local folder to upload (supports nested subdirectories)")
    parser.add_argument(
        "--project",
        metavar="NAME",
        help="Project name (fuzzy match) to assign uploaded docs to. Omit for unassigned.",
    )
    parser.add_argument(
        "--category",
        metavar="LABEL",
        default=None,
        help="S3 subfolder label for unassigned docs (default: preserves local subfolder structure)",
    )
    parser.add_argument(
        "--org-id", metavar="UUID", help="Organization UUID (auto-detected if omitted)"
    )
    parser.add_argument(
        "--user-id", metavar="UUID", help="Uploader user UUID (auto-detected if omitted)"
    )
    parser.add_argument("--dry-run", action="store_true", help="List files without uploading")
    args = parser.parse_args()

    folder = Path(args.folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"ERROR: '{folder}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    # ── Config from env ────────────────────────────────────────────────────
    db_url = os.environ.get("DATABASE_URL", "").replace("+asyncpg", "")
    if not db_url:
        print("ERROR: DATABASE_URL env var is required.", file=sys.stderr)
        sys.exit(1)

    aws_bucket = os.environ.get("AWS_S3_BUCKET", "scr-staging-documents")
    aws_region = os.environ.get("AWS_S3_REGION", "eu-north-1")
    aws_endpoint = os.environ.get("AWS_S3_ENDPOINT_URL") or None

    s3 = boto3.client(
        "s3",
        endpoint_url=aws_endpoint,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=aws_region,
        config=BotoConfig(signature_version="s3v4"),
    )

    # ── Database connection ────────────────────────────────────────────────
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
    except Exception as e:
        print(f"ERROR: Cannot connect to database: {e}", file=sys.stderr)
        sys.exit(1)

    # ── Resolve org_id ─────────────────────────────────────────────────────
    org_id = args.org_id
    if not org_id:
        cur.execute("SELECT id FROM organizations LIMIT 1")
        row = cur.fetchone()
        if not row:
            print("ERROR: No organizations found. Run the seed script first.", file=sys.stderr)
            sys.exit(1)
        org_id = str(row[0])
        print(f"Org:  {org_id}")

    # ── Resolve user_id ────────────────────────────────────────────────────
    user_id = args.user_id
    if not user_id:
        cur.execute(
            "SELECT id FROM users WHERE org_id = %s AND is_deleted = FALSE LIMIT 1",
            (org_id,),
        )
        row = cur.fetchone()
        if not row:
            print("ERROR: No users found for this org.", file=sys.stderr)
            sys.exit(1)
        user_id = str(row[0])
        print(f"User: {user_id}")

    # ── Resolve project_id (optional) ─────────────────────────────────────
    project_id = None
    if args.project:
        cur.execute(
            "SELECT id, name FROM projects WHERE org_id = %s AND LOWER(name) LIKE %s AND is_deleted = FALSE LIMIT 1",
            (org_id, f"%{args.project.lower()}%"),
        )
        row = cur.fetchone()
        if row:
            project_id = str(row[0])
            print(f"Project: {row[1]} ({project_id})")
        else:
            print(f"WARNING: No project matching '{args.project}' found — uploading as unassigned.")

    # ── Discover files ─────────────────────────────────────────────────────
    files = sorted(
        p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS
    )

    if not files:
        print(f"No supported files found in {folder}")
        print(f"Supported types: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
        sys.exit(0)

    print(f"\nFound {len(files)} file(s) in {folder}:")
    total_size = 0
    for f in files:
        size = f.stat().st_size
        total_size += size
        print(f"  {f.relative_to(folder)}  ({format_size(size)})")
    print(f"  Total: {format_size(total_size)}")

    if args.dry_run:
        print("\n[DRY RUN] No files were uploaded.")
        cur.close()
        conn.close()
        sys.exit(0)

    # ── Upload ────────────────────────────────────────────────────────────
    print(f"\nUploading to s3://{aws_bucket} ...")
    uploaded, failed = 0, 0

    for file_path in files:
        rel = file_path.relative_to(folder)
        file_type = get_file_type(file_path)
        file_size = file_path.stat().st_size
        checksum = compute_sha256(file_path)
        doc_id = uuid.uuid4()
        file_uuid = uuid.uuid4()
        safe_name = file_path.name.replace("/", "_").replace("\\", "_")
        mime_type = MIME_TYPE_MAP.get(file_type, "application/octet-stream")

        # Build S3 key preserving subfolder structure
        subdir = str(rel.parent) if str(rel.parent) != "." else ""

        if project_id:
            folder_segment = subdir or "root"
            s3_key = f"{org_id}/{project_id}/{folder_segment}/{file_uuid}_{safe_name}"
        else:
            category_segment = args.category or subdir or "unassigned"
            s3_key = f"{org_id}/unassigned/{category_segment}/{file_uuid}_{safe_name}"

        print(f"\n  {rel}  ({format_size(file_size)})")
        print(f"    s3://{aws_bucket}/{s3_key}")

        try:
            # Upload to S3
            with open(file_path, "rb") as fh:
                s3.upload_fileobj(
                    fh,
                    aws_bucket,
                    s3_key,
                    ExtraArgs={"ContentType": mime_type},
                )

            # Create Document record in DB
            cur.execute(
                """
                INSERT INTO documents (
                    id, org_id, project_id, folder_id, name,
                    file_type, mime_type, s3_key, s3_bucket,
                    file_size_bytes, status, version,
                    uploaded_by, checksum_sha256,
                    watermark_enabled, is_deleted,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, NULL, %s,
                    %s, %s, %s, %s,
                    %s, 'processing', 1,
                    %s, %s,
                    FALSE, FALSE,
                    NOW(), NOW()
                )
                """,
                (
                    str(doc_id),
                    org_id,
                    project_id,  # None = unassigned
                    file_path.name,
                    file_type,
                    mime_type,
                    s3_key,
                    aws_bucket,
                    file_size,
                    user_id,
                    checksum,
                ),
            )
            conn.commit()
            uploaded += 1
            print(f"    OK (doc_id={doc_id})")

        except ClientError as e:
            conn.rollback()
            print(f"    S3 ERROR: {e}", file=sys.stderr)
            failed += 1
        except Exception as e:
            conn.rollback()
            print(f"    ERROR: {e}", file=sys.stderr)
            failed += 1

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"\n{'─' * 50}")
    print(f"Uploaded: {uploaded}  Failed: {failed}")
    if uploaded > 0:
        print(
            "\nDocuments are in 'processing' status. The Celery worker will extract them\n"
            "automatically once processing tasks are triggered."
        )

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
