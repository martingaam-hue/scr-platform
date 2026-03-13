"use client";

import { useState } from "react";
import { Briefcase, CheckCircle2, Star, Users } from "lucide-react";
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

const MOCK_ADVISORS: AdvisorSearchResult[] = [
  {
    id: "adv-001",
    match_score: 94,
    bio: "Former CFO of a pan-European renewable energy infrastructure fund with 18 years experience in project finance, LP relations, and cross-border M&A.",
    expertise_areas: { "Project Finance": 1, "Renewable Energy": 1, "M&A": 1, "LP Relations": 1 },
    board_positions_held: 7,
    availability_status: "available",
    avg_rating: 4.8,
    verified: true,
  },
  {
    id: "adv-002",
    match_score: 88,
    bio: "Independent board member and former Head of Infrastructure at a Nordic pension fund. Deep expertise in ESG governance and Article 9 compliance frameworks.",
    expertise_areas: { "ESG Governance": 1, "Pension Funds": 1, "Article 9": 1 },
    board_positions_held: 5,
    availability_status: "available",
    avg_rating: 4.6,
    verified: true,
  },
  {
    id: "adv-003",
    match_score: 82,
    bio: "Energy transition specialist with operational background running wind farm portfolios in Scandinavia and the UK. Technical advisory and board roles across 12 projects.",
    expertise_areas: { "Wind Energy": 1, "Operations": 1, "Technical Advisory": 1 },
    board_positions_held: 12,
    availability_status: "limited",
    avg_rating: 4.4,
    verified: true,
  },
  {
    id: "adv-004",
    match_score: 76,
    bio: "Partner at a European infrastructure law firm, specialising in energy regulation, grid connection agreements, and PPAs across EU jurisdictions.",
    expertise_areas: { "Energy Law": 1, "PPA Structuring": 1, "Regulation": 1 },
    board_positions_held: 4,
    availability_status: "available",
    avg_rating: 4.5,
    verified: false,
  },
  {
    id: "adv-005",
    match_score: 71,
    bio: "Digital transformation and asset management technology advisor. Previously CTO at a large infra asset manager. Focused on data and AI integration in portfolio management.",
    expertise_areas: { "Technology": 1, "Asset Management": 1, "AI": 1 },
    board_positions_held: 3,
    availability_status: "unavailable",
    avg_rating: 4.2,
    verified: false,
  },
];

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

function AdvisorCard({ advisor }: { advisor: AdvisorSearchResult }) {
  const expertise = advisor.expertise_areas
    ? Object.keys(advisor.expertise_areas).slice(0, 3)
    : [];

  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-start justify-between mb-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              {advisor.verified && (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              )}
              <span className="text-sm font-semibold text-neutral-800">
                Board Advisor
              </span>
            </div>
            <p className="text-xs text-neutral-500">
              {advisor.board_positions_held} board position
              {advisor.board_positions_held !== 1 ? "s" : ""} held
            </p>
          </div>
          <div className="text-right">
            <p className="text-lg font-bold text-primary-600">
              {advisor.match_score}
            </p>
            <p className="text-xs text-neutral-400">match score</p>
          </div>
        </div>
        <p className="text-sm text-neutral-600 line-clamp-2 mb-3">
          {advisor.bio}
        </p>
        <div className="flex flex-wrap gap-1 mb-3">
          {expertise.map((e) => (
            <Badge key={e} variant="neutral" className="text-xs">
              {e}
            </Badge>
          ))}
        </div>
        <div className="flex items-center justify-between">
          <Badge
            variant={
              advisor.availability_status === "available" ? "success" : "neutral"
            }
          >
            {AVAILABILITY_LABELS[advisor.availability_status] ??
              advisor.availability_status}
          </Badge>
          {advisor.avg_rating != null && (
            <span className="flex items-center gap-1 text-xs text-neutral-500">
              <Star className="h-3 w-3 text-amber-400" />
              {advisor.avg_rating.toFixed(1)}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default function BoardAdvisorPage() {
  const [expertise, setExpertise] = useState("");
  const { data: advisorsData = [], isLoading } = useAdvisorSearch(
    expertise || undefined
  );
  const advisors = advisorsData.length > 0 ? advisorsData : MOCK_ADVISORS;
  const { data: applicationsData = [] } = useAdvisorApplications();
  const applications = applicationsData.length > 0 ? applicationsData : MOCK_APPLICATIONS;
  const updateStatus = useUpdateApplicationStatus();

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-primary-100 rounded-lg">
          <Briefcase className="h-6 w-6 text-primary-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">
            Board Advisor Network
          </h1>
          <p className="text-sm text-neutral-500 mt-1">
            Find and connect with experienced board advisors for your projects.
          </p>
        </div>
      </div>

      <InfoBanner>
        The <strong>Board Advisor Program</strong> connects you with experienced professionals who can
        serve on your project boards. Use the <strong>Find Advisors</strong> tab to search by
        expertise area, and the <strong>Applications</strong> tab to review and respond to incoming
        advisor applications.
      </InfoBanner>

      <Tabs defaultValue="find">
        <TabsList>
          <TabsTrigger value="find">Find Advisors</TabsTrigger>
          <TabsTrigger value="applications">
            Applications ({applications.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="find" className="space-y-4 mt-4">
          <div className="flex gap-3">
            <input
              className="flex-1 rounded-md border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Search by expertise (e.g. solar, finance, operations)..."
              value={expertise}
              onChange={(e) => setExpertise(e.target.value)}
            />
          </div>
          {isLoading && advisorsData.length === 0 ? (
            <div className="flex h-40 items-center justify-center">
              <div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
            </div>
          ) : advisors.length === 0 ? (
            <EmptyState
              icon={<Users className="h-10 w-10 text-neutral-400" />}
              title="No advisors found"
              description="Try adjusting your search criteria."
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {advisors.map((a) => (
                <AdvisorCard key={a.id} advisor={a} />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="applications" className="space-y-4 mt-4">
          {applicationsData.length === 0 && applications.length === 0 ? (
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
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-semibold text-neutral-800">
                          {app.role_offered}
                        </p>
                        <p className="text-xs text-neutral-500 mt-0.5">
                          Project ID: {app.project_id.slice(0, 8)}...
                        </p>
                        {app.message && (
                          <p className="text-xs text-neutral-600 mt-1 line-clamp-2">
                            {app.message}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={applicationStatusBadge(app.status)}>
                          {APPLICATION_STATUS_LABELS[app.status] ?? app.status}
                        </Badge>
                        {app.status === "pending" && (
                          <div className="flex gap-1">
                            <Button
                              size="sm"
                              onClick={() =>
                                updateStatus.mutate({
                                  applicationId: app.id,
                                  status: "accepted",
                                })
                              }
                              disabled={updateStatus.isPending}
                            >
                              Accept
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() =>
                                updateStatus.mutate({
                                  applicationId: app.id,
                                  status: "rejected",
                                })
                              }
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
