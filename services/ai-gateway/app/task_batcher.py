"""
Task Batcher for small Haiku calls.

Groups multiple same-type tasks into batched LLM calls to reduce latency and cost.
Only batches Haiku tasks — Sonnet tasks always run individually for quality.

Usage:
    results = await batcher.batch_complete("classify_document", [
        {"filename": "report.pdf", "document_preview": "..."},
        {"filename": "contract.pdf", "document_preview": "..."},
    ])
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import structlog

logger = structlog.get_logger()

# Tasks eligible for batching (all Haiku tasks with small JSON outputs)
BATCHABLE_TASKS: frozenset[str] = frozenset({
    "classify_document",
    "extract_kpis",
    "summarize_document",
    "explain_match",
    "insurance_risk_impact",
    "risk_monitoring_analysis",
})

MAX_BATCH_SIZE = 8  # Quality degrades beyond this


class _CompletionResult:
    """Minimal result wrapper matching the gateway response shape."""
    def __init__(self, content: str, validated_data: dict[str, Any] | None = None) -> None:
        self.content = content
        self.validated_data = validated_data


class TaskBatcher:
    """Batches multiple small Haiku tasks into combined LLM calls."""

    def __init__(self, llm_client: Any, prompt_registry: Any | None = None) -> None:
        self.llm = llm_client
        self.registry = prompt_registry

    async def batch_complete(
        self,
        task_type: str,
        contexts: list[dict[str, Any]],
        max_batch_size: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Process multiple tasks of the same type in batched LLM calls.

        Args:
            task_type: Must be in BATCHABLE_TASKS for batching; otherwise processed individually.
            contexts: List of context dicts, one per task.
            max_batch_size: Override default batch size.

        Returns:
            List of result dicts in the same order as input contexts.
        """
        if not contexts:
            return []

        batch_size = max_batch_size or MAX_BATCH_SIZE

        # Non-batchable or single item → individual calls
        if task_type not in BATCHABLE_TASKS or len(contexts) == 1:
            return await self._process_individually(task_type, contexts)

        # Split into batches
        batches = [contexts[i:i + batch_size] for i in range(0, len(contexts), batch_size)]

        # Process batches concurrently
        batch_coros = [
            self._process_batch(task_type, batch, idx)
            for idx, batch in enumerate(batches)
        ]
        batch_results = await asyncio.gather(*batch_coros, return_exceptions=True)

        # Flatten, falling back to individual calls on batch failure
        all_results: list[dict[str, Any]] = []
        for idx, result in enumerate(batch_results):
            if isinstance(result, Exception):
                logger.warning(
                    "batch_failed_falling_back",
                    task_type=task_type,
                    batch_idx=idx,
                    error=str(result),
                )
                individual = await self._process_individually(task_type, batches[idx])
                all_results.extend(individual)
            else:
                all_results.extend(result)  # type: ignore[arg-type]

        return all_results

    async def _process_batch(
        self,
        task_type: str,
        batch: list[dict[str, Any]],
        batch_idx: int,
    ) -> list[dict[str, Any]]:
        """Execute one batch of tasks in a single LLM call."""
        task_prompts: list[str] = []
        system_prompt: str | None = None

        for i, context in enumerate(batch):
            if self.registry:
                try:
                    messages, _, _ = await self.registry.render(task_type, context)
                    user_msg = next(
                        (m["content"] for m in messages if m["role"] == "user"), None
                    )
                    if user_msg:
                        task_prompts.append(f"TASK {i + 1}:\n{user_msg}")
                        # Extract system prompt from first context only
                        if system_prompt is None:
                            sys_msgs = [m for m in messages if m["role"] == "system"]
                            if sys_msgs:
                                system_prompt = sys_msgs[0]["content"]
                        continue
                except Exception:
                    pass
            task_prompts.append(f"TASK {i + 1}:\n{json.dumps(context, default=str)}")

        combined_prompt = (
            f"Process these {len(batch)} tasks. For each task, provide a JSON result.\n"
            f"Respond with ONLY a JSON array of {len(batch)} objects, one per task, in order.\n"
            f"Example: [{{\"key\": \"value for task 1\"}}, {{\"key\": \"value for task 2\"}}]\n\n"
            + "\n\n---\n\n".join(task_prompts)
        )

        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": combined_prompt})

        response = await self.llm.complete(
            model="claude-haiku-4-5-20251001",
            messages=messages,
            temperature=0.1,
            max_tokens=4096,
            task_type=task_type,
        )

        results = self._parse_batch_response(response.content, len(batch))

        if len(results) != len(batch):
            raise ValueError(
                f"Batch {batch_idx}: expected {len(batch)} results, got {len(results)}"
            )

        logger.info(
            "batch_completed",
            task_type=task_type,
            batch_size=len(batch),
            batch_idx=batch_idx,
        )
        return results

    def _parse_batch_response(
        self, response_text: str, expected_count: int
    ) -> list[dict[str, Any]]:
        """Parse a JSON array response from a batched LLM call using 4 strategies."""

        # Strategy 1: Direct JSON parse
        try:
            parsed = json.loads(response_text)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

        # Strategy 2: Strip markdown fences
        cleaned = re.sub(r"```(?:json)?\s*", "", response_text)
        cleaned = re.sub(r"```\s*$", "", cleaned).strip()
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

        # Strategy 3: Extract first [...] block
        match = re.search(r"\[[\s\S]*\]", response_text)
        if match:
            try:
                parsed = json.loads(match.group())
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass

        # Strategy 4: Extract individual top-level {...} objects
        objects: list[dict[str, Any]] = []
        # Match top-level objects (non-nested)
        depth = 0
        start = -1
        for i, ch in enumerate(response_text):
            if ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and start != -1:
                    try:
                        obj = json.loads(response_text[start:i + 1])
                        objects.append(obj)
                    except json.JSONDecodeError:
                        pass
                    start = -1

        if len(objects) == expected_count:
            return objects

        logger.warning(
            "batch_parse_failed",
            expected=expected_count,
            found=len(objects),
            preview=response_text[:200],
        )
        return []  # Caller will trigger fallback

    async def _process_individually(
        self,
        task_type: str,
        contexts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Process tasks one-by-one (fallback path or for non-batchable tasks)."""
        results: list[dict[str, Any]] = []
        model = "claude-haiku-4-5-20251001" if task_type in BATCHABLE_TASKS else "claude-sonnet-4-20250514"

        for context in contexts:
            try:
                if self.registry:
                    messages, _, _ = await self.registry.render(task_type, context)
                else:
                    messages = [{"role": "user", "content": json.dumps(context, default=str)}]

                response = await self.llm.complete(
                    model=model,
                    messages=messages,
                    task_type=task_type,
                )

                if getattr(response, "validated_data", None):
                    results.append(response.validated_data)
                else:
                    try:
                        results.append(json.loads(response.content))
                    except json.JSONDecodeError:
                        results.append({
                            "error": "Failed to parse response",
                            "raw": response.content[:200],
                        })
            except Exception as exc:
                logger.error("individual_task_failed", task_type=task_type, error=str(exc))
                results.append({"error": str(exc)})

        return results
