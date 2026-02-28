"""Ralph AI — tool implementations that call existing SCR service layers."""

import json
import uuid
from typing import Any

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = structlog.get_logger()


class RalphTools:
    """Executes Ralph's 19 tools by delegating to existing SCR service layers."""

    def __init__(self, db: AsyncSession, org_id: uuid.UUID) -> None:
        self.db = db
        self.org_id = org_id
        self._gateway_url = settings.AI_GATEWAY_URL
        self._gateway_key = settings.AI_GATEWAY_API_KEY

    async def execute(self, tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a tool call by name and return the result."""
        handler = getattr(self, f"_tool_{tool_name}", None)
        if handler is None:
            return {"error": f"Unknown tool: {tool_name}"}
        try:
            return await handler(**tool_input)
        except Exception as e:
            logger.warning("ralph_tool_error", tool=tool_name, error=str(e))
            return {"error": str(e)}

    # ── Project tools ─────────────────────────────────────────────────────────

    async def _tool_get_project_details(self, project_id: str) -> dict[str, Any]:
        from app.models.projects import Project
        stmt = select(Project).where(
            Project.id == uuid.UUID(project_id),
            Project.org_id == self.org_id,
            Project.is_deleted.is_(False),
        )
        result = await self.db.execute(stmt)
        project = result.scalar_one_or_none()
        if project is None:
            return {"error": "Project not found"}
        return {
            "id": str(project.id),
            "name": project.name,
            "project_type": project.project_type.value if project.project_type else None,
            "status": project.status.value if project.status else None,
            "stage": project.stage.value if project.stage else None,
            "country": project.country,
            "description": project.description,
            "target_raise": float(project.target_raise) if project.target_raise else None,
            "created_at": str(project.created_at),
        }

    async def _tool_get_signal_score(self, project_id: str) -> dict[str, Any]:
        from app.models.projects import SignalScore
        stmt = select(SignalScore).where(
            SignalScore.project_id == uuid.UUID(project_id),
        ).order_by(SignalScore.created_at.desc())
        result = await self.db.execute(stmt)
        score = result.scalars().first()
        if score is None:
            return {"error": "No signal score found for this project"}
        return {
            "project_id": project_id,
            "overall_score": float(score.overall_score) if score.overall_score else None,
            "tier": score.tier.value if score.tier else None,
            "dimension_scores": score.dimension_scores,
            "created_at": str(score.created_at),
        }

    async def _tool_get_risk_assessment(self, entity_id: str, entity_type: str = "project") -> dict[str, Any]:
        from app.models.investors import RiskAssessment
        stmt = select(RiskAssessment).where(
            RiskAssessment.org_id == self.org_id,
            RiskAssessment.entity_id == uuid.UUID(entity_id),
            RiskAssessment.entity_type == entity_type,
            RiskAssessment.is_deleted.is_(False),
        ).order_by(RiskAssessment.created_at.desc())
        result = await self.db.execute(stmt)
        assessment = result.scalars().first()
        if assessment is None:
            return {"error": "No risk assessment found"}
        return {
            "id": str(assessment.id),
            "entity_id": entity_id,
            "overall_score": float(assessment.overall_score) if assessment.overall_score else None,
            "risk_level": assessment.risk_level.value if assessment.risk_level else None,
            "status": assessment.status.value if assessment.status else None,
            "summary": assessment.summary,
            "created_at": str(assessment.created_at),
        }

    # ── Portfolio tools ───────────────────────────────────────────────────────

    async def _tool_get_portfolio_metrics(self, portfolio_id: str | None = None) -> dict[str, Any]:
        from app.models.investors import Portfolio, PortfolioMetrics
        if portfolio_id:
            stmt = select(Portfolio).where(
                Portfolio.id == uuid.UUID(portfolio_id),
                Portfolio.org_id == self.org_id,
                Portfolio.is_deleted.is_(False),
            )
        else:
            stmt = select(Portfolio).where(
                Portfolio.org_id == self.org_id,
                Portfolio.is_deleted.is_(False),
            ).limit(1)
        result = await self.db.execute(stmt)
        portfolio = result.scalar_one_or_none()
        if portfolio is None:
            return {"error": "No portfolio found"}

        metrics_stmt = select(PortfolioMetrics).where(
            PortfolioMetrics.portfolio_id == portfolio.id,
        ).order_by(PortfolioMetrics.calculated_at.desc())
        metrics_result = await self.db.execute(metrics_stmt)
        metrics = metrics_result.scalars().first()

        return {
            "portfolio_id": str(portfolio.id),
            "name": portfolio.name,
            "strategy": portfolio.strategy.value if portfolio.strategy else None,
            "total_committed": float(portfolio.total_committed) if portfolio.total_committed else None,
            "total_deployed": float(portfolio.total_deployed) if portfolio.total_deployed else None,
            "metrics": {
                "total_value": float(metrics.total_value) if metrics and metrics.total_value else None,
                "irr": float(metrics.irr) if metrics and metrics.irr else None,
                "moic": float(metrics.moic) if metrics and metrics.moic else None,
                "num_holdings": metrics.num_holdings if metrics else None,
            } if metrics else None,
        }

    # ── AI-gateway powered tools ──────────────────────────────────────────────

    async def _tool_search_documents(self, query: str, project_id: str | None = None) -> dict[str, Any]:
        """Search documents via AI gateway RAG endpoint."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload: dict[str, Any] = {
                    "query": query,
                    "org_id": str(self.org_id),
                    "limit": 5,
                }
                if project_id:
                    payload["entity_id"] = project_id
                resp = await client.post(
                    f"{self._gateway_url}/v1/search",
                    json=payload,
                    headers={"Authorization": f"Bearer {self._gateway_key}"},
                )
                if resp.status_code == 200:
                    return resp.json()
                return {"results": [], "error": f"Search unavailable (status {resp.status_code})"}
        except Exception as e:
            return {"results": [], "error": str(e)}

    async def _tool_generate_report_section(
        self, topic: str, context: str, section_type: str = "analysis"
    ) -> dict[str, Any]:
        """Generate a report section via AI gateway."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self._gateway_url}/v1/completions",
                    json={
                        "task_type": "generate_section",
                        "prompt": f"Write a {section_type} section about: {topic}\n\nContext:\n{context}",
                        "org_id": str(self.org_id),
                    },
                    headers={"Authorization": f"Bearer {self._gateway_key}"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return {"content": data.get("content", ""), "model": data.get("model_used")}
                return {"content": "", "error": f"Generation failed (status {resp.status_code})"}
        except Exception as e:
            return {"content": "", "error": str(e)}

    # ── Matching tools ────────────────────────────────────────────────────────

    async def _tool_find_matching_investors(self, project_id: str, limit: int = 5) -> dict[str, Any]:
        from app.models.projects import Project
        from app.modules.matching import service as matching_service
        try:
            recs = await matching_service.get_investor_recommendations(
                self.db, self.org_id, limit=limit
            )
            return {"investors": [r.model_dump() for r in recs.items[:limit]]}
        except Exception as e:
            return {"investors": [], "error": str(e)}

    async def _tool_find_matching_projects(self, limit: int = 5) -> dict[str, Any]:
        from app.modules.matching import service as matching_service
        try:
            recs = await matching_service.get_ally_recommendations(
                self.db, self.org_id, limit=limit
            )
            return {"projects": [r.model_dump() for r in recs.items[:limit]]}
        except Exception as e:
            return {"projects": [], "error": str(e)}

    # ── Financial tools ───────────────────────────────────────────────────────

    async def _tool_run_valuation(self, project_id: str, method: str = "dcf") -> dict[str, Any]:
        from app.modules.valuation import service as val_service
        try:
            result = await val_service.get_latest_valuation(
                self.db, uuid.UUID(project_id), self.org_id
            )
            if result is None:
                return {"error": "No valuation found for this project"}
            return {
                "project_id": project_id,
                "method": result.method.value if result.method else method,
                "value": float(result.estimated_value) if result.estimated_value else None,
                "currency": result.currency,
                "created_at": str(result.created_at),
            }
        except Exception as e:
            return {"error": str(e)}

    async def _tool_calculate_equity_scenario(
        self, project_id: str, investment_amount: float, equity_percentage: float
    ) -> dict[str, Any]:
        from app.modules.equity_calculator import service as eq_service
        try:
            result = await eq_service.calculate_scenario(
                self.db, self.org_id, uuid.UUID(project_id),
                investment_amount=investment_amount,
                equity_percentage=equity_percentage,
            )
            return result.model_dump() if hasattr(result, "model_dump") else {"result": str(result)}
        except Exception as e:
            return {"error": str(e)}

    async def _tool_get_capital_efficiency(self, project_id: str) -> dict[str, Any]:
        from app.modules.capital_efficiency import service as ce_service
        try:
            result = await ce_service.get_capital_efficiency_report(
                self.db, self.org_id, uuid.UUID(project_id)
            )
            return result.model_dump() if hasattr(result, "model_dump") else {"result": str(result)}
        except Exception as e:
            return {"error": str(e)}

    # ── Carbon / Tax credit tools ─────────────────────────────────────────────

    async def _tool_get_carbon_estimate(self, project_id: str) -> dict[str, Any]:
        from app.modules.carbon_credits import service as cc_service
        try:
            result = await cc_service.get_carbon_estimate(
                self.db, self.org_id, uuid.UUID(project_id)
            )
            return result.model_dump() if hasattr(result, "model_dump") else {"result": str(result)}
        except Exception as e:
            return {"error": str(e)}

    async def _tool_get_tax_credit_info(self, project_id: str) -> dict[str, Any]:
        from app.modules.tax_credits import service as tc_service
        try:
            result = await tc_service.get_tax_credit_summary(
                self.db, self.org_id, uuid.UUID(project_id)
            )
            return result.model_dump() if hasattr(result, "model_dump") else {"result": str(result)}
        except Exception as e:
            return {"error": str(e)}

    # ── Signal score tools ────────────────────────────────────────────────────

    async def _tool_get_investor_signal_score(self) -> dict[str, Any]:
        from app.modules.investor_signal_score import service as iss_service
        try:
            result = await iss_service.get_investor_signal_score(self.db, self.org_id)
            return result.model_dump() if hasattr(result, "model_dump") else {"result": str(result)}
        except Exception as e:
            return {"error": str(e)}

    async def _tool_get_improvement_plan(self, project_id: str | None = None) -> dict[str, Any]:
        from app.modules.signal_score import service as ss_service
        try:
            result = await ss_service.get_improvement_plan(
                self.db, self.org_id,
                project_id=uuid.UUID(project_id) if project_id else None,
            )
            return result.model_dump() if hasattr(result, "model_dump") else {"result": str(result)}
        except Exception as e:
            return {"error": str(e)}

    # ── Advisory tools ────────────────────────────────────────────────────────

    async def _tool_find_board_advisors(self, expertise: list[str] | None = None) -> dict[str, Any]:
        from app.modules.board_advisor import service as ba_service
        try:
            result = await ba_service.find_matching_advisors(
                self.db, self.org_id, expertise=expertise
            )
            return result.model_dump() if hasattr(result, "model_dump") else {"result": str(result)}
        except Exception as e:
            return {"error": str(e)}

    async def _tool_get_risk_mitigation_strategies(self, risk_type: str, project_id: str | None = None) -> dict[str, Any]:
        from app.modules.risk import service as risk_service
        try:
            result = await risk_service.get_mitigation_strategies(
                self.db, self.org_id,
                risk_type=risk_type,
                entity_id=uuid.UUID(project_id) if project_id else None,
            )
            return result.model_dump() if hasattr(result, "model_dump") else {"result": str(result)}
        except Exception as e:
            return {"error": str(e)}

    async def _tool_get_insurance_impact(self, project_id: str) -> dict[str, Any]:
        from app.modules.risk import service as risk_service
        try:
            result = await risk_service.get_insurance_impact_analysis(
                self.db, self.org_id, uuid.UUID(project_id)
            )
            return result.model_dump() if hasattr(result, "model_dump") else {"result": str(result)}
        except Exception as e:
            return {"error": str(e)}

    # ── Legal tools ───────────────────────────────────────────────────────────

    async def _tool_review_legal_document(self, document_id: str) -> dict[str, Any]:
        from app.modules.legal import service as legal_service
        try:
            result = await legal_service.review_document(
                self.db, self.org_id, uuid.UUID(document_id)
            )
            return result.model_dump() if hasattr(result, "model_dump") else {"result": str(result)}
        except Exception as e:
            return {"error": str(e)}

    # ── Workflow tools (concurrent chains) ────────────────────────────────────

    async def _tool_deep_dive_project(self, project_id: str) -> dict[str, Any]:
        """Comprehensive project analysis — chains 6 tools concurrently."""
        import asyncio
        results = await asyncio.gather(
            self._tool_get_project_details(project_id),
            self._tool_get_signal_score(project_id),
            self._tool_get_risk_assessment(project_id, "project"),
            self._tool_search_documents("business plan overview financials", project_id=project_id),
            self._tool_run_valuation(project_id),
            self._tool_find_matching_investors(project_id, limit=3),
            return_exceptions=True,
        )
        keys = ["project", "signal_score", "risk", "documents", "valuation", "matching_investors"]
        return {
            k: (v if not isinstance(v, Exception) else {"error": str(v)})
            for k, v in zip(keys, results)
        }

    async def _tool_portfolio_health_check(self, portfolio_id: str | None = None) -> dict[str, Any]:
        """Portfolio-wide health check — chains 3 tools concurrently."""
        import asyncio

        portfolio_result = await self._tool_get_portfolio_metrics(portfolio_id)
        pid = portfolio_result.get("portfolio_id") if "error" not in portfolio_result else None

        async def _no_portfolio() -> dict[str, Any]:
            return {"error": "No portfolio found"}

        risk_coro = (
            self._tool_get_risk_assessment(pid, "portfolio") if pid else _no_portfolio()
        )
        docs_coro = self._tool_search_documents("compliance regulatory reporting portfolio")

        risk_result, docs_result = await asyncio.gather(risk_coro, docs_coro, return_exceptions=True)

        return {
            "portfolio": portfolio_result,
            "risk": risk_result if not isinstance(risk_result, Exception) else {"error": str(risk_result)},
            "compliance_documents": docs_result if not isinstance(docs_result, Exception) else {"error": str(docs_result)},
        }

    async def _tool_deal_readiness_check(self, project_id: str) -> dict[str, Any]:
        """Deal readiness assessment — chains 4 tools concurrently."""
        import asyncio

        signal_coro = self._tool_get_signal_score(project_id)
        docs_coro = self._tool_search_documents("term sheet subscription agreement legal document", project_id=project_id)
        improvement_coro = self._tool_get_improvement_plan(project_id)
        risk_coro = self._tool_get_risk_assessment(project_id, "project")

        signal, docs, improvement, risk = await asyncio.gather(
            signal_coro, docs_coro, improvement_coro, risk_coro, return_exceptions=True
        )

        return {
            "signal_score": signal if not isinstance(signal, Exception) else {"error": str(signal)},
            "documents": docs if not isinstance(docs, Exception) else {"error": str(docs)},
            "improvement_plan": improvement if not isinstance(improvement, Exception) else {"error": str(improvement)},
            "risk": risk if not isinstance(risk, Exception) else {"error": str(risk)},
        }


# ── Tool definitions for Claude API ──────────────────────────────────────────

RALPH_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_project_details",
            "description": "Retrieve full details for a specific project by its ID, including type, status, stage, country, and funding target.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "UUID of the project"},
                },
                "required": ["project_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_signal_score",
            "description": "Get the latest signal score for a project, including overall score, tier, and dimension breakdown.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "UUID of the project"},
                },
                "required": ["project_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_portfolio_metrics",
            "description": "Get portfolio performance metrics including IRR, MOIC, total value, and number of holdings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "portfolio_id": {"type": "string", "description": "UUID of the portfolio (optional, defaults to primary)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_risk_assessment",
            "description": "Retrieve the latest risk assessment for a project or portfolio.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {"type": "string", "description": "UUID of the entity"},
                    "entity_type": {"type": "string", "enum": ["project", "portfolio"], "description": "Type of entity"},
                },
                "required": ["entity_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Search through uploaded documents using semantic search. Use this to find specific information in pitch decks, financial models, contracts, or other documents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "project_id": {"type": "string", "description": "Optional project UUID to scope the search"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_valuation",
            "description": "Get the latest valuation for a project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "UUID of the project"},
                    "method": {"type": "string", "enum": ["dcf", "comparables", "replacement_cost", "blended"], "description": "Valuation method"},
                },
                "required": ["project_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_matching_investors",
            "description": "Find investors that match the organization's projects based on sector, geography, ticket size, and investment thesis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "UUID of the project to match"},
                    "limit": {"type": "integer", "description": "Maximum number of results", "default": 5},
                },
                "required": ["project_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_matching_projects",
            "description": "Find projects that match the investor's mandate, sector preferences, geography, and ticket size.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Maximum number of results", "default": 5},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_carbon_estimate",
            "description": "Get carbon credit estimates and environmental impact metrics for a project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "UUID of the project"},
                },
                "required": ["project_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_tax_credit_info",
            "description": "Get tax credit information and eligibility for a project (IRA, ITC, PTC, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "UUID of the project"},
                },
                "required": ["project_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_report_section",
            "description": "Generate a written analysis or report section on any topic using available data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "The topic to analyze or write about"},
                    "context": {"type": "string", "description": "Supporting data or context to include"},
                    "section_type": {"type": "string", "description": "Type of section: analysis, summary, recommendation"},
                },
                "required": ["topic", "context"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_investor_signal_score",
            "description": "Get the investor signal score for the current organization, including profile completeness and engagement metrics.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_improvement_plan",
            "description": "Get actionable improvement recommendations to increase signal score or deal readiness.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Optional project UUID for project-specific recommendations"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_board_advisors",
            "description": "Find board advisor matches based on expertise, sector experience, and network.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expertise": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of expertise areas to match",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_risk_mitigation_strategies",
            "description": "Get risk mitigation strategies and recommendations for specific risk types.",
            "parameters": {
                "type": "object",
                "properties": {
                    "risk_type": {"type": "string", "description": "Type of risk: market, operational, regulatory, environmental, financial"},
                    "project_id": {"type": "string", "description": "Optional project UUID for project-specific strategies"},
                },
                "required": ["risk_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "review_legal_document",
            "description": "Review a legal document and extract key clauses, risks, and recommendations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string", "description": "UUID of the document to review"},
                },
                "required": ["document_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_equity_scenario",
            "description": "Calculate equity dilution, ownership percentages, and return scenarios for an investment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "UUID of the project"},
                    "investment_amount": {"type": "number", "description": "Investment amount in USD"},
                    "equity_percentage": {"type": "number", "description": "Equity percentage requested"},
                },
                "required": ["project_id", "investment_amount", "equity_percentage"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_capital_efficiency",
            "description": "Analyze capital efficiency metrics: burn rate, runway, deployment efficiency, and use-of-proceeds breakdown.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "UUID of the project"},
                },
                "required": ["project_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_insurance_impact",
            "description": "Analyze the impact of insurance coverage on project risk profile and investor returns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "UUID of the project"},
                },
                "required": ["project_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "deep_dive_project",
            "description": "Run a comprehensive deep-dive analysis on a project. Concurrently retrieves project details, signal score, risk assessment, document search, valuation, and matching investors. Use this when the user wants a full picture of a specific project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "UUID of the project to analyze"},
                },
                "required": ["project_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "portfolio_health_check",
            "description": "Run a portfolio-wide health check. Concurrently retrieves portfolio metrics, risk assessment, and compliance documents. Use this when the user asks about overall portfolio performance or health.",
            "parameters": {
                "type": "object",
                "properties": {
                    "portfolio_id": {"type": "string", "description": "UUID of the portfolio (optional, defaults to primary portfolio)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "deal_readiness_check",
            "description": "Assess deal readiness for a project. Concurrently checks signal score, legal documents, improvement plan, and risk profile to determine how investment-ready the project is.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "UUID of the project to assess"},
                },
                "required": ["project_id"],
            },
        },
    },
]
