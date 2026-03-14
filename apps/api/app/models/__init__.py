"""SQLAlchemy models package — import all models so Base.metadata is populated."""

# Advisory / Board / Insurance
from app.models.advisory import (
    BoardAdvisorApplication,
    BoardAdvisorProfile,
    CapitalEfficiencyMetrics,
    EquityScenario,
    InsurancePolicy,
    InsuranceQuote,
    InvestorPersona,
    InvestorSignalScore,
    MonitoringAlert,
)

# AI
from app.models.ai import AIConversation, AIMessage, AITaskLog

# AI Citations & Data Lineage
from app.models.citations import AICitation
from app.models.lineage import DataLineage

# Alley-side models
from app.models.alley import RiskMitigationStatus

# API Keys
from app.models.api_keys import OrgApiKey

# Score Backtesting
from app.models.backtesting import BacktestRun, DealOutcome
from app.models.base import AuditMixin, BaseModel, ModelMixin, TimestampedModel

# Blockchain Audit Trail
from app.models.blockchain import BlockchainAnchor

# Certification
from app.models.certification import InvestorReadinessCertification

# Collaboration
from app.models.collaboration import Activity, Comment

# Compliance Calendar
from app.models.compliance import ComplianceDeadline

# Comparable Transactions
from app.models.comps import ComparableTransaction

# Professional Connections & Warm Intros
from app.models.connections import IntroductionRequest, ProfessionalConnection

# Data Connectors
from app.models.connectors import DataConnector, DataFetchLog, OrgConnectorConfig

# Core
from app.models.core import AuditLog, Notification, Organization, User

# CRM Sync
from app.models.crm import CRMConnection, CRMEntityMapping, CRMSyncLog

# Custom Domain (E03)
from app.models.custom_domain import CustomDomain

# Data Room
from app.models.dataroom import (
    Document,
    DocumentAccessLog,
    DocumentExtraction,
    DocumentFolder,
    ShareLink,
)

# Deal Flow Analytics
from app.models.deal_flow import DealStageTransition

# Deal Rooms
from app.models.deal_rooms import (
    DealRoom,
    DealRoomActivity,
    DealRoomDocument,
    DealRoomMember,
    DealRoomMessage,
)

# Digest History
from app.models.digest_log import DigestLog

# Document Version Control
from app.models.doc_versions import DocumentVersion

# Document Annotations
from app.models.document_annotations import DocumentAnnotation

# Due Diligence
from app.models.due_diligence import (
    DDChecklistItem,
    DDChecklistTemplate,
    DDItemStatus,
    DDProjectChecklist,
)

# Document Engagement
from app.models.engagement import DealEngagementSummary, DocumentEngagement
from app.models.enums import (
    AdvisorAvailabilityStatus,
    AdvisorCompensationPreference,
    AIAgentType,
    AIContextType,
    AIMessageRole,
    AITaskStatus,
    AntiDilutionType,
    AssetType,
    BoardAdvisorApplicationStatus,
    BudgetItemStatus,
    BusinessPlanStatus,
    CarbonVerificationStatus,
    DocumentAccessAction,
    DocumentClassification,
    DocumentStatus,
    EquitySecurityType,
    ExtractionType,
    FundType,
    HoldingStatus,
    InsurancePolicyStatus,
    InsurancePremiumFrequency,
    InsuranceSide,
    InvestorPersonaStrategy,
    LegalDocumentStatus,
    LegalDocumentType,
    ListingStatus,
    ListingType,
    ListingVisibility,
    MatchInitiator,
    MatchStatus,
    MilestoneStatus,
    MonitoringAlertDomain,
    MonitoringAlertSeverity,
    MonitoringAlertType,
    NotificationType,
    OrgType,
    PortfolioStatus,
    PortfolioStrategy,
    ProjectStage,
    ProjectStatus,
    ProjectType,
    ReportCategory,
    ReportFrequency,
    ReportStatus,
    RFQStatus,
    RiskAssessmentStatus,
    RiskEntityType,
    RiskProbability,
    RiskSeverity,
    RiskTolerance,
    RiskType,
    SFDRClassification,
    SubscriptionStatus,
    SubscriptionTier,
    TaxCreditQualification,
    TransactionStatus,
    UserRole,
    ValuationMethod,
    ValuationStatus,
)

# ESG Impact
from app.models.esg import ESGMetrics

# Expert Insights
from app.models.expert_notes import ExpertNote

# External Market Data
from app.models.external_data import ExternalDataPoint

# Financial
from app.models.financial import BusinessPlan, CarbonCredit, TaxCredit, Valuation
from app.models.financial_templates import FinancialTemplate

# FX Rates
from app.models.fx import FXRate

# Gamification
from app.models.gamification import Badge, ImprovementQuest, UserBadge

# Risk Profiling
from app.models.investor_risk import InvestorRiskProfile

# Investors
from app.models.investors import (
    InvestorMandate,
    Portfolio,
    PortfolioHolding,
    PortfolioMetrics,
    RiskAssessment,
)

# Launch Preparation (E04)
from app.models.launch import FeatureFlag, FeatureFlagOverride, UsageEvent, WaitlistEntry

# Legal
from app.models.legal import LegalDocument, LegalTemplate

# LP Reporting
from app.models.lp_report import LPReport

# Market Data Enrichment
from app.models.market_enrichment import (
    DataReviewQueue,
    MarketDataProcessed,
    MarketDataRaw,
    MarketDataSource,
    MarketEnrichmentFetchLog,
)

# Marketplace
from app.models.marketplace import RFQ, Listing, Transaction

# Matching
from app.models.matching import MatchMessage, MatchResult

# Meeting Prep
from app.models.meeting_prep import MeetingBriefing

# Metrics & Benchmarks
from app.models.metrics import BenchmarkAggregate, MetricSnapshot

# Covenant & KPI Monitoring
from app.models.monitoring import Covenant, KPIActual, KPITarget

# Cashflow Pacing
from app.models.pacing import CashflowAssumption, CashflowProjection

# Projects
from app.models.projects import Project, ProjectBudgetItem, ProjectMilestone, SignalScore

# Q&A Workflow
from app.models.qa import QAAnswer, QAQuestion

# AI Document Redaction
from app.models.redaction import RedactionJob

# Reporting
from app.models.reporting import GeneratedReport, ReportTemplate, ScheduledReport

# Resource Ownership (object-level RBAC)
from app.models.resource_ownership import PermissionLevel, ResourceOwnership

# Smart Screener
from app.models.screener import SavedSearch

# Portfolio Stress Testing
from app.models.stress_test import StressTestRun

# Industry Taxonomy & Financial Templates
from app.models.taxonomy import IndustryTaxonomy

# Tokenization
from app.models.tokenization import TokenHolding, TokenizationRecord, TokenTransfer

# Watchlists & Alerts
from app.models.watchlists import Watchlist, WatchlistAlert

# Webhooks
from app.models.webhooks import WebhookDelivery, WebhookSubscription

__all__ = [
    "RFQ",
    # AI
    "AIConversation",
    "AIMessage",
    "AITaskLog",
    # AI Citations & Data Lineage
    "AICitation",
    "DataLineage",
    "Activity",
    "AuditLog",
    "AuditMixin",
    "BacktestRun",
    # Gamification
    "Badge",
    # Base
    "BaseModel",
    "BenchmarkAggregate",
    # Blockchain Audit Trail
    "BlockchainAnchor",
    "BoardAdvisorApplication",
    # Advisory / Board / Insurance
    "BoardAdvisorProfile",
    "BusinessPlan",
    # CRM Sync
    "CRMConnection",
    "CRMEntityMapping",
    "CRMSyncLog",
    "CapitalEfficiencyMetrics",
    "CarbonCredit",
    # Cashflow Pacing
    "CashflowAssumption",
    "CashflowProjection",
    # Collaboration
    "Comment",
    # Comparable Transactions
    "ComparableTransaction",
    # Compliance Calendar
    "ComplianceDeadline",
    # Covenant & KPI Monitoring
    "Covenant",
    # Custom Domain (E03)
    "CustomDomain",
    "DDChecklistItem",
    # Due Diligence
    "DDChecklistTemplate",
    "DDItemStatus",
    "DDProjectChecklist",
    # Data Connectors
    "DataConnector",
    "DataFetchLog",
    "DealEngagementSummary",
    # Score Backtesting
    "DealOutcome",
    # Deal Rooms
    "DealRoom",
    "DealRoomActivity",
    "DealRoomDocument",
    "DealRoomMember",
    "DealRoomMessage",
    # Deal Flow Analytics
    "DealStageTransition",
    # Digest History
    "DigestLog",
    # Data Room
    "Document",
    "DocumentAccessLog",
    # Document Annotations
    "DocumentAnnotation",
    # Document Engagement
    "DocumentEngagement",
    "DocumentExtraction",
    "DocumentFolder",
    # Document Version Control
    "DocumentVersion",
    # ESG Impact
    "ESGMetrics",
    "EquityScenario",
    # Expert Insights
    "ExpertNote",
    # External Market Data
    "ExternalDataPoint",
    # FX Rates
    "FXRate",
    # Launch Preparation (E04)
    "FeatureFlag",
    "FeatureFlagOverride",
    "FinancialTemplate",
    "GeneratedReport",
    "ImprovementQuest",
    # Industry Taxonomy & Financial Templates
    "IndustryTaxonomy",
    "InsurancePolicy",
    "InsuranceQuote",
    "IntroductionRequest",
    "InvestorMandate",
    "InvestorPersona",
    # Certification
    "InvestorReadinessCertification",
    # Risk Profiling
    "InvestorRiskProfile",
    "InvestorSignalScore",
    "KPIActual",
    "KPITarget",
    # LP Reporting
    "LPReport",
    # Legal
    "LegalDocument",
    "LegalTemplate",
    # Market Data Enrichment
    "DataReviewQueue",
    "MarketDataProcessed",
    "MarketDataRaw",
    "MarketDataSource",
    "MarketEnrichmentFetchLog",
    # Marketplace
    "Listing",
    "MatchMessage",
    # Matching
    "MatchResult",
    # Meeting Prep
    "MeetingBriefing",
    # Metrics & Benchmarks
    "MetricSnapshot",
    "ModelMixin",
    "MonitoringAlert",
    "Notification",
    # API Keys
    "OrgApiKey",
    "OrgConnectorConfig",
    # Core
    "Organization",
    # Investors
    "Portfolio",
    "PortfolioHolding",
    "PortfolioMetrics",
    # Warm Introductions
    "ProfessionalConnection",
    # Projects
    "Project",
    "ProjectBudgetItem",
    "ProjectMilestone",
    "QAAnswer",
    # Q&A Workflow
    "QAQuestion",
    # AI Document Redaction
    "RedactionJob",
    # Resource Ownership (object-level RBAC)
    "PermissionLevel",
    "ResourceOwnership",
    # Reporting
    "ReportTemplate",
    "RiskAssessment",
    # Alley-side models
    "RiskMitigationStatus",
    # Smart Screener
    "SavedSearch",
    "ScheduledReport",
    "ShareLink",
    "SignalScore",
    # Portfolio Stress Testing
    "StressTestRun",
    "TaxCredit",
    "TimestampedModel",
    "TokenHolding",
    "TokenTransfer",
    "TokenizationRecord",
    "Transaction",
    "UsageEvent",
    "User",
    "UserBadge",
    # Financial
    "Valuation",
    "WaitlistEntry",
    # Watchlists
    "Watchlist",
    "WatchlistAlert",
    "WebhookDelivery",
    # Webhooks
    "WebhookSubscription",
]
