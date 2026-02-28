"""Celery tasks for Legal Document generation and AI review."""

import uuid

import structlog
from celery import Celery

from app.core.config import settings

logger = structlog.get_logger()

celery_app = Celery("legal", broker=settings.CELERY_BROKER_URL)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def generate_legal_doc_task(
    self,
    doc_id: str,
    org_id: str,
    user_id: str,
) -> dict:
    """Generate a legal document from questionnaire answers using AI + upload to S3."""
    import time

    import httpx
    import boto3
    from botocore.config import Config as BotoConfig
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as SyncSession

    from app.models.legal import LegalDocument
    from app.modules.legal.templates import SYSTEM_TEMPLATES

    engine = create_engine(settings.DATABASE_URL_SYNC)
    doc_uuid = uuid.UUID(doc_id)
    start_time = time.time()

    with SyncSession(engine) as session:
        doc = session.get(LegalDocument, doc_uuid)
        if not doc:
            return {"status": "error", "detail": "Document not found"}

        meta = dict(doc.metadata_ or {})

        try:
            meta["generation_status"] = "generating"
            doc.metadata_ = meta
            session.commit()

            template_id = meta.get("template_id", "")
            answers = meta.get("questionnaire_answers", {})
            template = next((t for t in SYSTEM_TEMPLATES if t["id"] == template_id), None)

            template_text = template["template_text"] if template else "Legal Document\n\n[Content to be generated]"
            template_name = template["name"] if template else "Legal Document"

            # Fill in template placeholders with answers
            filled_template = template_text
            for key, value in answers.items():
                if isinstance(value, bool):
                    filled_template = filled_template.replace(f"{{{{{key}}}}}", "Yes" if value else "No")
                elif value is not None:
                    filled_template = filled_template.replace(f"{{{{{key}}}}}", str(value))

            system_prompt = (
                "You are a professional legal drafter specialising in investment and corporate law. "
                "You will receive a partial legal document template with some sections pre-filled. "
                "Complete the document with professional, legally sound language. "
                "Ensure the document is complete, coherent, and enforceable. "
                "Do not add a preamble — output only the document text."
            )
            user_prompt = (
                f"Complete this {template_name} document. "
                f"Replace any [AI will complete...] sections with proper legal text.\n\n"
                f"DOCUMENT:\n{filled_template}\n\n"
                f"Output the complete, professional legal document."
            )

            # Try PromptRegistry for legal_document_completion prompt
            _legal_gen_messages: list[dict] = []
            try:
                import asyncio as _asyncio
                from app.services.prompt_registry import PromptRegistry as _PR
                from app.core.database import async_session_factory as _asf

                async def _render_legal_gen() -> tuple:
                    async with _asf() as _adb:
                        return await _PR(_adb).render(
                            "legal_document_completion",
                            {
                                "template_name": template_name,
                                "document": filled_template[:6000],
                            },
                        )

                _lg_loop = _asyncio.new_event_loop()
                try:
                    _legal_gen_messages, _, _ = (
                        _lg_loop.run_until_complete(_render_legal_gen())
                    )
                finally:
                    _lg_loop.close()
            except Exception:
                pass  # fall back to hardcoded prompts

            _legal_gen_payload: dict = {
                "task_type": "legal_document_completion" if _legal_gen_messages else "analysis",
                "max_tokens": 4096,
                "temperature": 0.2,
            }
            if _legal_gen_messages:
                _legal_gen_payload["messages"] = _legal_gen_messages
            else:
                _legal_gen_payload["system"] = system_prompt
                _legal_gen_payload["prompt"] = user_prompt
            response = httpx.post(
                f"{settings.AI_GATEWAY_URL}/v1/completions",
                json=_legal_gen_payload,
                headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("content") or data.get("text") or filled_template
            model_used = data.get("model", "claude-sonnet-4")

            # Build simple HTML document
            html_content = (
                f"<!DOCTYPE html><html><head>"
                f"<meta charset='UTF-8'>"
                f"<style>body{{font-family:Georgia,serif;max-width:800px;margin:60px auto;line-height:1.7;"
                f"color:#1a1a1a;font-size:12pt;}}"
                f"h1{{font-size:16pt;text-align:center;margin-bottom:8px;}}"
                f"p{{margin-bottom:12px;white-space:pre-wrap;}}</style>"
                f"</head><body>"
                f"<h1>{doc.title}</h1>"
                f"<p>{content.replace(chr(10), '</p><p>')}</p>"
                f"</body></html>"
            )
            html_bytes = html_content.encode("utf-8")

            # Upload to S3
            s3 = boto3.client(
                "s3",
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION,
                config=BotoConfig(signature_version="s3v4"),
            )
            s3_key = f"{org_id}/legal/{doc_id}.html"
            s3.put_object(
                Bucket=settings.AWS_S3_BUCKET,
                Key=s3_key,
                Body=html_bytes,
                ContentType="text/html",
            )

            elapsed_ms = int((time.time() - start_time) * 1000)
            doc.content = content[:5000]  # store preview in content field
            doc.s3_key = s3_key
            meta["generation_status"] = "completed"
            meta["model_used"] = model_used
            meta["processing_time_ms"] = elapsed_ms
            doc.metadata_ = meta
            session.commit()

            logger.info("legal_doc_generated", doc_id=doc_id, elapsed_ms=elapsed_ms)
            return {"status": "success", "doc_id": doc_id}

        except Exception as exc:
            session.rollback()
            with SyncSession(engine) as err_session:
                err_doc = err_session.get(LegalDocument, doc_uuid)
                if err_doc:
                    err_meta = dict(err_doc.metadata_ or {})
                    err_meta["generation_status"] = "failed"
                    err_meta["error"] = str(exc)[:500]
                    err_doc.metadata_ = err_meta
                    err_session.commit()

            logger.error("legal_doc_generation_failed", doc_id=doc_id, error=str(exc))
            raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def review_legal_doc_task(
    self,
    task_log_id: str,
    org_id: str,
    document_id: str | None,
    document_text: str | None,
    mode: str,
    jurisdiction: str,
) -> dict:
    """AI review of a legal document."""
    import time

    import httpx
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as SyncSession

    from app.models.ai import AITaskLog
    from app.models.enums import AITaskStatus
    from app.models.legal import LegalDocument

    engine = create_engine(settings.DATABASE_URL_SYNC)
    task_log_uuid = uuid.UUID(task_log_id)
    start_time = time.time()

    with SyncSession(engine) as session:
        task_log = session.get(AITaskLog, task_log_uuid)
        if not task_log:
            return {"status": "error"}

        try:
            task_log.status = AITaskStatus.PROCESSING
            session.commit()

            # Get document text
            doc_text = document_text or ""
            if document_id and not doc_text:
                doc = session.get(LegalDocument, uuid.UUID(document_id))
                if doc:
                    doc_text = doc.content

            mode_descriptions = {
                "comprehensive": "Perform a full clause-by-clause analysis",
                "risk_focused": "Focus on high-risk clauses and missing protections",
                "compliance": "Check against regulatory requirements for the given jurisdiction",
                "negotiation": "Identify negotiation leverage points and suggest alternatives",
            }
            mode_desc = mode_descriptions.get(mode, mode_descriptions["risk_focused"])

            system_prompt = (
                "You are a senior legal counsel specialising in investment law and corporate transactions. "
                f"{mode_desc}. Jurisdiction: {jurisdiction}. "
                "Respond ONLY with valid JSON matching the schema provided."
            )
            user_prompt = (
                f"Review this legal document and respond with JSON:\n\n"
                f"DOCUMENT:\n{doc_text[:8000]}\n\n"
                f"Respond with this exact JSON structure:\n"
                f'{{"overall_risk_score": <0-100>, "summary": "<2-3 sentences>", '
                f'"clause_analyses": [{{"clause_type": "...", "text_excerpt": "...", '
                f'"risk_level": "low|medium|high|critical", "issue": "...", "recommendation": "..."}}], '
                f'"missing_clauses": ["..."], "jurisdiction_issues": ["..."], "recommendations": ["..."]}}'
            )

            # Try PromptRegistry for legal_document_review prompt
            _legal_rev_messages: list[dict] = []
            try:
                import asyncio as _asyncio
                from app.services.prompt_registry import PromptRegistry as _PR
                from app.core.database import async_session_factory as _asf

                async def _render_legal_rev() -> tuple:
                    async with _asf() as _adb:
                        return await _PR(_adb).render(
                            "legal_document_review",
                            {
                                "document": doc_text[:8000],
                                "mode": mode,
                                "mode_description": mode_desc,
                                "jurisdiction": jurisdiction,
                            },
                        )

                _lr_loop = _asyncio.new_event_loop()
                try:
                    _legal_rev_messages, _, _ = (
                        _lr_loop.run_until_complete(_render_legal_rev())
                    )
                finally:
                    _lr_loop.close()
            except Exception:
                pass  # fall back to hardcoded prompts

            _legal_rev_payload: dict = {
                "task_type": "legal_document_review" if _legal_rev_messages else "analysis",
                "max_tokens": 3000,
                "temperature": 0.1,
            }
            if _legal_rev_messages:
                _legal_rev_payload["messages"] = _legal_rev_messages
            else:
                _legal_rev_payload["system"] = system_prompt
                _legal_rev_payload["prompt"] = user_prompt
            response = httpx.post(
                f"{settings.AI_GATEWAY_URL}/v1/completions",
                json=_legal_rev_payload,
                headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("content") or data.get("text") or "{}"
            model_used = data.get("model", "claude-sonnet-4")

            # Parse JSON with markdown fallback
            import json
            import re
            try:
                output = json.loads(content)
            except json.JSONDecodeError:
                match = re.search(r"\{.*\}", content, re.DOTALL)
                output = json.loads(match.group()) if match else {}

            elapsed_ms = int((time.time() - start_time) * 1000)
            task_log.status = AITaskStatus.COMPLETED
            task_log.output_data = output
            task_log.model_used = model_used
            task_log.processing_time_ms = elapsed_ms
            session.commit()

            logger.info("legal_review_completed", task_log_id=task_log_id, elapsed_ms=elapsed_ms)
            return {"status": "success"}

        except Exception as exc:
            session.rollback()
            with SyncSession(engine) as err_session:
                err_log = err_session.get(AITaskLog, task_log_uuid)
                if err_log:
                    err_log.status = AITaskStatus.FAILED
                    err_log.error_message = str(exc)[:1000]
                    err_session.commit()

            logger.error("legal_review_failed", task_log_id=task_log_id, error=str(exc))
            raise self.retry(exc=exc)
