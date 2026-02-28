"""
Context Window Manager for Ralph AI.

Manages a fixed token budget across 4 buckets:
  - System: system prompt + tool definitions (~2K tokens, fixed)
  - RAG: retrieved document context (~3K tokens, capped)
  - History: conversation history (~8K tokens, managed)
  - Current: new user message + response space (~3K tokens, reserved)

Total budget: ~16K tokens (conservative — works with all Claude models)

Strategy for long conversations:
  1. Always include: system prompt, RAG context, last 3 message pairs, new message
  2. If budget allows: include older messages in full
  3. If budget tight: summarize older messages via Haiku
  4. Emergency: drop RAG before dropping conversation context
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


# ── Minimal AI client adapter ─────────────────────────────────────────────────


class _CompletionResult:
    def __init__(self, content: str) -> None:
        self.content = content


class GatewayAIClient:
    """Thin adapter that calls the AI gateway for Haiku summarisation requests."""

    def __init__(self, gateway_url: str, gateway_key: str) -> None:
        self._url = gateway_url
        self._key = gateway_key

    async def complete(
        self,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int = 200,
        temperature: float = 0.1,
    ) -> _CompletionResult:
        payload = {
            "messages": messages,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "task_type": "summarize_document",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self._url}/v1/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {self._key}"},
                )
                resp.raise_for_status()
                data = resp.json()
                return _CompletionResult(content=data.get("content", ""))
        except Exception as exc:
            logger.warning("context_manager_summarize_failed", error=str(exc))
            raise


# ── Context Window Manager ────────────────────────────────────────────────────


class ContextWindowManager:
    """Fits conversation history, RAG context, and system prompt within a 16K token budget."""

    # Token budget allocation
    TOTAL_BUDGET = 16_000
    SYSTEM_BUDGET = 2_000     # System prompt + tool definitions
    RAG_BUDGET = 3_000        # Retrieved document context
    HISTORY_BUDGET = 8_000    # Conversation history
    CURRENT_BUDGET = 3_000    # New message + response headroom

    # Always keep at least this many recent message pairs
    MIN_RECENT_PAIRS = 3

    def __init__(self, ai_client: GatewayAIClient) -> None:
        self.ai = ai_client
        try:
            import tiktoken
            self._tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self._tokenizer = None  # Fallback to char-based estimation

    def count_tokens(self, text: str) -> int:
        """Count tokens in text. Falls back to char/4 estimate if tiktoken unavailable."""
        if not text:
            return 0
        if self._tokenizer:
            return len(self._tokenizer.encode(text))
        return max(1, len(text) // 4)

    def count_message_tokens(self, message: dict[str, Any]) -> int:
        """Count tokens in a message dict (role + content)."""
        content = message.get("content", "")
        if isinstance(content, list):
            # Handle multi-part content (tool calls, etc.)
            text_parts = [p.get("text", "") for p in content if isinstance(p, dict)]
            content = " ".join(text_parts)
        return self.count_tokens(str(content)) + 4  # +4 for message framing overhead

    async def prepare_context(
        self,
        system_prompt: str,
        tool_definitions: list[dict[str, Any]],
        rag_context: str,
        conversation_history: list[dict[str, Any]],  # [{role, content}, ...] — excludes new message
        new_message: str,
    ) -> list[dict[str, Any]]:
        """Build the messages array for the LLM call, fitting within token budget.

        Returns list[dict] ready for the Claude API / AI gateway.
        """
        messages: list[dict[str, Any]] = []

        # ── 1. System prompt (always included, budget: SYSTEM_BUDGET) ──────────
        system_tokens = self.count_tokens(system_prompt)
        if system_tokens > self.SYSTEM_BUDGET:
            system_prompt = self._truncate_to_tokens(system_prompt, self.SYSTEM_BUDGET)
            system_tokens = self.SYSTEM_BUDGET

        messages.append({"role": "system", "content": system_prompt})

        # Reserve budget for tool definitions (counted but not added as message)
        tool_tokens = self.count_tokens(json.dumps(tool_definitions)) if tool_definitions else 0
        remaining_budget = self.TOTAL_BUDGET - system_tokens - tool_tokens - self.CURRENT_BUDGET

        # ── 2. RAG context (capped at RAG_BUDGET) ───────────────────────────────
        rag_tokens = 0
        if rag_context:
            rag_tokens = self.count_tokens(rag_context)
            if rag_tokens > self.RAG_BUDGET:
                rag_context = self._truncate_to_tokens(rag_context, self.RAG_BUDGET)
                rag_tokens = self.RAG_BUDGET
            messages.append({
                "role": "system",
                "content": f"Relevant documents:\n\n{rag_context}",
            })
            remaining_budget -= rag_tokens

        # ── 3. Conversation history (managed within remaining budget) ────────────
        history_budget = min(remaining_budget, self.HISTORY_BUDGET)

        if conversation_history:
            history_messages = await self._fit_history(conversation_history, history_budget)
            messages.extend(history_messages)

        # ── 4. New user message (always included) ────────────────────────────────
        messages.append({"role": "user", "content": new_message})

        logger.debug(
            "context_prepared",
            total_messages=len(messages),
            rag_tokens=rag_tokens,
            history_len=len(conversation_history),
        )
        return messages

    # ── History fitting ───────────────────────────────────────────────────────

    async def _fit_history(
        self,
        history: list[dict[str, Any]],
        budget: int,
    ) -> list[dict[str, Any]]:
        """Fit conversation history into the token budget.

        Strategy:
        1. Always include last MIN_RECENT_PAIRS pairs (6 messages).
        2. Fill remaining budget with older messages (newest first).
        3. If still over budget, summarise older messages via Haiku.
        """
        if not history:
            return []

        # Split into recent (always keep) and older
        recent_count = self.MIN_RECENT_PAIRS * 2  # pairs → individual messages
        if len(history) > recent_count:
            recent = history[-recent_count:]
            older = history[:-recent_count]
        else:
            recent = history
            older = []

        # Count recent tokens
        recent_tokens = sum(self.count_message_tokens(m) for m in recent)

        if recent_tokens >= budget:
            # Even recent messages exceed budget — keep what fits
            return self._truncate_messages(recent, budget)

        remaining = budget - recent_tokens

        if not older:
            return recent

        # Try to fit older messages in (newest first)
        older_to_include: list[dict[str, Any]] = []
        older_tokens = 0
        for msg in reversed(older):
            msg_tokens = self.count_message_tokens(msg)
            if older_tokens + msg_tokens <= remaining:
                older_to_include.insert(0, msg)
                older_tokens += msg_tokens
            else:
                break

        # If some older messages couldn't fit, summarise them
        unincluded_count = len(older) - len(older_to_include)
        unincluded = older[:unincluded_count]
        if unincluded and (remaining - older_tokens) > 200:
            try:
                summary = await self._summarize_messages(unincluded)
                summary_tokens = self.count_tokens(summary)
                if summary_tokens <= remaining - older_tokens:
                    summary_msg: dict[str, Any] = {
                        "role": "system",
                        "content": f"Earlier conversation summary:\n{summary}",
                    }
                    return [summary_msg] + older_to_include + recent
            except Exception as exc:
                logger.warning("context_summary_failed", error=str(exc))
                # Continue without summary

        return older_to_include + recent

    async def _summarize_messages(self, messages: list[dict[str, Any]]) -> str:
        """Summarise older conversation turns into a concise paragraph using Haiku."""
        formatted: list[str] = []
        for msg in messages:
            role = "User" if msg.get("role") == "user" else "Ralph"
            content = str(msg.get("content", ""))[:500]
            formatted.append(f"{role}: {content}")

        conversation_text = "\n".join(formatted)

        response = await self.ai.complete(
            model="claude-haiku-4-5-20251001",
            messages=[{
                "role": "user",
                "content": (
                    "Summarise this conversation history in 2-3 sentences. "
                    "Focus on: what the user asked about, key findings discussed, "
                    "and any decisions or action items.\n\n"
                    f"{conversation_text[:3000]}"
                ),
            }],
            max_tokens=200,
            temperature=0.1,
        )
        return response.content.strip()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to approximately max_tokens."""
        if self._tokenizer:
            tokens = self._tokenizer.encode(text)
            if len(tokens) <= max_tokens:
                return text
            return self._tokenizer.decode(tokens[:max_tokens])
        # Fallback: char-based
        return text[:max_tokens * 4]

    def _truncate_messages(
        self, messages: list[dict[str, Any]], budget: int
    ) -> list[dict[str, Any]]:
        """Keep most-recent messages that fit within budget."""
        result: list[dict[str, Any]] = []
        total = 0
        for msg in reversed(messages):
            tokens = self.count_message_tokens(msg)
            if total + tokens <= budget:
                result.insert(0, msg)
                total += tokens
            else:
                break
        return result
