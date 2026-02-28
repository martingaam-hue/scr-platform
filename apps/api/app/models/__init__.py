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
]
