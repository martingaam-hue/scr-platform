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
import {
  APPLICATION_STATUS_LABELS,
  AVAILABILITY_LABELS,
  applicationStatusBadge,
  useAdvisorApplications,
  useAdvisorSearch,
  useUpdateApplicationStatus,
  type AdvisorSearchResult,
} from "@/lib/board-advisor";

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
  const { data: advisors = [], isLoading } = useAdvisorSearch(
    expertise || undefined
  );
  const { data: applications = [] } = useAdvisorApplications();
  const updateStatus = useUpdateApplicationStatus();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-neutral-900">
          Board Advisor Network
        </h1>
        <p className="text-sm text-neutral-500 mt-1">
          Find and connect with experienced board advisors for your projects.
        </p>
      </div>

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
          {isLoading ? (
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
