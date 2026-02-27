"""Signal Score criteria definitions: 6 dimensions with detailed scoring rubric."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Criterion:
    """A single scoring criterion within a dimension."""

    id: str
    name: str
    description: str
    max_points: int
    relevant_classifications: tuple[str, ...]  # DocumentClassification values


@dataclass(frozen=True)
class Dimension:
    """A scoring dimension with weight and criteria."""

    id: str
    name: str
    weight: float
    criteria: tuple[Criterion, ...]


# ── Project Viability (20%) ──────────────────────────────────────────────────

TECHNICAL = Dimension(
    id="technical",
    name="Project Viability",
    weight=0.20,
    criteria=(
        Criterion(
            id="tech_site_assessment",
            name="Site Assessment / Feasibility Study",
            description="Comprehensive site assessment or feasibility study covering resource availability, site conditions, and technical constraints.",
            max_points=15,
            relevant_classifications=("technical_study",),
        ),
        Criterion(
            id="tech_technology_selection",
            name="Technology Selection",
            description="Documented technology selection with justification, vendor comparison, and performance specifications.",
            max_points=10,
            relevant_classifications=("technical_study",),
        ),
        Criterion(
            id="tech_epc_contracts",
            name="EPC Contracts / Quotes",
            description="Engineering, Procurement, and Construction contracts, LOIs, or detailed quotes from qualified contractors.",
            max_points=15,
            relevant_classifications=("legal_agreement",),
        ),
        Criterion(
            id="tech_eia",
            name="Environmental Impact Assessment",
            description="Environmental impact assessment covering ecological, water, noise, and visual impact analyses.",
            max_points=10,
            relevant_classifications=("environmental_report",),
        ),
        Criterion(
            id="tech_grid_connection",
            name="Grid Connection Study",
            description="Grid connection feasibility study, interconnection agreement, or utility approval documentation.",
            max_points=10,
            relevant_classifications=("technical_study",),
        ),
        Criterion(
            id="tech_construction_timeline",
            name="Construction Timeline",
            description="Detailed construction schedule with milestones, critical path analysis, and contingency planning.",
            max_points=10,
            relevant_classifications=("business_plan",),
        ),
        Criterion(
            id="tech_risk_assessment",
            name="Technical Risk Assessment",
            description="Systematic identification and mitigation plan for technical risks including technology, resource, and construction risks.",
            max_points=10,
            relevant_classifications=("technical_study",),
        ),
        Criterion(
            id="tech_third_party_review",
            name="Third-Party Technical Review",
            description="Independent engineer's report or third-party technical due diligence review.",
            max_points=10,
            relevant_classifications=("technical_study",),
        ),
        Criterion(
            id="tech_permits",
            name="Permits Application Filed",
            description="Evidence of permit applications filed, including building, environmental, and operational permits.",
            max_points=10,
            relevant_classifications=("permit",),
        ),
    ),
)

# ── Financial Planning (20%) ─────────────────────────────────────────────────

FINANCIAL = Dimension(
    id="financial",
    name="Financial Planning",
    weight=0.20,
    criteria=(
        Criterion(
            id="fin_revenue_model",
            name="Revenue Model / PPA",
            description="Documented revenue model with Power Purchase Agreement, feed-in tariff, or market price assumptions.",
            max_points=15,
            relevant_classifications=("financial_statement", "business_plan"),
        ),
        Criterion(
            id="fin_cost_structure",
            name="Detailed Cost Structure",
            description="Comprehensive cost breakdown including CAPEX, OPEX, and lifecycle cost analysis.",
            max_points=15,
            relevant_classifications=("financial_statement",),
        ),
        Criterion(
            id="fin_funding_plan",
            name="Funding Plan / Capital Stack",
            description="Capital stack detailing equity, debt, grants, and other funding sources with terms.",
            max_points=15,
            relevant_classifications=("business_plan",),
        ),
        Criterion(
            id="fin_projections",
            name="Financial Projections",
            description="Multi-year financial model with cash flow projections, IRR, NPV, and sensitivity analysis.",
            max_points=15,
            relevant_classifications=("financial_statement",),
        ),
        Criterion(
            id="fin_insurance",
            name="Insurance Coverage Plan",
            description="Insurance program covering construction, operational, and liability risks.",
            max_points=10,
            relevant_classifications=("insurance",),
        ),
        Criterion(
            id="fin_valuation",
            name="Valuation / Appraisal",
            description="Independent valuation or appraisal report using recognized methodologies.",
            max_points=10,
            relevant_classifications=("valuation",),
        ),
        Criterion(
            id="fin_tax_credits",
            name="Tax Credit Analysis",
            description="Analysis of applicable tax credits, incentives, and their qualification status.",
            max_points=10,
            relevant_classifications=("financial_statement",),
        ),
        Criterion(
            id="fin_dscr",
            name="Debt Service Coverage Analysis",
            description="DSCR analysis demonstrating ability to service debt obligations under various scenarios.",
            max_points=10,
            relevant_classifications=("financial_statement",),
        ),
    ),
)

# ── ESG & Impact (15%) ───────────────────────────────────────────────────────

ESG = Dimension(
    id="esg",
    name="ESG & Impact",
    weight=0.15,
    criteria=(
        Criterion(
            id="esg_environmental",
            name="Environmental Impact Quantification",
            description="Quantified environmental benefits including emissions avoided, energy generated, and resource savings.",
            max_points=20,
            relevant_classifications=("environmental_report",),
        ),
        Criterion(
            id="esg_carbon",
            name="Carbon Reduction Methodology",
            description="Documented carbon reduction methodology with baseline, additionality, and verification approach.",
            max_points=15,
            relevant_classifications=("environmental_report",),
        ),
        Criterion(
            id="esg_social",
            name="Social Impact Assessment",
            description="Assessment of social impacts including job creation, community benefits, and stakeholder engagement.",
            max_points=15,
            relevant_classifications=("environmental_report",),
        ),
        Criterion(
            id="esg_community",
            name="Community Engagement Plan",
            description="Structured community engagement and benefit-sharing plan with affected stakeholders.",
            max_points=15,
            relevant_classifications=("business_plan",),
        ),
        Criterion(
            id="esg_governance",
            name="Governance Structure",
            description="Clear governance framework with board composition, decision-making processes, and conflict resolution.",
            max_points=15,
            relevant_classifications=("legal_agreement",),
        ),
        Criterion(
            id="esg_sdg",
            name="SDG Alignment Mapping",
            description="Mapping of project contributions to UN Sustainable Development Goals with measurable indicators.",
            max_points=10,
            relevant_classifications=("business_plan",),
        ),
        Criterion(
            id="esg_reporting",
            name="ESG Reporting Framework",
            description="Adopted ESG reporting framework (GRI, SASB, TCFD) with defined KPIs and reporting cadence.",
            max_points=10,
            relevant_classifications=("environmental_report",),
        ),
    ),
)

# ── Risk Assessment (15%) ────────────────────────────────────────────────────

REGULATORY = Dimension(
    id="regulatory",
    name="Risk Assessment",
    weight=0.15,
    criteria=(
        Criterion(
            id="reg_permits",
            name="Permits & Licenses Obtained",
            description="Status of all required permits and licenses including building, environmental, and operational.",
            max_points=20,
            relevant_classifications=("permit",),
        ),
        Criterion(
            id="reg_env_compliance",
            name="Environmental Compliance Status",
            description="Documentation of environmental compliance including monitoring reports and regulatory correspondence.",
            max_points=15,
            relevant_classifications=("permit", "environmental_report"),
        ),
        Criterion(
            id="reg_legal_structure",
            name="Legal Entity Structure",
            description="Legal entity documentation including SPV formation, shareholder agreements, and corporate governance.",
            max_points=15,
            relevant_classifications=("legal_agreement",),
        ),
        Criterion(
            id="reg_land_rights",
            name="Land Rights / Leases",
            description="Secured land rights through ownership, long-term lease, or easement agreements.",
            max_points=15,
            relevant_classifications=("legal_agreement",),
        ),
        Criterion(
            id="reg_approvals_timeline",
            name="Regulatory Approvals Timeline",
            description="Timeline and status tracker for all regulatory approvals with expected completion dates.",
            max_points=15,
            relevant_classifications=("permit",),
        ),
        Criterion(
            id="reg_insurance_req",
            name="Insurance Requirements Met",
            description="Evidence that all regulatory and lender-required insurance coverages are in place.",
            max_points=10,
            relevant_classifications=("insurance",),
        ),
        Criterion(
            id="reg_compliance_plan",
            name="Compliance Monitoring Plan",
            description="Ongoing compliance monitoring plan covering environmental, safety, and regulatory requirements.",
            max_points=10,
            relevant_classifications=("business_plan",),
        ),
    ),
)

# ── Team Strength (15%) ──────────────────────────────────────────────────────

TEAM = Dimension(
    id="team",
    name="Team Strength",
    weight=0.15,
    criteria=(
        Criterion(
            id="team_core",
            name="Core Team Bios & Experience",
            description="Detailed bios of key team members with relevant experience in alternative investments and asset development.",
            max_points=20,
            relevant_classifications=("business_plan", "presentation"),
        ),
        Criterion(
            id="team_track_record",
            name="Track Record Documentation",
            description="Documented track record of successfully completed projects with performance data.",
            max_points=20,
            relevant_classifications=("business_plan",),
        ),
        Criterion(
            id="team_advisory",
            name="Advisory Board",
            description="Advisory board or technical committee with relevant industry expertise and credentials.",
            max_points=15,
            relevant_classifications=("presentation",),
        ),
        Criterion(
            id="team_partnerships",
            name="Key Partnerships / MoUs",
            description="Strategic partnerships or MoUs with technology providers, offtakers, or development partners.",
            max_points=15,
            relevant_classifications=("legal_agreement",),
        ),
        Criterion(
            id="team_pm_plan",
            name="Project Management Plan",
            description="Comprehensive project management plan with roles, responsibilities, and decision framework.",
            max_points=15,
            relevant_classifications=("business_plan",),
        ),
        Criterion(
            id="team_org_chart",
            name="Organizational Chart",
            description="Organizational structure showing reporting lines, key hires, and staffing plan.",
            max_points=15,
            relevant_classifications=("presentation",),
        ),
    ),
)

# ── Market Opportunity (15%) ─────────────────────────────────────────────────

MARKET_OPPORTUNITY = Dimension(
    id="market_opportunity",
    name="Market Opportunity",
    weight=0.15,
    criteria=(
        Criterion(
            id="mkt_market_research",
            name="Market Research & Sizing",
            description="Independent market research quantifying addressable market size, demand drivers, and growth trajectory.",
            max_points=20,
            relevant_classifications=("business_plan", "technical_study"),
        ),
        Criterion(
            id="mkt_competitive_analysis",
            name="Competitive Analysis",
            description="Analysis of competitive landscape identifying key competitors, market positioning, and differentiation.",
            max_points=15,
            relevant_classifications=("business_plan",),
        ),
        Criterion(
            id="mkt_demand_validation",
            name="Demand Validation / LOIs",
            description="Letters of Intent, offtake agreements, or other evidence of validated demand from potential customers.",
            max_points=20,
            relevant_classifications=("legal_agreement", "business_plan"),
        ),
        Criterion(
            id="mkt_exit_strategy",
            name="Exit Strategy & Liquidity",
            description="Documented exit strategy with potential acquirers, comparable transactions, and expected return timeline.",
            max_points=15,
            relevant_classifications=("business_plan",),
        ),
        Criterion(
            id="mkt_growth_plan",
            name="Growth & Expansion Plan",
            description="Roadmap for scaling the investment with milestones, resource requirements, and market expansion strategy.",
            max_points=15,
            relevant_classifications=("business_plan", "presentation"),
        ),
        Criterion(
            id="mkt_macro_trends",
            name="Macro Trend Alignment",
            description="Analysis of alignment with macro trends (regulatory tailwinds, demographic shifts, technology disruption).",
            max_points=15,
            relevant_classifications=("business_plan", "technical_study"),
        ),
    ),
)

# ── Module-level exports ─────────────────────────────────────────────────────

DIMENSIONS: list[Dimension] = [TECHNICAL, FINANCIAL, ESG, REGULATORY, TEAM, MARKET_OPPORTUNITY]

ALL_CRITERIA: dict[str, Criterion] = {}
for dim in DIMENSIONS:
    for crit in dim.criteria:
        ALL_CRITERIA[crit.id] = crit
