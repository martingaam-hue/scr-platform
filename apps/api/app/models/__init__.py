"""SQLAlchemy models package — import all models so Base.metadata is populated."""

from app.models.base import AuditMixin, BaseModel, ModelMixin, TimestampedModel
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

# Core
from app.models.core import AuditLog, Notification, Organization, User

# Data Room
from app.models.dataroom import (
    Document,
    DocumentAccessLog,
    DocumentExtraction,
    DocumentFolder,
    ShareLink,
)

# Projects
from app.models.projects import Project, ProjectBudgetItem, ProjectMilestone, SignalScore

# Investors
from app.models.investors import (
    InvestorMandate,
    Portfolio,
    PortfolioHolding,
    PortfolioMetrics,
    RiskAssessment,
)

# Matching
from app.models.matching import MatchMessage, MatchResult

# Financial
from app.models.financial import BusinessPlan, CarbonCredit, TaxCredit, Valuation

# Legal
from app.models.legal import LegalDocument, LegalTemplate

# AI
from app.models.ai import AIConversation, AIMessage, AITaskLog

# Collaboration
from app.models.collaboration import Activity, Comment

# Marketplace
from app.models.marketplace import Listing, RFQ, Transaction

# Reporting
from app.models.reporting import GeneratedReport, ReportTemplate, ScheduledReport

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

# Smart Screener
from app.models.screener import SavedSearch

# Risk Profiling
from app.models.investor_risk import InvestorRiskProfile

# Certification
from app.models.certification import InvestorReadinessCertification

# Deal Flow Analytics
from app.models.deal_flow import DealStageTransition

# Due Diligence
from app.models.due_diligence import (
    DDChecklistTemplate,
    DDChecklistItem,
    DDProjectChecklist,
    DDItemStatus,
)

# ESG Impact
from app.models.esg import ESGMetrics

# LP Reporting
from app.models.lp_report import LPReport

# Comparable Transactions
from app.models.comps import ComparableTransaction

# Professional Connections & Warm Intros
from app.models.connections import IntroductionRequest, ProfessionalConnection

# Document Version Control
from app.models.doc_versions import DocumentVersion

# FX Rates
from app.models.fx import FXRate

# Meeting Prep
from app.models.meeting_prep import MeetingBriefing

# Compliance Calendar
from app.models.compliance import ComplianceDeadline

# Portfolio Stress Testing
from app.models.stress_test import StressTestRun

# Data Connectors
from app.models.connectors import DataConnector, DataFetchLog, OrgConnectorConfig

# Deal Rooms
from app.models.deal_rooms import DealRoom, DealRoomActivity, DealRoomDocument, DealRoomMember, DealRoomMessage

# Watchlists & Alerts
from app.models.watchlists import Watchlist, WatchlistAlert

# Blockchain Audit Trail
from app.models.blockchain import BlockchainAnchor

# Gamification
from app.models.gamification import Badge, ImprovementQuest, UserBadge

# Metrics & Benchmarks
from app.models.metrics import BenchmarkAggregate, MetricSnapshot

# Q&A Workflow
from app.models.qa import QAAnswer, QAQuestion

# Document Engagement
from app.models.engagement import DealEngagementSummary, DocumentEngagement

# Covenant & KPI Monitoring
from app.models.monitoring import Covenant, KPIActual, KPITarget

# API Keys
from app.models.api_keys import OrgApiKey

# CRM Sync
from app.models.crm import CRMConnection, CRMEntityMapping, CRMSyncLog

# Cashflow Pacing
from app.models.pacing import CashflowAssumption, CashflowProjection

# Industry Taxonomy & Financial Templates
from app.models.taxonomy import IndustryTaxonomy
from app.models.financial_templates import FinancialTemplate

# Score Backtesting
from app.models.backtesting import BacktestRun, DealOutcome

# Expert Insights
from app.models.expert_notes import ExpertNote

# Webhooks
from app.models.webhooks import WebhookDelivery, WebhookSubscription

# Document Annotations
from app.models.document_annotations import DocumentAnnotation

# AI Document Redaction
from app.models.redaction import RedactionJob

# External Market Data
from app.models.external_data import ExternalDataPoint

# Launch Preparation (E04)
from app.models.launch import FeatureFlag, FeatureFlagOverride, UsageEvent, WaitlistEntry

# Custom Domain (E03)
from app.models.custom_domain import CustomDomain

# Digest History
from app.models.digest_log import DigestLog

__all__ = [
    # Base
    "BaseModel",
    "TimestampedModel",
    "ModelMixin",
    "AuditMixin",
    # Core
    "Organization",
    "User",
    "AuditLog",
    "Notification",
    # Data Room
    "Document",
    "DocumentFolder",
    "DocumentExtraction",
    "DocumentAccessLog",
    "ShareLink",
    # Projects
    "Project",
    "ProjectMilestone",
    "ProjectBudgetItem",
    "SignalScore",
    # Investors
    "Portfolio",
    "PortfolioHolding",
    "PortfolioMetrics",
    "InvestorMandate",
    "RiskAssessment",
    # Matching
    "MatchResult",
    "MatchMessage",
    # Financial
    "Valuation",
    "TaxCredit",
    "CarbonCredit",
    "BusinessPlan",
    # Legal
    "LegalDocument",
    "LegalTemplate",
    # AI
    "AIConversation",
    "AIMessage",
    "AITaskLog",
    # Collaboration
    "Comment",
    "Activity",
    # Marketplace
    "Listing",
    "RFQ",
    "Transaction",
    # Reporting
    "ReportTemplate",
    "GeneratedReport",
    "ScheduledReport",
    # Advisory / Board / Insurance
    "BoardAdvisorProfile",
    "BoardAdvisorApplication",
    "InvestorPersona",
    "EquityScenario",
    "CapitalEfficiencyMetrics",
    "MonitoringAlert",
    "InvestorSignalScore",
    "InsuranceQuote",
    "InsurancePolicy",
    # Smart Screener
    "SavedSearch",
    # Risk Profiling
    "InvestorRiskProfile",
    # Certification
    "InvestorReadinessCertification",
    # Deal Flow Analytics
    "DealStageTransition",
    # Due Diligence
    "DDChecklistTemplate",
    "DDChecklistItem",
    "DDProjectChecklist",
    "DDItemStatus",
    # ESG Impact
    "ESGMetrics",
    # LP Reporting
    "LPReport",
    # Comparable Transactions
    "ComparableTransaction",
    # Warm Introductions
    "ProfessionalConnection",
    "IntroductionRequest",
    # Document Version Control
    "DocumentVersion",
    # FX Rates
    "FXRate",
    # Meeting Prep
    "MeetingBriefing",
    # Compliance Calendar
    "ComplianceDeadline",
    # Portfolio Stress Testing
    "StressTestRun",
    # Data Connectors
    "DataConnector",
    "OrgConnectorConfig",
    "DataFetchLog",
    # Deal Rooms
    "DealRoom",
    "DealRoomMember",
    "DealRoomDocument",
    "DealRoomMessage",
    "DealRoomActivity",
    # Watchlists
    "Watchlist",
    "WatchlistAlert",
    # Blockchain Audit Trail
    "BlockchainAnchor",
    # Gamification
    "Badge",
    "UserBadge",
    "ImprovementQuest",
    # Metrics & Benchmarks
    "MetricSnapshot",
    "BenchmarkAggregate",
    # Q&A Workflow
    "QAQuestion",
    "QAAnswer",
    # Document Engagement
    "DocumentEngagement",
    "DealEngagementSummary",
    # Covenant & KPI Monitoring
    "Covenant",
    "KPIActual",
    "KPITarget",
    # API Keys
    "OrgApiKey",
    # CRM Sync
    "CRMConnection",
    "CRMSyncLog",
    "CRMEntityMapping",
    # Cashflow Pacing
    "CashflowAssumption",
    "CashflowProjection",
    # Industry Taxonomy & Financial Templates
    "IndustryTaxonomy",
    "FinancialTemplate",
    # Score Backtesting
    "DealOutcome",
    "BacktestRun",
    # Expert Insights
    "ExpertNote",
    # Webhooks
    "WebhookSubscription",
    "WebhookDelivery",
    # Document Annotations
    "DocumentAnnotation",
    # AI Document Redaction
    "RedactionJob",
    # External Market Data
    "ExternalDataPoint",
    # Launch Preparation (E04)
    "FeatureFlag",
    "FeatureFlagOverride",
    "UsageEvent",
    "WaitlistEntry",
    # Custom Domain (E03)
    "CustomDomain",
    # Digest History
    "DigestLog",
]
