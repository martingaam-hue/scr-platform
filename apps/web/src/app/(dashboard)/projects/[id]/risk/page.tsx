"use client";

import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, ShieldAlert } from "lucide-react";
import { RiskDashboardView } from "@/components/risk/risk-dashboard-view";
import { InfoBanner } from "@scr/ui";

export default function ProjectRiskPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  return (
    <div className="space-y-6">
      <button
        onClick={() => router.push(`/projects/${id}`)}
        className="flex items-center gap-1 text-sm text-neutral-500 hover:text-neutral-700"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Project
      </button>

      <div className="flex items-center gap-3">
        <div className="p-2 bg-red-50 rounded-lg">
          <ShieldAlert className="h-6 w-6 text-red-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Risk Dashboard</h1>
          <p className="text-sm text-neutral-500 mt-0.5">
            Risk monitoring, severity breakdown, mitigation strategies and development advisor for this project
          </p>
        </div>
      </div>

      <InfoBanner>
        Monitor all risk factors for this project — from active alerts and severity breakdowns
        to AI-generated mitigation strategies. Use the <strong>Mitigation</strong> tab to generate
        targeted action plans, and the <strong>Advisor</strong> tab for development recommendations.
      </InfoBanner>

      <RiskDashboardView projectId={id} />
    </div>
  );
}
