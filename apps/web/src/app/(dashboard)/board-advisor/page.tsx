"use client";

import { useState } from "react";
import { Briefcase, CheckCircle2, Star, Users, Filter, Search, Globe, Award } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  EmptyState,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@scr/ui";
import { InfoBanner } from "@/components/info-banner";
import {
  APPLICATION_STATUS_LABELS,
  AVAILABILITY_LABELS,
  applicationStatusBadge,
  useAdvisorApplications,
  useAdvisorSearch,
  useUpdateApplicationStatus,
  type AdvisorSearchResult,
} from "@/lib/board-advisor";

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
              <div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
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
