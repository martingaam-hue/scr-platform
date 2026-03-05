"""Market Data Enrichment — Celery tasks for scheduled and on-demand data fetching."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime

import structlog
from celery import shared_task
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session as SyncSession

logger = structlog.get_logger()

CONFIDENCE_THRESHOLD = 0.75  # Below this → flag for DataReviewQueue


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    name="market_enrichment.fetch_tier1_source",
)
def fetch_tier1_source(
    self,
    source_id: str,
    org_id: str,
    fetch_log_id: str | None = None,
) -> None:
    """Fetch data from Tier-1 Official API sources."""
    from app.core.config import settings
    from app.models.market_enrichment import (
        MarketDataRaw,
        MarketDataSource,
        MarketEnrichmentFetchLog,
    )

    engine = create_engine(settings.DATABASE_URL_SYNC)

    try:
        import httpx

        with SyncSession(engine) as db:
            source = db.get(MarketDataSource, uuid.UUID(source_id))
            if not source or not source.is_active:
                logger.warning("market_enrichment_source_not_found", source_id=source_id)
                return

            # Update fetch log status to running
            log_id = uuid.UUID(fetch_log_id) if fetch_log_id else None
            if log_id:
                log = db.get(MarketEnrichmentFetchLog, log_id)
                if log:
                    log.status = "running"
                    log.started_at = datetime.now(tz=UTC)
                    db.commit()

            # Fetch from source URL
            headers = source.config.get("headers", {})
            params = source.config.get("params", {})
            url = source.base_url or ""

            if not url:
                logger.warning("market_enrichment_no_url", source_id=source_id)
                return

            try:
                response = httpx.get(url, headers=headers, params=params, timeout=30.0)
                response.raise_for_status()
                raw_data = (
                    response.json()
                    if "json" in response.headers.get("content-type", "")
                    else {"text": response.text}
                )
            except Exception as fetch_exc:
                if log_id:
                    log = db.get(MarketEnrichmentFetchLog, log_id)
                    if log:
                        log.status = "failed"
                        log.error_message = str(fetch_exc)
                        log.completed_at = datetime.now(tz=UTC)
                        db.commit()
                raise self.retry(exc=fetch_exc) from fetch_exc

            # Normalise to list of records
            records = raw_data if isinstance(raw_data, list) else [raw_data]
            field_mappings = source.config.get("field_mappings", {})

            new_count = 0
            for record in records:
                # Apply field mappings if configured
                if field_mappings:
                    mapped = {
                        target: record.get(src)
                        for src, target in field_mappings.items()
                        if record.get(src) is not None
                    }
                    if mapped:
                        record = {**record, **mapped}

                content_hash = hashlib.sha256(
                    json.dumps(record, sort_keys=True, default=str).encode()
                ).hexdigest()

                # Dedup check
                existing = db.execute(
                    select(MarketDataRaw).where(
                        MarketDataRaw.org_id == source.org_id,
                        MarketDataRaw.source_id == source.id,
                        MarketDataRaw.content_hash == content_hash,
                    )
                ).scalar_one_or_none()

                if existing:
                    continue

                raw_record = MarketDataRaw(
                    org_id=source.org_id,
                    source_id=source.id,
                    fetch_log_id=log_id,
                    raw_content=record,
                    content_hash=content_hash,
                    fetched_at=datetime.now(tz=UTC),
                )
                db.add(raw_record)
                db.flush()
                new_count += 1

                # Queue AI extraction for new records
                extract_structured_data.delay(str(raw_record.id), org_id)

            # Update fetch log
            if log_id:
                log = db.get(MarketEnrichmentFetchLog, log_id)
                if log:
                    log.status = "success"
                    log.records_fetched = len(records)
                    log.records_new = new_count
                    log.completed_at = datetime.now(tz=UTC)

            db.commit()
            logger.info(
                "market_enrichment_tier1_done",
                source_id=source_id,
                fetched=len(records),
                new=new_count,
            )

    except Exception as exc:
        logger.error("market_enrichment_tier1_failed", source_id=source_id, error=str(exc))
        raise self.retry(exc=exc) from exc
    finally:
        engine.dispose()


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    name="market_enrichment.fetch_tier2_rss",
)
def fetch_tier2_rss(
    self,
    source_id: str,
    org_id: str,
    fetch_log_id: str | None = None,
) -> None:
    """Fetch and parse RSS/Atom feeds (Tier 2)."""
    from app.core.config import settings
    from app.models.market_enrichment import (
        MarketDataProcessed,
        MarketDataRaw,
        MarketDataSource,
        MarketEnrichmentFetchLog,
    )

    engine = create_engine(settings.DATABASE_URL_SYNC)

    try:
        import httpx

        with SyncSession(engine) as db:
            source = db.get(MarketDataSource, uuid.UUID(source_id))
            if not source or not source.is_active:
                return

            log_id = uuid.UUID(fetch_log_id) if fetch_log_id else None
            if log_id:
                log = db.get(MarketEnrichmentFetchLog, log_id)
                if log:
                    log.status = "running"
                    log.started_at = datetime.now(tz=UTC)
                    db.commit()

            url = source.base_url or ""
            if not url:
                return

            try:
                response = httpx.get(url, timeout=30.0)
                response.raise_for_status()
                feed_text = response.text
            except Exception as fetch_exc:
                if log_id:
                    log = db.get(MarketEnrichmentFetchLog, log_id)
                    if log:
                        log.status = "failed"
                        log.error_message = str(fetch_exc)
                        log.completed_at = datetime.now(tz=UTC)
                        db.commit()
                raise self.retry(exc=fetch_exc) from fetch_exc

            # Parse RSS/Atom
            entries = _parse_rss_feed(feed_text)
            new_count = 0

            for entry in entries:
                content_hash = hashlib.sha256(
                    json.dumps(entry, sort_keys=True, default=str).encode()
                ).hexdigest()

                existing = db.execute(
                    select(MarketDataRaw).where(
                        MarketDataRaw.org_id == source.org_id,
                        MarketDataRaw.source_id == source.id,
                        MarketDataRaw.content_hash == content_hash,
                    )
                ).scalar_one_or_none()

                if existing:
                    continue

                raw_record = MarketDataRaw(
                    org_id=source.org_id,
                    source_id=source.id,
                    fetch_log_id=log_id,
                    raw_content=entry,
                    content_hash=content_hash,
                    fetched_at=datetime.now(tz=UTC),
                )
                db.add(raw_record)
                db.flush()

                # RSS feeds: store as "news" type directly
                processed = MarketDataProcessed(
                    org_id=source.org_id,
                    raw_id=raw_record.id,
                    data_type="news",
                    category=source.config.get("category", "general"),
                    value_text=entry.get("title", ""),
                    value_json={"summary": entry.get("summary"), "link": entry.get("link")},
                    source_url=entry.get("link"),
                    confidence=0.9,
                    review_status="auto_accepted",
                )
                db.add(processed)
                new_count += 1

            if log_id:
                log = db.get(MarketEnrichmentFetchLog, log_id)
                if log:
                    log.status = "success"
                    log.records_fetched = len(entries)
                    log.records_new = new_count
                    log.completed_at = datetime.now(tz=UTC)

            db.commit()
            logger.info(
                "market_enrichment_tier2_done",
                source_id=source_id,
                fetched=len(entries),
                new=new_count,
            )

    except Exception as exc:
        logger.error("market_enrichment_tier2_failed", source_id=source_id, error=str(exc))
        raise self.retry(exc=exc) from exc
    finally:
        engine.dispose()


def _parse_rss_feed(feed_text: str) -> list[dict]:
    """Parse RSS/Atom feed XML into a list of entry dicts."""
    try:
        import xml.etree.ElementTree as ET

        root = ET.fromstring(feed_text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = []

        # Atom feed
        for entry in root.findall("atom:entry", ns):
            entries.append(
                {
                    "title": entry.findtext("atom:title", namespaces=ns),
                    "summary": entry.findtext("atom:summary", namespaces=ns),
                    "link": entry.find("atom:link", ns).get("href")
                    if entry.find("atom:link", ns) is not None
                    else None,
                    "published": entry.findtext("atom:published", namespaces=ns),
                }
            )

        # RSS 2.0
        if not entries:
            for item in root.iter("item"):
                entries.append(
                    {
                        "title": item.findtext("title"),
                        "summary": item.findtext("description"),
                        "link": item.findtext("link"),
                        "published": item.findtext("pubDate"),
                    }
                )

        return entries
    except Exception:
        return []


@shared_task(
    bind=True,
    max_retries=1,
    default_retry_delay=30,
    name="market_enrichment.extract_structured_data",
)
def extract_structured_data(self, raw_id: str, org_id: str) -> None:
    """Use AI Gateway to extract structured fields from raw data."""
    from app.core.config import settings
    from app.models.market_enrichment import DataReviewQueue, MarketDataProcessed, MarketDataRaw

    engine = create_engine(settings.DATABASE_URL_SYNC)

    try:
        import httpx

        with SyncSession(engine) as db:
            raw = db.get(MarketDataRaw, uuid.UUID(raw_id))
            if not raw:
                return

            content_str = json.dumps(raw.raw_content, default=str)[:3000]

            try:
                response = httpx.post(
                    f"{settings.AI_GATEWAY_URL}/v1/completions",
                    json={
                        "prompt": (
                            "Extract structured market data from the following content. "
                            "Return JSON with fields: data_type (price/policy/project_pipeline/macro_indicator/news), "
                            "category (e.g. solar_ppi, capacity_factor, feed_in_tariff), "
                            "region, technology, effective_date (YYYY-MM-DD), "
                            "value_numeric, unit (e.g. USD/MWh, MW, %), confidence (0.0-1.0).\n\n"
                            f"Content:\n{content_str}"
                        ),
                        "task_type": "analysis",
                        "max_tokens": 500,
                        "temperature": 0.1,
                    },
                    headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
                    timeout=120.0,
                )
                response.raise_for_status()
                ai_result = response.json()
                content = ai_result.get("content", {})
                if isinstance(content, str):
                    try:
                        content = json.loads(content)
                    except Exception:
                        content = {}
            except Exception as ai_exc:
                logger.warning(
                    "market_enrichment_ai_extract_failed", raw_id=raw_id, error=str(ai_exc)
                )
                content = {}

            confidence = float(content.get("confidence", 0.5))
            review_status = (
                "auto_accepted" if confidence >= CONFIDENCE_THRESHOLD else "pending_review"
            )

            processed = MarketDataProcessed(
                org_id=raw.org_id,
                raw_id=raw.id,
                data_type=content.get("data_type", "news"),
                category=content.get("category", "unclassified"),
                region=content.get("region"),
                technology=content.get("technology"),
                effective_date=_parse_date(content.get("effective_date")),
                value_numeric=content.get("value_numeric"),
                unit=content.get("unit"),
                confidence=confidence,
                review_status=review_status,
            )
            db.add(processed)
            db.flush()

            # Flag low-confidence records for review
            if review_status == "pending_review":
                queue_item = DataReviewQueue(
                    org_id=raw.org_id,
                    processed_id=processed.id,
                    priority=1 if confidence < 0.5 else 0,
                    reason=f"Low AI confidence: {confidence:.2f}",
                )
                db.add(queue_item)

            db.commit()
            logger.info(
                "market_enrichment_extracted",
                raw_id=raw_id,
                confidence=confidence,
                review_status=review_status,
            )

    except Exception as exc:
        logger.error("market_enrichment_extract_failed", raw_id=raw_id, error=str(exc))
        raise self.retry(exc=exc) from exc
    finally:
        engine.dispose()


def _parse_date(value: str | None):
    if not value:
        return None
    try:
        from datetime import date as _date

        return _date.fromisoformat(value[:10])
    except Exception:
        return None


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name="market_enrichment.run_scheduled_fetches",
)
def run_scheduled_fetches(
    self,
    org_id: str | None = None,
    tier: int | None = None,
) -> None:
    """Fan-out: dispatch per-source fetch tasks for all active sources."""
    from app.core.config import settings
    from app.models.market_enrichment import MarketDataSource

    engine = create_engine(settings.DATABASE_URL_SYNC)

    try:
        with SyncSession(engine) as db:
            stmt = select(MarketDataSource).where(MarketDataSource.is_active.is_(True))
            if org_id:
                stmt = stmt.where(MarketDataSource.org_id == uuid.UUID(org_id))
            if tier:
                stmt = stmt.where(MarketDataSource.tier == tier)

            sources = db.execute(stmt).scalars().all()
            dispatched = 0

            for source in sources:
                fetch_tier1_source.apply_async(
                    kwargs={
                        "source_id": str(source.id),
                        "org_id": str(source.org_id),
                    }
                ) if source.tier == 1 else fetch_tier2_rss.apply_async(
                    kwargs={
                        "source_id": str(source.id),
                        "org_id": str(source.org_id),
                    }
                )
                dispatched += 1

            logger.info(
                "market_enrichment_scheduled_dispatched",
                tier=tier,
                dispatched=dispatched,
            )

    except Exception as exc:
        logger.error("market_enrichment_scheduled_failed", error=str(exc))
        raise self.retry(exc=exc) from exc
    finally:
        engine.dispose()
