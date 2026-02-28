"""Ralph AI — agentic loop with tool use and streaming support."""

import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai import AIMessage
from app.models.enums import AIMessageRole
from app.modules.ralph_ai import service
from app.modules.ralph_ai.context_manager import ContextWindowManager, GatewayAIClient
from app.modules.ralph_ai.tools import RALPH_TOOL_DEFINITIONS, RalphTools

logger = structlog.get_logger()

RALPH_SYSTEM_PROMPT = """You are Ralph, the AI analyst for SCR Platform — the premier investment intelligence platform connecting impact project developers ("Allies") with professional investors ("Investors").

You are a sophisticated financial analyst and investment advisor. Your role is to help users understand their projects, portfolios, and investment opportunities by querying the platform's data and providing clear, actionable insights.

## Your Capabilities
You have access to tools that let you:
- Retrieve project details, signal scores, risk assessments, and valuations
- Analyze portfolio metrics and performance
- Search through documents using semantic search
- Find investor-project matches
- Calculate carbon credits, tax credits, and equity scenarios
- Generate report sections and analysis
- Provide risk mitigation strategies and legal document reviews

## Asset Classes You Cover
- Renewable Energy: Solar, Wind, Hydro, Geothermal, Biomass
- Infrastructure: Transportation, Utilities, Telecoms
- Real Estate: Commercial, Residential, Mixed-Use
- Digital Assets: Blockchain, Tokenized Assets
- Impact Investing: ESG-aligned, SDG-focused projects
- Climate Finance: Carbon markets, green bonds, sustainability-linked instruments

## Communication Style
- Be concise and data-driven — lead with numbers and facts
- When you retrieve data, explain what it means in context
- Proactively surface risks and opportunities the user may not have asked about
- Use markdown formatting for clarity (tables, bullet points, bold for key metrics)
- Always cite which data source or tool you used
- If data is unavailable, say so clearly and suggest alternatives

## Guidelines
- Always operate within the user's organization context (multi-tenant)
- For financial projections, clearly state assumptions
- Recommend consulting legal/financial professionals for binding decisions
- Never fabricate data — if a tool returns an error, acknowledge it
"""

MAX_TOOL_ITERATIONS = 10


class RalphAgent:
    """Tool-using agentic loop for Ralph AI."""

    def __init__(self) -> None:
        self._gateway_url = settings.AI_GATEWAY_URL
        self._gateway_key = settings.AI_GATEWAY_API_KEY
        _ai_client = GatewayAIClient(self._gateway_url, self._gateway_key)
        self.context_manager = ContextWindowManager(_ai_client)

    async def process_message(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user_content: str,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> tuple[AIMessage, AIMessage]:
        """
        Run the full agentic loop synchronously.
        Returns (user_message, assistant_message).
        """
        # 1. Save user message
        user_msg = await service.append_message(
            db, conversation_id, AIMessageRole.USER, user_content
        )

        # 2. Build context-managed message history
        # history includes the just-saved user message as last entry; exclude it for context manager
        full_history = await service.get_conversation_messages(db, conversation_id)
        prior_history = full_history[:-1] if full_history and full_history[-1].role == AIMessageRole.USER else full_history
        messages = await self.context_manager.prepare_context(
            system_prompt=RALPH_SYSTEM_PROMPT,
            tool_definitions=RALPH_TOOL_DEFINITIONS,
            rag_context="",  # RAG available via tools
            conversation_history=_history_to_dicts(prior_history),
            new_message=user_content,
        )

        # 3. Agentic loop
        tools_instance = RalphTools(db=db, org_id=org_id)
        all_tool_calls: list[dict[str, Any]] = []
        all_tool_results: list[dict[str, Any]] = []
        final_content = ""
        model_used = "claude-sonnet-4-20250514"
        tokens_in = 0
        tokens_out = 0

        for _iteration in range(MAX_TOOL_ITERATIONS):
            result = await _call_gateway_with_tools(
                gateway_url=self._gateway_url,
                gateway_key=self._gateway_key,
                messages=messages,
                tools=RALPH_TOOL_DEFINITIONS,
            )

            model_used = result.get("model_used", model_used)
            usage = result.get("usage", {})
            tokens_in += usage.get("prompt_tokens", 0)
            tokens_out += usage.get("completion_tokens", 0)
            stop_reason = result.get("stop_reason", "end_turn")

            if stop_reason == "tool_calls" or result.get("tool_calls"):
                tool_calls = result["tool_calls"]
                all_tool_calls.extend(tool_calls)

                # Build assistant message with tool calls for context
                assistant_turn: dict[str, Any] = {
                    "role": "assistant",
                    "content": result.get("content") or "",
                    "tool_calls": tool_calls,
                }
                messages.append(assistant_turn)

                # Execute each tool
                for tc in tool_calls:
                    fn_name = tc["function"]["name"]
                    try:
                        fn_args = json.loads(tc["function"]["arguments"])
                    except (json.JSONDecodeError, KeyError):
                        fn_args = {}

                    logger.info("ralph_tool_call", tool=fn_name, args=fn_args)
                    tool_result = await tools_instance.execute(fn_name, fn_args)
                    all_tool_results.append({"tool": fn_name, "result": tool_result})

                    # Append tool result message
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps(tool_result),
                    })

            else:
                # end_turn — save final response
                final_content = result.get("content", "")
                break

        # 4. Save assistant message
        assistant_msg = await service.append_message(
            db,
            conversation_id,
            AIMessageRole.ASSISTANT,
            final_content,
            tool_calls={"calls": all_tool_calls} if all_tool_calls else None,
            tool_results={"results": all_tool_results} if all_tool_results else None,
            model_used=model_used,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )

        return user_msg, assistant_msg

    async def process_message_stream(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user_content: str,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Stream the agentic response.
        Phase 1: Tool calls (yield tool events, no streaming)
        Phase 2: Stream final response tokens
        Phase 3: Save to DB, yield done event
        """
        # Save user message
        user_msg = await service.append_message(
            db, conversation_id, AIMessageRole.USER, user_content
        )
        yield {"type": "user_message", "message_id": str(user_msg.id)}

        # Build message history
        full_history = await service.get_conversation_messages(db, conversation_id)
        prior_history = full_history[:-1] if full_history and full_history[-1].role == AIMessageRole.USER else full_history
        messages = await self.context_manager.prepare_context(
            system_prompt=RALPH_SYSTEM_PROMPT,
            tool_definitions=RALPH_TOOL_DEFINITIONS,
            rag_context="",  # RAG available via tools
            conversation_history=_history_to_dicts(prior_history),
            new_message=user_content,
        )

        tools_instance = RalphTools(db=db, org_id=org_id)
        all_tool_calls: list[dict[str, Any]] = []
        all_tool_results: list[dict[str, Any]] = []
        model_used = "claude-sonnet-4-20250514"
        tokens_in = 0
        tokens_out = 0

        # Phase 1: Tool loop
        for _iteration in range(MAX_TOOL_ITERATIONS):
            result = await _call_gateway_with_tools(
                gateway_url=self._gateway_url,
                gateway_key=self._gateway_key,
                messages=messages,
            )

            model_used = result.get("model_used", model_used)
            usage = result.get("usage", {})
            tokens_in += usage.get("prompt_tokens", 0)
            stop_reason = result.get("stop_reason", "end_turn")

            if stop_reason == "tool_calls" or result.get("tool_calls"):
                tool_calls = result["tool_calls"]
                all_tool_calls.extend(tool_calls)

                assistant_turn: dict[str, Any] = {
                    "role": "assistant",
                    "content": result.get("content") or "",
                    "tool_calls": tool_calls,
                }
                messages.append(assistant_turn)

                for tc in tool_calls:
                    fn_name = tc["function"]["name"]
                    try:
                        fn_args = json.loads(tc["function"]["arguments"])
                    except (json.JSONDecodeError, KeyError):
                        fn_args = {}

                    yield {"type": "tool_call", "name": fn_name, "status": "running"}
                    tool_result = await tools_instance.execute(fn_name, fn_args)
                    all_tool_results.append({"tool": fn_name, "result": tool_result})
                    yield {"type": "tool_call", "name": fn_name, "status": "done", "result": tool_result}

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps(tool_result),
                    })
            else:
                # Ready to stream final response
                break

        # Phase 2: Stream final response
        final_content_parts: list[str] = []
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self._gateway_url}/v1/completions/stream",
                    json={
                        "messages": messages,
                        "task_type": "chat_with_tools",
                        "org_id": str(org_id),
                    },
                    headers={"Authorization": f"Bearer {self._gateway_key}"},
                ) as resp:
                    if resp.status_code != 200:
                        # Fall back to non-streaming
                        fallback = await _call_gateway_with_tools(
                            gateway_url=self._gateway_url,
                            gateway_key=self._gateway_key,
                            messages=messages,
                        )
                        content = fallback.get("content", "")
                        final_content_parts.append(content)
                        tokens_out += fallback.get("usage", {}).get("completion_tokens", 0)
                        yield {"type": "token", "content": content}
                    else:
                        async for line in resp.aiter_lines():
                            if line.startswith("data: "):
                                raw = line[6:]
                                try:
                                    data = json.loads(raw)
                                    if data.get("done"):
                                        break
                                    if "token" in data:
                                        token = data["token"]
                                        final_content_parts.append(token)
                                        yield {"type": "token", "content": token}
                                except json.JSONDecodeError:
                                    pass
        except Exception as e:
            logger.warning("ralph_stream_error", error=str(e))
            # Non-streaming fallback
            fallback = await _call_gateway_with_tools(
                gateway_url=self._gateway_url,
                gateway_key=self._gateway_key,
                messages=messages,
            )
            content = fallback.get("content", "")
            final_content_parts.append(content)
            yield {"type": "token", "content": content}

        final_content = "".join(final_content_parts)

        # Phase 3: Save and yield done
        assistant_msg = await service.append_message(
            db,
            conversation_id,
            AIMessageRole.ASSISTANT,
            final_content,
            tool_calls={"calls": all_tool_calls} if all_tool_calls else None,
            tool_results={"results": all_tool_results} if all_tool_results else None,
            model_used=model_used,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )

        yield {"type": "done", "message_id": str(assistant_msg.id)}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _history_to_dicts(history: list[AIMessage]) -> list[dict[str, Any]]:
    """Convert DB AIMessage objects to plain dicts for the context manager."""
    result: list[dict[str, Any]] = []
    for msg in history:
        role = msg.role.value
        if role in ("user", "assistant"):
            entry: dict[str, Any] = {"role": role, "content": msg.content or ""}
            if msg.tool_calls and role == "assistant":
                calls = msg.tool_calls.get("calls", [])
                if calls:
                    entry["tool_calls"] = calls
            result.append(entry)
        elif role == "tool_call":
            if msg.tool_results:
                for item in msg.tool_results.get("results", []):
                    result.append({
                        "role": "tool",
                        "content": json.dumps(item.get("result", {})),
                        "tool_call_id": item.get("id", "unknown"),
                    })
    return result


def _build_messages_for_llm(history: list[AIMessage]) -> list[dict[str, Any]]:
    """Convert DB messages to the format expected by the LLM API."""
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": RALPH_SYSTEM_PROMPT}
    ]
    for msg in history:
        role = msg.role.value
        if role in ("user", "assistant"):
            entry: dict[str, Any] = {"role": role, "content": msg.content or ""}
            if msg.tool_calls and role == "assistant":
                calls = msg.tool_calls.get("calls", [])
                if calls:
                    entry["tool_calls"] = calls
            messages.append(entry)
        elif role == "tool_call":
            # Reconstruct tool result messages from stored data
            if msg.tool_results:
                for item in msg.tool_results.get("results", []):
                    messages.append({
                        "role": "tool",
                        "content": json.dumps(item.get("result", {})),
                        "tool_call_id": item.get("id", "unknown"),
                    })
    return messages


async def _call_gateway_with_tools(
    gateway_url: str,
    gateway_key: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Call the AI gateway completions endpoint with optional tools."""
    payload: dict[str, Any] = {
        "messages": messages,
        "task_type": "chat_with_tools",
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{gateway_url}/v1/completions",
                json=payload,
                headers={"Authorization": f"Bearer {gateway_key}"},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("gateway_call_failed", error=str(e))
        return {
            "content": "I encountered an error processing your request. Please try again.",
            "tool_calls": None,
            "stop_reason": "end_turn",
            "model_used": "unknown",
            "usage": {},
        }
