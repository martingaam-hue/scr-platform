"use client";

import { useState } from "react";
import {
  Briefcase,
  CheckCircle2,
  Star,
  Users,
  Filter,
  Search,
  Globe,
  Award,
  DollarSign,
  Building2,
  Lightbulb,
  Shield,
  Target,
  UserPlus,
  X,
  type LucideIcon,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  EmptyState,
  InfoBanner,
  LoadingSpinner,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@scr/ui";
import {
  APPLICATION_STATUS_LABELS,
  AVAILABILITY_LABELS,
  applicationStatusBadge,
  useAdvisorApplications,
  useAdvisorSearch,
  useUpdateApplicationStatus,
  type AdvisorSearchResult,
} from "@/lib/board-advisor";

// ── Types ──────────────────────────────────────────────────────────────────────

interface ExpertiseCategory {
  id: string;
  title: string;
  description: string;
  icon: LucideIcon;
  iconBg: string;
  iconColor: string;
  accentColor: string;
  available: number;
  impact: number;
}

interface CategoryAdvisor {
  id: string;
  name: string;
  title: string;
  org: string;
  experience: string;
  matchScore: number;
}

// ── Mock data ─────────────────────────────────────────────────────────────────

const MOCK_ADVISORS = [
  {
    id: "adv-001",
    match_score: 94,
    name: "Dr. Katrin Müller",
    title: "Former CFO, pan-European Infrastructure Fund",
    bio: "Former CFO of a pan-European renewable energy infrastructure fund with 18 years experience in project finance, LP relations, and cross-border M&A.",
    expertise_areas: { "Project Finance": 1, "Renewable Energy": 1, "M&A": 1, "LP Relations": 1 },
    board_positions_held: 7,
    availability_status: "available",
    avg_rating: 4.8,
    verified: true,
    geography: "Germany / EU",
    languages: ["English", "German", "French"],
    platform_member: true,
  },
  {
    id: "adv-002",
    match_score: 88,
    name: "Lars Eriksson",
    title: "Head of Infrastructure, Nordic Pension Fund",
    bio: "Independent board member and former Head of Infrastructure at a Nordic pension fund. Deep expertise in ESG governance and Article 9 compliance frameworks.",
    expertise_areas: { "ESG Governance": 1, "Pension Funds": 1, "Article 9": 1 },
    board_positions_held: 5,
    availability_status: "available",
    avg_rating: 4.6,
    verified: true,
    geography: "Sweden / Nordics",
    languages: ["English", "Swedish"],
    platform_member: true,
  },
  {
    id: "adv-003",
    match_score: 82,
    name: "Sarah O'Brien",
    title: "Wind Energy Specialist & Technical Advisor",
    bio: "Energy transition specialist with operational background running wind farm portfolios in Scandinavia and the UK. Technical advisory and board roles across 12 projects.",
    expertise_areas: { "Wind Energy": 1, "Operations": 1, "Technical Advisory": 1 },
    board_positions_held: 12,
    availability_status: "limited",
    avg_rating: 4.4,
    verified: true,
    geography: "UK / Scandinavia",
    languages: ["English"],
    platform_member: true,
  },
  {
    id: "adv-004",
    match_score: 76,
    name: "Mauro Ferretti",
    title: "Partner, Energy Regulatory Law",
    bio: "Partner at a European infrastructure law firm, specialising in energy regulation, grid connection agreements, and PPAs across EU jurisdictions.",
    expertise_areas: { "Energy Law": 1, "PPA Structuring": 1, "Regulation": 1 },
    board_positions_held: 4,
    availability_status: "available",
    avg_rating: 4.5,
    verified: false,
    geography: "Italy / EU",
    languages: ["English", "Italian"],
    platform_member: false,
  },
  {
    id: "adv-005",
    match_score: 71,
    name: "Yuki Tanaka",
    title: "CTO & Digital Transformation, Asset Management",
    bio: "Digital transformation and asset management technology advisor. Previously CTO at a large infra asset manager. Focused on data and AI integration in portfolio management.",
    expertise_areas: { "Technology": 1, "Asset Management": 1, "AI": 1 },
    board_positions_held: 3,
    availability_status: "unavailable",
    avg_rating: 4.2,
    verified: false,
    geography: "Japan / Global",
    languages: ["English", "Japanese"],
    platform_member: false,
  },
  {
    id: "adv-006",
    match_score: 79,
    name: "Amara Diallo",
    title: "Development Finance & Impact Investing",
    bio: "Former senior director at the African Development Bank. Expert in blended finance, DFI co-investment structures, and impact measurement frameworks.",
    expertise_areas: { "Development Finance": 1, "Blended Finance": 1, "Impact Measurement": 1 },
    board_positions_held: 8,
    availability_status: "available",
    avg_rating: 4.7,
    verified: true,
    geography: "Senegal / West Africa",
    languages: ["English", "French"],
    platform_member: true,
  },
] as unknown as (AdvisorSearchResult & {
  name?: string;
  title?: string;
  geography?: string;
  languages?: string[];
  platform_member?: boolean;
})[];

const MOCK_APPLICATIONS = [
  {
    id: "app-001",
    role_offered: "Independent Board Member — Baltic BESS Grid Storage",
    project_id: "proj-bess-001",
    message: "I have direct experience with grid-scale BESS projects in the Baltic region and would welcome the opportunity to contribute to the board oversight of this asset.",
    status: "pending" as const,
    equity_offered: null,
  },
  {
    id: "app-002",
    role_offered: "Advisory Board Member — ESG & Sustainability",
    project_id: "proj-alpine-005",
    message: "Given my background in ESG governance for Swiss infrastructure projects, I believe I can add value to Alpine Hydro's sustainability committee.",
    status: "accepted" as const,
    equity_offered: null,
  },
  {
    id: "app-003",
    role_offered: "Finance Committee Advisor — Nordvik Wind Farm II",
    project_id: "proj-wind-002",
    message: "Happy to support the refinancing process with LP reporting expertise.",
    status: "pending" as const,
    equity_offered: null,
  },
];

// ── Suggested expertise data ──────────────────────────────────────────────────

const EXPERTISE_CATEGORIES: ExpertiseCategory[] = [
  {
    id: "financial",
    title: "Financial Expertise",
    description: "CFO-level financial strategy, fundraising, and investor relations",
    icon: DollarSign,
    iconBg: "bg-green-100",
    iconColor: "text-green-600",
    accentColor: "#22c55e",
    available: 12,
    impact: 1.5,
  },
  {
    id: "industry",
    title: "Industry Veteran",
    description: "Deep sector experience and market knowledge",
    icon: Building2,
    iconBg: "bg-blue-100",
    iconColor: "text-blue-600",
    accentColor: "#3b82f6",
    available: 8,
    impact: 1.5,
  },
  {
    id: "technical",
    title: "Technical Leadership",
    description: "CTO-level technical guidance and innovation strategy",
    icon: Lightbulb,
    iconBg: "bg-indigo-100",
    iconColor: "text-indigo-700",
    accentColor: "#4338ca",
    available: 15,
    impact: 1.3,
  },
  {
    id: "regulatory",
    title: "Regulatory & Legal",
    description: "Compliance, regulatory navigation, and legal frameworks",
    icon: Shield,
    iconBg: "bg-amber-100",
    iconColor: "text-amber-600",
    accentColor: "#f59e0b",
    available: 6,
    impact: 1.0,
  },
  {
    id: "strategic",
    title: "Strategic Growth",
    description: "Business development, partnerships, and scaling expertise",
    icon: Target,
    iconBg: "bg-emerald-100",
    iconColor: "text-emerald-600",
    accentColor: "#10b981",
    available: 10,
    impact: 1.4,
  },
  {
    id: "international",
    title: "International Expansion",
    description: "Global market entry and cross-border operations",
    icon: Globe,
    iconBg: "bg-teal-100",
    iconColor: "text-teal-600",
    accentColor: "#14b8a6",
    available: 7,
    impact: 1.1,
  },
];

// Sorted highest impact first (already ordered above, kept explicit)
const SORTED_EXPERTISE = [...EXPERTISE_CATEGORIES].sort((a, b) => b.impact - a.impact);

const CATEGORY_ADVISORS: Record<string, CategoryAdvisor[]> = {
  financial: [
    {
      id: "f1",
      name: "Henrik Larsson",
      title: "CFO",
      org: "Nordic Green Capital",
      experience: "15 years infrastructure finance",
      matchScore: 96,
    },
    {
      id: "f2",
      name: "Maria Santos",
      title: "Partner",
      org: "Iberian Ventures",
      experience: "IPO and M&A specialist",
      matchScore: 91,
    },
    {
      id: "f3",
      name: "Thomas Weber",
      title: "Director",
      org: "Deutsche Infra Bank",
      experience: "Project finance structuring",
      matchScore: 87,
    },
  ],
  industry: [
    {
      id: "i1",
      name: "Jean-Pierre Moreau",
      title: "Former CEO",
      org: "EDF Renewables",
      experience: "25 years energy sector leadership",
      matchScore: 98,
    },
    {
      id: "i2",
      name: "Ingrid Haugen",
      title: "Board Member",
      org: "Statkraft",
      experience: "Nordic energy markets expert",
      matchScore: 93,
    },
    {
      id: "i3",
      name: "Paolo Bianchi",
      title: "Managing Director",
      org: "Enel Green Power",
      experience: "Southern European renewables",
      matchScore: 88,
    },
  ],
  technical: [
    {
      id: "t1",
      name: "Dr. Akira Tanaka",
      title: "CTO",
      org: "SolarTech Global",
      experience: "PV technology and grid integration",
      matchScore: 94,
    },
    {
      id: "t2",
      name: "Fiona MacGregor",
      title: "VP Engineering",
      org: "Vestas",
      experience: "Wind turbine technology",
      matchScore: 90,
    },
    {
      id: "t3",
      name: "Lars Nilsson",
      title: "Chief Architect",
      org: "Northvolt",
      experience: "Battery storage systems",
      matchScore: 85,
    },
  ],
  regulatory: [
    {
      id: "r1",
      name: "Dr. Elise Beaumont",
      title: "Senior Partner",
      org: "Linklaters Energy",
      experience: "EU energy regulatory frameworks",
      matchScore: 95,
    },
    {
      id: "r2",
      name: "Carlos Navarro",
      title: "Head of Compliance",
      org: "Iberdrola Group",
      experience: "Permitting and grid connection",
      matchScore: 89,
    },
    {
      id: "r3",
      name: "Annika Berg",
      title: "Partner",
      org: "Mannheimer Swartling",
      experience: "Nordic energy law and PPAs",
      matchScore: 83,
    },
  ],
  strategic: [
    {
      id: "s1",
      name: "Rolf Hansen",
      title: "Chief Strategy Officer",
      org: "Ørsted",
      experience: "Offshore wind scaling and partnerships",
      matchScore: 92,
    },
    {
      id: "s2",
      name: "Nadia Al-Rashid",
      title: "Partner",
      org: "McKinsey Sustainability",
      experience: "Clean energy growth strategy",
      matchScore: 88,
    },
    {
      id: "s3",
      name: "Victor Osei",
      title: "VP Business Development",
      org: "Mainstream Renewable Power",
      experience: "Emerging market project development",
      matchScore: 84,
    },
  ],
  international: [
    {
      id: "x1",
      name: "Sophia Chen",
      title: "Managing Director",
      org: "APAC Infrastructure Partners",
      experience: "Cross-border energy investment",
      matchScore: 91,
    },
    {
      id: "x2",
      name: "Mohammed Al-Farsi",
      title: "Director",
      org: "MENA Clean Energy Fund",
      experience: "Middle East and North Africa renewables",
      matchScore: 86,
    },
    {
      id: "x3",
      name: "Isabela Rodrigues",
      title: "Partner",
      org: "Vinci Energies Brasil",
      experience: "Latin American market entry",
      matchScore: 82,
    },
  ],
};

// ── Expertise card ─────────────────────────────────────────────────────────────

function ExpertiseCategoryCard({
  category,
  onApply,
}: {
  category: ExpertiseCategory;
  onApply: (id: string) => void;
}) {
  const Icon = category.icon;
  return (
    <div
      className="bg-white rounded-xl border border-neutral-200 overflow-hidden hover:shadow-md transition-shadow flex flex-col"
      style={{ borderLeftColor: category.accentColor, borderLeftWidth: 3 }}
    >
      <div className="p-4 flex-1">
        {/* Top row: icon + available badge */}
        <div className="flex items-start justify-between mb-3">
          <div className={`p-2 rounded-full ${category.iconBg}`}>
            <Icon className={`h-4 w-4 ${category.iconColor}`} />
          </div>
          <span className="text-[10px] font-semibold bg-neutral-100 text-neutral-500 rounded-full px-2 py-0.5 uppercase tracking-wide">
            {category.available} available
          </span>
        </div>

        {/* Title + description */}
        <p className="text-sm font-bold text-neutral-900 mb-1">{category.title}</p>
        <p className="text-xs text-neutral-500 leading-relaxed">{category.description}</p>
      </div>

      {/* Footer band */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-green-50/60 border-t border-neutral-100">
        <div>
          <p className="text-[10px] text-neutral-400 uppercase tracking-wide font-semibold">
            Signal Score Impact
          </p>
          <p className="text-sm font-bold text-green-600">
            +{category.impact.toFixed(1)}
          </p>
        </div>
        <Button
          size="sm"
          variant="outline"
          className="text-xs h-7 gap-1"
          onClick={() => onApply(category.id)}
        >
          <UserPlus className="h-3 w-3" />
          Apply
        </Button>
      </div>
    </div>
  );
}

// ── Suggested expertise section ────────────────────────────────────────────────

function SuggestedBoardSupportSection({ onApply }: { onApply: (id: string) => void }) {
  return (
    <div className="space-y-4">
      {/* Section header */}
      <div className="flex items-center gap-3">
        <div className="p-1.5 bg-amber-100 rounded-lg">
          <Star className="h-4 w-4 text-amber-500" />
        </div>
        <div>
          <p className="text-base font-bold text-neutral-900">Suggested Board Support Members</p>
          <p className="text-xs text-neutral-500">Strategic expertise areas to strengthen your team</p>
        </div>
        <div className="ml-auto">
          <span className="text-[10px] font-semibold bg-blue-50 text-blue-600 border border-blue-200 rounded-full px-3 py-1 uppercase tracking-wide">
            AI-Powered
          </span>
        </div>
      </div>

      {/* Analysis context pill */}
      <div className="flex items-center gap-2 text-xs text-neutral-500 bg-neutral-50 rounded-lg px-3 py-2 border border-neutral-100">
        <Lightbulb className="h-3.5 w-3.5 text-amber-400 shrink-0" />
        <span>
          Recommendations based on Signal Score dimension gaps, risk profile, project stage, and sector analysis.
          Sorted by highest estimated score impact.
        </span>
      </div>

      {/* 3×2 grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {SORTED_EXPERTISE.map((cat) => (
          <ExpertiseCategoryCard key={cat.id} category={cat} onApply={onApply} />
        ))}
      </div>
    </div>
  );
}

// ── Advisor modal ──────────────────────────────────────────────────────────────

function CategoryAdvisorsModal({
  categoryId,
  onClose,
}: {
  categoryId: string;
  onClose: () => void;
}) {
  const category = EXPERTISE_CATEGORIES.find((c) => c.id === categoryId);
  const advisors = CATEGORY_ADVISORS[categoryId] ?? [];
  if (!category) return null;
  const Icon = category.icon;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden">
        {/* Header */}
        <div
          className="px-5 py-4 flex items-center justify-between"
          style={{ borderBottom: `3px solid ${category.accentColor}` }}
        >
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-full ${category.iconBg}`}>
              <Icon className={`h-4 w-4 ${category.iconColor}`} />
            </div>
            <div>
              <p className="text-sm font-bold text-neutral-900">{category.title}</p>
              <p className="text-xs text-neutral-500">{advisors.length} advisors available</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-full p-1.5 hover:bg-neutral-100 transition-colors text-neutral-500"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Advisor list */}
        <div className="divide-y divide-neutral-100 max-h-[60vh] overflow-y-auto">
          {advisors.map((adv) => (
            <div key={adv.id} className="px-5 py-4 flex items-center gap-4 hover:bg-neutral-50 transition-colors">
              {/* Score bubble */}
              <div
                className="h-10 w-10 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0"
                style={{ backgroundColor: category.accentColor }}
              >
                {adv.matchScore}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-neutral-900">{adv.name}</p>
                <p className="text-xs text-neutral-500 truncate">
                  {adv.title} · {adv.org}
                </p>
                <p className="text-[11px] text-neutral-400 mt-0.5">{adv.experience}</p>
              </div>

              {/* CTA */}
              <Button size="sm" variant="outline" className="text-xs h-7 shrink-0">
                Request Intro
              </Button>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 bg-neutral-50 border-t border-neutral-100 flex items-center justify-between">
          <p className="text-xs text-neutral-400">
            Signal Score impact: <span className="font-bold text-green-600">+{category.impact.toFixed(1)}</span> estimated
          </p>
          <Button size="sm" onClick={onClose} variant="outline" className="text-xs">
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Advisor card ──────────────────────────────────────────────────────────────

function AdvisorCard({ advisor }: {
  advisor: AdvisorSearchResult & {
    name?: string; title?: string; geography?: string; languages?: string[]; platform_member?: boolean;
  }
}) {
  const expertise = advisor.expertise_areas
    ? Object.keys(advisor.expertise_areas).slice(0, 3)
    : [];

  const availColor =
    advisor.availability_status === "available" ? "success" :
    advisor.availability_status === "limited" ? "warning" : "neutral";

  return (
    <Card className="overflow-hidden hover:shadow-md transition-all border-neutral-200">
      {/* Score accent bar */}
      <div
        className="h-1"
        style={{
          background:
            advisor.match_score >= 90 ? "#22c55e" :
            advisor.match_score >= 75 ? "#3b82f6" :
            advisor.match_score >= 60 ? "#f59e0b" : "#9ca3af",
        }}
      />
      <CardContent className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-0.5">
              {advisor.verified && (
                <CheckCircle2 className="h-3.5 w-3.5 text-green-500 shrink-0" />
              )}
              {(advisor as { platform_member?: boolean }).platform_member && (
                <Badge variant="info" className="text-[10px] px-1.5 py-0">Platform Member</Badge>
              )}
            </div>
            <p className="text-sm font-bold text-neutral-900">
              {(advisor as { name?: string }).name ?? "Board Advisor"}
            </p>
            <p className="text-xs text-neutral-500 mt-0.5">
              {(advisor as { title?: string }).title}
            </p>
          </div>
          <div className="text-right shrink-0 ml-3">
            <p className="text-2xl font-bold text-primary-600">{advisor.match_score}</p>
            <p className="text-[10px] text-neutral-400 font-medium uppercase tracking-wide">match</p>
          </div>
        </div>

        <p className="text-xs text-neutral-600 line-clamp-2 mb-3 leading-relaxed">
          {advisor.bio}
        </p>

        {/* Expertise tags */}
        <div className="flex flex-wrap gap-1 mb-3">
          {expertise.map((e) => (
            <span key={e} className="text-[10px] bg-neutral-100 text-neutral-600 rounded-md px-1.5 py-0.5 font-medium">
              {e}
            </span>
          ))}
        </div>

        {/* Meta row */}
        <div className="flex items-center gap-3 text-xs text-neutral-400 mb-3">
          <span className="flex items-center gap-1">
            <Briefcase className="h-3 w-3" />
            {advisor.board_positions_held} positions
          </span>
          {(advisor as { geography?: string }).geography && (
            <span className="flex items-center gap-1">
              <Globe className="h-3 w-3" />
              {(advisor as { geography?: string }).geography}
            </span>
          )}
          {advisor.avg_rating != null && (
            <span className="flex items-center gap-1 ml-auto">
              <Star className="h-3 w-3 text-amber-400" />
              {advisor.avg_rating.toFixed(1)}
            </span>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between">
          <Badge variant={availColor}>
            {AVAILABILITY_LABELS[advisor.availability_status] ?? advisor.availability_status}
          </Badge>
          <Button size="sm" variant="outline" className="text-xs h-7">
            Request Intro
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function BoardAdvisorPage() {
  const [expertise, setExpertise] = useState("");
  const [availFilter, setAvailFilter] = useState<"all" | "available" | "limited" | "unavailable">("all");
  const [platformOnly, setPlatformOnly] = useState(false);
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(null);

  const { data: advisorsData = [], isLoading } = useAdvisorSearch(expertise || undefined);
  const rawAdvisors = advisorsData.length > 0 ? advisorsData : MOCK_ADVISORS;

  // Apply client-side filters
  const advisors = rawAdvisors.filter((a) => {
    if (availFilter !== "all" && a.availability_status !== availFilter) return false;
    if (platformOnly && !(a as { platform_member?: boolean }).platform_member) return false;
    return true;
  });

  const { data: applicationsData = [] } = useAdvisorApplications();
  const applications = applicationsData.length > 0 ? applicationsData : MOCK_APPLICATIONS;
  const updateStatus = useUpdateApplicationStatus();

  const availCounts = {
    available: rawAdvisors.filter((a) => a.availability_status === "available").length,
    limited: rawAdvisors.filter((a) => a.availability_status === "limited").length,
    unavailable: rawAdvisors.filter((a) => a.availability_status === "unavailable").length,
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-primary-100 rounded-lg">
          <Briefcase className="h-6 w-6 text-primary-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Board Advisor Network</h1>
          <p className="text-sm text-neutral-500 mt-0.5">
            Find and connect with experienced board advisors for your projects.
          </p>
        </div>
      </div>

      <InfoBanner>
        The <strong>Board Advisor Program</strong> connects you with experienced professionals who can
        serve on your project boards. Filter by expertise and availability, and use{" "}
        <strong>Platform Members</strong> to find advisors already verified within the SCR network.
      </InfoBanner>

      {/* ── AI-Suggested Board Support ──────────────────────────────────────── */}
      <SuggestedBoardSupportSection onApply={setSelectedCategoryId} />

      {/* ── Advisor modal ──────────────────────────────────────────────────── */}
      {selectedCategoryId && (
        <CategoryAdvisorsModal
          categoryId={selectedCategoryId}
          onClose={() => setSelectedCategoryId(null)}
        />
      )}

      {/* ── Search & Applications tabs ─────────────────────────────────────── */}
      <Tabs defaultValue="find">
        <TabsList>
          <TabsTrigger value="find">
            <Search className="h-3.5 w-3.5 mr-1.5" />
            Find Advisors
          </TabsTrigger>
          <TabsTrigger value="applications">
            <Award className="h-3.5 w-3.5 mr-1.5" />
            Applications ({applications.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="find" className="space-y-5 mt-5">
          {/* Search + filters bar */}
          <div className="flex flex-wrap gap-3 items-end p-4 bg-neutral-50 rounded-xl border border-neutral-200">
            <div className="flex-1 min-w-[200px]">
              <label className="block text-xs font-semibold text-neutral-500 mb-1.5 uppercase tracking-wide">
                Expertise Search
              </label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-neutral-400" />
                <input
                  className="w-full rounded-lg border border-neutral-200 pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
                  placeholder="Solar, finance, ESG governance..."
                  value={expertise}
                  onChange={(e) => setExpertise(e.target.value)}
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-500 mb-1.5 uppercase tracking-wide">
                Availability
              </label>
              <select
                value={availFilter}
                onChange={(e) => setAvailFilter(e.target.value as typeof availFilter)}
                className="rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 bg-white"
              >
                <option value="all">All ({rawAdvisors.length})</option>
                <option value="available">Available ({availCounts.available})</option>
                <option value="limited">Limited ({availCounts.limited})</option>
                <option value="unavailable">Unavailable ({availCounts.unavailable})</option>
              </select>
            </div>

            <div className="flex items-center gap-2 mt-auto pb-0.5">
              <input
                type="checkbox"
                id="platform-only"
                checked={platformOnly}
                onChange={(e) => setPlatformOnly(e.target.checked)}
                className="rounded border-neutral-300 text-primary-600 focus:ring-primary-400"
              />
              <label htmlFor="platform-only" className="text-sm text-neutral-600 cursor-pointer select-none">
                Platform members only
              </label>
            </div>

            <div className="flex items-center gap-2 ml-auto text-xs text-neutral-400">
              <Filter className="h-3.5 w-3.5" />
              <span>{advisors.length} advisor{advisors.length !== 1 ? "s" : ""} shown</span>
            </div>
          </div>

          {/* Quick filter chips */}
          <div className="flex gap-2 flex-wrap">
            {["Project Finance", "ESG", "Wind", "Solar", "Legal", "Operations", "LP Relations"].map((chip) => (
              <button
                key={chip}
                onClick={() => setExpertise(expertise === chip ? "" : chip)}
                className={`text-xs px-3 py-1.5 rounded-full border transition-colors font-medium ${
                  expertise === chip
                    ? "border-primary-400 bg-primary-50 text-primary-700"
                    : "border-neutral-200 bg-white text-neutral-500 hover:border-neutral-300"
                }`}
              >
                {chip}
              </button>
            ))}
          </div>

          {/* Advisor grid */}
          {isLoading && advisorsData.length === 0 ? (
            <div className="flex h-40 items-center justify-center">
              <LoadingSpinner className="h-6 w-6" />
            </div>
          ) : advisors.length === 0 ? (
            <EmptyState
              icon={<Users className="h-10 w-10 text-neutral-400" />}
              title="No advisors match"
              description="Try adjusting your search or availability filter."
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {advisors.map((a) => (
                <AdvisorCard key={a.id} advisor={a as typeof MOCK_ADVISORS[0]} />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="applications" className="space-y-4 mt-5">
          {applications.length === 0 ? (
            <EmptyState
              icon={<Briefcase className="h-10 w-10 text-neutral-400" />}
              title="No applications yet"
              description="Applications from board advisors will appear here."
            />
          ) : (
            <div className="space-y-3">
              {applications.map((app) => (
                <Card key={app.id}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <p className="text-sm font-semibold text-neutral-800">
                          {app.role_offered}
                        </p>
                        <p className="text-xs text-neutral-400 mt-0.5">
                          Project · {app.project_id.slice(0, 12)}…
                        </p>
                        {app.message && (
                          <p className="text-xs text-neutral-600 mt-2 leading-relaxed line-clamp-2">
                            {app.message}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <Badge variant={applicationStatusBadge(app.status)}>
                          {APPLICATION_STATUS_LABELS[app.status] ?? app.status}
                        </Badge>
                        {app.status === "pending" && (
                          <div className="flex gap-1">
                            <Button
                              size="sm"
                              onClick={() => updateStatus.mutate({ applicationId: app.id, status: "accepted" })}
                              disabled={updateStatus.isPending}
                            >
                              Accept
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => updateStatus.mutate({ applicationId: app.id, status: "rejected" })}
                              disabled={updateStatus.isPending}
                            >
                              Reject
                            </Button>
                          </div>
                        )}
                      </div>
                    </div>
                    {app.equity_offered != null && (
                      <p className="text-xs text-neutral-500 mt-2">
                        Equity offered: {app.equity_offered}%
                      </p>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
