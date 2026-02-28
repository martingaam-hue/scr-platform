"use client";

import Link from "next/link";
import {
  ArrowRight,
  Calendar,
  CheckCircle2,
  Clock,
  Construction,
  Loader2,
  Monitor,
  Package,
} from "lucide-react";
import { Badge, Button, Card, CardContent, EmptyState, cn } from "@scr/ui";
import { useProjects } from "@/lib/projects";
import { useDevelopmentOS } from "@/lib/development-os";

// ── Project Dev Card ──────────────────────────────────────────────────────────

function ProjectDevCard({ project }: { project: { id: string; name: string; stage: string; project_type: string } }) {
  const { data, isLoading } = useDevelopmentOS(project.id);

  const completion = data?.overall_completion_pct ?? null;
  const nextMilestone = data?.next_milestone ?? null;
  const daysToNext = data?.days_to_next_milestone ?? null;

  const phaseStatusColor = (s: string) => {
    switch (s) {
      case "completed": return "bg-green-500";
      case "in_progress": return "bg-indigo-500";
      case "delayed": return "bg-red-500";
      default: return "bg-gray-300";
    }
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-5 space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="font-semibold text-gray-900 leading-tight">{project.name}</p>
            <p className="text-xs text-gray-500 capitalize mt-0.5">
              {project.project_type.replace(/_/g, " ")} · {project.stage.replace(/_/g, " ")}
            </p>
          </div>
          {completion !== null && (
            <div className="text-right flex-shrink-0">
              <p className="text-lg font-bold text-indigo-600">{completion.toFixed(0)}%</p>
              <p className="text-xs text-gray-400">complete</p>
            </div>
          )}
        </div>

        {/* Progress bar */}
        {completion !== null && (
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-indigo-500 rounded-full transition-all"
              style={{ width: `${Math.min(100, completion)}%` }}
            />
          </div>
        )}

        {/* Phase dots */}
        {isLoading ? (
          <div className="flex items-center gap-1.5">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-2 flex-1 bg-gray-200 rounded-full animate-pulse" />
            ))}
          </div>
        ) : data?.phases && data.phases.length > 0 ? (
          <div className="flex items-center gap-1">
            {data.phases.slice(0, 6).map((phase, i) => (
              <div
                key={i}
                className={cn("h-2 flex-1 rounded-full", phaseStatusColor(phase.status))}
                title={`${phase.phase_name}: ${phase.completion_pct.toFixed(0)}%`}
              />
            ))}
          </div>
        ) : null}

        {/* Next milestone */}
        {nextMilestone && (
          <div className="flex items-center gap-2 text-xs text-gray-600 bg-gray-50 rounded-lg p-2.5">
            <Calendar className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
            <span className="truncate">
              Next: <span className="font-medium">{nextMilestone.title}</span>
            </span>
            {daysToNext !== null && (
              <Badge
                variant={daysToNext <= 7 ? "warning" : "neutral"}
                className="text-xs ml-auto flex-shrink-0"
              >
                {daysToNext === 0 ? "Today" : `${daysToNext}d`}
              </Badge>
            )}
          </div>
        )}

        {/* Open button */}
        <Link href={`/development-os/${project.id}`}>
          <Button size="sm" variant="outline" className="w-full">
            Open Dev OS <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
          </Button>
        </Link>
      </CardContent>
    </Card>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DevelopmentOSPage() {
  const { data, isLoading } = useProjects({ page_size: 50 });
  const projects = data?.items ?? [];

  // Separate by stage bucket: construction-phase vs earlier
  const activeProjects = projects.filter(
    (p) => !["concept", "archived"].includes(p.stage ?? "")
  );
  const earlyProjects = projects.filter((p) => p.stage === "concept");

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 flex items-center gap-2">
            <Monitor className="h-6 w-6 text-indigo-500" />
            Development OS
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Construction lifecycle, milestones, and procurement across all projects
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
        </div>
      ) : projects.length === 0 ? (
        <EmptyState
          title="No projects yet"
          description="Create your first project to start tracking its development lifecycle."
          action={
            <Button asChild>
              <Link href="/projects/new">New Project</Link>
            </Button>
          }
        />
      ) : (
        <div className="space-y-6">
          {activeProjects.length > 0 && (
            <section>
              <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">
                Active Projects ({activeProjects.length})
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {activeProjects.map((p) => (
                  <ProjectDevCard
                    key={p.id}
                    project={{ id: p.id, name: p.name, stage: p.stage ?? "concept", project_type: p.project_type }}
                  />
                ))}
              </div>
            </section>
          )}

          {earlyProjects.length > 0 && (
            <section>
              <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">
                Concept Stage ({earlyProjects.length})
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {earlyProjects.map((p) => (
                  <ProjectDevCard
                    key={p.id}
                    project={{ id: p.id, name: p.name, stage: p.stage ?? "concept", project_type: p.project_type }}
                  />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
