"""PostgreSQL native enums for all domain models."""

import enum


# ── Core ─────────────────────────────────────────────────────────────────────


class OrgType(str, enum.Enum):
    INVESTOR = "investor"
    ALLY = "ally"
    ADMIN = "admin"


class SubscriptionTier(str, enum.Enum):
    FOUNDATION = "foundation"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    TRIAL = "trial"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    VIEWER = "viewer"


class NotificationType(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ACTION_REQUIRED = "action_required"
    MENTION = "mention"
    SYSTEM = "system"


# ── Data Room ────────────────────────────────────────────────────────────────


class DocumentStatus(str, enum.Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"
    ARCHIVED = "archived"


class ExtractionType(str, enum.Enum):
    KPI = "kpi"
    CLAUSE = "clause"
    DEADLINE = "deadline"
    FINANCIAL = "financial"
    CLASSIFICATION = "classification"
    SUMMARY = "summary"
    # Cross-module analysis cache types (added by migration f1a2b3c4d5e6)
    QUALITY_ASSESSMENT = "quality_assessment"
    RISK_FLAGS = "risk_flags"
    DEAL_RELEVANCE = "deal_relevance"
    COMPLETENESS_CHECK = "completeness_check"
    KEY_FIGURES = "key_figures"
    ENTITY_EXTRACTION = "entity_extraction"


class DocumentAccessAction(str, enum.Enum):
    VIEW = "view"
    DOWNLOAD = "download"
    SHARE = "share"
    PRINT = "print"


class DocumentClassification(str, enum.Enum):
    FINANCIAL_STATEMENT = "financial_statement"
    LEGAL_AGREEMENT = "legal_agreement"
    TECHNICAL_STUDY = "technical_study"
    ENVIRONMENTAL_REPORT = "environmental_report"
    PERMIT = "permit"
    INSURANCE = "insurance"
    VALUATION = "valuation"
    BUSINESS_PLAN = "business_plan"
    PRESENTATION = "presentation"
    CORRESPONDENCE = "correspondence"
    OTHER = "other"


# ── Projects ─────────────────────────────────────────────────────────────────


class ProjectType(str, enum.Enum):
    # Legacy renewable energy asset types (retained for backward compatibility)
    SOLAR = "solar"
    WIND = "wind"
    HYDRO = "hydro"
    BIOMASS = "biomass"
    GEOTHERMAL = "geothermal"
    ENERGY_EFFICIENCY = "energy_efficiency"
    GREEN_BUILDING = "green_building"
    SUSTAINABLE_AGRICULTURE = "sustainable_agriculture"
    # Broader alternative investment asset classes
    INFRASTRUCTURE = "infrastructure"          # Energy, transport, telecom, water, social
    REAL_ESTATE = "real_estate"                # Commercial, residential, development
    PRIVATE_EQUITY = "private_equity"          # Growth, buyout, venture
    NATURAL_RESOURCES = "natural_resources"    # Agriculture, forestry, mining, water rights
    PRIVATE_CREDIT = "private_credit"          # Direct lending, mezzanine, distressed
    DIGITAL_ASSETS = "digital_assets"          # Tokenized securities, blockchain-based
    IMPACT = "impact"                          # SDG-aligned, community development
    SPECIALTY = "specialty"                    # Litigation finance, royalties, collectibles
    OTHER = "other"


class ProjectStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    FUNDRAISING = "fundraising"
    FUNDED = "funded"
    CONSTRUCTION = "construction"
    OPERATIONAL = "operational"
    ARCHIVED = "archived"


class ProjectStage(str, enum.Enum):
    CONCEPT = "concept"
    PRE_DEVELOPMENT = "pre_development"
    DEVELOPMENT = "development"
    CONSTRUCTION_READY = "construction_ready"
    UNDER_CONSTRUCTION = "under_construction"
    OPERATIONAL = "operational"


class MilestoneStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"
    BLOCKED = "blocked"


class BudgetItemStatus(str, enum.Enum):
    PLANNED = "planned"
    COMMITTED = "committed"
    PAID = "paid"


# ── Investors ────────────────────────────────────────────────────────────────


class PortfolioStrategy(str, enum.Enum):
    IMPACT = "impact"
    GROWTH = "growth"
    INCOME = "income"
    BALANCED = "balanced"
    OPPORTUNISTIC = "opportunistic"


class FundType(str, enum.Enum):
    OPEN_END = "open_end"
    CLOSED_END = "closed_end"
    EVERGREEN = "evergreen"
    SPV = "spv"


class SFDRClassification(str, enum.Enum):
    ARTICLE_6 = "article_6"
    ARTICLE_8 = "article_8"
    ARTICLE_9 = "article_9"
    NOT_APPLICABLE = "not_applicable"


class PortfolioStatus(str, enum.Enum):
    FUNDRAISING = "fundraising"
    INVESTING = "investing"
    FULLY_INVESTED = "fully_invested"
    HARVESTING = "harvesting"
    LIQUIDATED = "liquidated"


class AssetType(str, enum.Enum):
    EQUITY = "equity"
    DEBT = "debt"
    MEZZANINE = "mezzanine"
    PREFERRED = "preferred"
    CONVERTIBLE = "convertible"


class HoldingStatus(str, enum.Enum):
    ACTIVE = "active"
    EXITED = "exited"
    WRITTEN_OFF = "written_off"
    PENDING = "pending"


class RiskEntityType(str, enum.Enum):
    PROJECT = "project"
    PORTFOLIO = "portfolio"
    HOLDING = "holding"


class RiskType(str, enum.Enum):
    MARKET = "market"
    CREDIT = "credit"
    OPERATIONAL = "operational"
    REGULATORY = "regulatory"
    CLIMATE = "climate"
    CONCENTRATION = "concentration"
    COUNTERPARTY = "counterparty"
    LIQUIDITY = "liquidity"


class RiskSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskProbability(str, enum.Enum):
    UNLIKELY = "unlikely"
    POSSIBLE = "possible"
    LIKELY = "likely"
    VERY_LIKELY = "very_likely"


class RiskAssessmentStatus(str, enum.Enum):
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    MITIGATED = "mitigated"
    ACCEPTED = "accepted"


class RiskTolerance(str, enum.Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


# ── Matching ─────────────────────────────────────────────────────────────────


class MatchStatus(str, enum.Enum):
    SUGGESTED = "suggested"
    VIEWED = "viewed"
    INTERESTED = "interested"
    INTRO_REQUESTED = "intro_requested"
    ENGAGED = "engaged"
    MEETING_SCHEDULED = "meeting_scheduled"
    PASSED = "passed"
    DECLINED = "declined"


class MatchInitiator(str, enum.Enum):
    SYSTEM = "system"
    INVESTOR = "investor"
    ALLY = "ally"


# ── Financial ────────────────────────────────────────────────────────────────


class ValuationMethod(str, enum.Enum):
    DCF = "dcf"
    COMPARABLES = "comparables"
    REPLACEMENT_COST = "replacement_cost"
    BOOK_VALUE = "book_value"
    MARKET_VALUE = "market_value"
    BLENDED = "blended"


class ValuationStatus(str, enum.Enum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    SUPERSEDED = "superseded"


class TaxCreditQualification(str, enum.Enum):
    POTENTIAL = "potential"
    QUALIFIED = "qualified"
    CLAIMED = "claimed"
    TRANSFERRED = "transferred"


class CarbonVerificationStatus(str, enum.Enum):
    ESTIMATED = "estimated"
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    ISSUED = "issued"
    RETIRED = "retired"
    LISTED = "listed"


class BusinessPlanStatus(str, enum.Enum):
    DRAFT = "draft"
    REVIEW = "review"
    FINALIZED = "finalized"


# ── Legal ────────────────────────────────────────────────────────────────────


class LegalDocumentType(str, enum.Enum):
    TERM_SHEET = "term_sheet"
    SUBSCRIPTION_AGREEMENT = "subscription_agreement"
    SPV_INCORPORATION = "spv_incorporation"
    NDA = "nda"
    SIDE_LETTER = "side_letter"
    AMENDMENT = "amendment"


class LegalDocumentStatus(str, enum.Enum):
    DRAFT = "draft"
    REVIEW = "review"
    SENT = "sent"
    SIGNED = "signed"
    EXECUTED = "executed"
    EXPIRED = "expired"


# ── AI ───────────────────────────────────────────────────────────────────────


class AIContextType(str, enum.Enum):
    GENERAL = "general"
    PROJECT = "project"
    PORTFOLIO = "portfolio"
    DATAROOM = "dataroom"
    DEAL = "deal"


class AIMessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"


class AIAgentType(str, enum.Enum):
    DOCUMENT_INTELLIGENCE = "document_intelligence"
    SCORING = "scoring"
    FINANCIAL = "financial"
    MATCHING = "matching"
    REPORT = "report"
    CONVERSATIONAL = "conversational"
    COMPLIANCE = "compliance"


class AITaskStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Marketplace ──────────────────────────────────────────────────────────────


class ListingType(str, enum.Enum):
    EQUITY_SALE = "equity_sale"
    DEBT_SALE = "debt_sale"
    CO_INVESTMENT = "co_investment"
    CARBON_CREDIT = "carbon_credit"


class ListingStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    UNDER_NEGOTIATION = "under_negotiation"
    SOLD = "sold"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class ListingVisibility(str, enum.Enum):
    PUBLIC = "public"
    QUALIFIED_ONLY = "qualified_only"
    INVITE_ONLY = "invite_only"


class RFQStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    COUNTERED = "countered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


# ── Advisory / Board ─────────────────────────────────────────────────────────


class AdvisorAvailabilityStatus(str, enum.Enum):
    AVAILABLE = "available"
    LIMITED = "limited"
    UNAVAILABLE = "unavailable"


class AdvisorCompensationPreference(str, enum.Enum):
    EQUITY = "equity"
    CASH = "cash"
    PRO_BONO = "pro_bono"
    NEGOTIABLE = "negotiable"


class BoardAdvisorApplicationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    ACTIVE = "active"
    COMPLETED = "completed"


# ── Investor Personas ─────────────────────────────────────────────────────────


class InvestorPersonaStrategy(str, enum.Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    GROWTH = "growth"
    AGGRESSIVE = "aggressive"
    IMPACT_FIRST = "impact_first"


# ── Equity Scenarios ──────────────────────────────────────────────────────────


class EquitySecurityType(str, enum.Enum):
    COMMON_EQUITY = "common_equity"
    PREFERRED_EQUITY = "preferred_equity"
    CONVERTIBLE_NOTE = "convertible_note"
    SAFE = "safe"
    REVENUE_SHARE = "revenue_share"


class AntiDilutionType(str, enum.Enum):
    NONE = "none"
    BROAD_BASED = "broad_based"
    NARROW_BASED = "narrow_based"
    FULL_RATCHET = "full_ratchet"


# ── Monitoring Alerts ─────────────────────────────────────────────────────────


class MonitoringAlertType(str, enum.Enum):
    REGULATORY_CHANGE = "regulatory_change"
    MARKET_SHIFT = "market_shift"
    RISK_THRESHOLD = "risk_threshold"
    DATA_UPDATE = "data_update"
    NEWS_ALERT = "news_alert"
    COMPLIANCE_DEADLINE = "compliance_deadline"


class MonitoringAlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class MonitoringAlertDomain(str, enum.Enum):
    MARKET = "market"
    CLIMATE = "climate"
    REGULATORY = "regulatory"
    TECHNOLOGY = "technology"
    LIQUIDITY = "liquidity"


# ── Insurance ─────────────────────────────────────────────────────────────────


class InsurancePremiumFrequency(str, enum.Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class InsurancePolicyStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING_RENEWAL = "pending_renewal"


class InsuranceSide(str, enum.Enum):
    ALLY = "ally"
    INVESTOR = "investor"


# ── Reporting ────────────────────────────────────────────────────────────────


class ReportCategory(str, enum.Enum):
    PERFORMANCE = "performance"
    ESG = "esg"
    COMPLIANCE = "compliance"
    PORTFOLIO = "portfolio"
    PROJECT = "project"
    CUSTOM = "custom"


class ReportStatus(str, enum.Enum):
    QUEUED = "queued"
    GENERATING = "generating"
    READY = "ready"
    ERROR = "error"


class ReportFrequency(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"
