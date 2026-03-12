"use client";

import { ShieldAlert } from "lucide-react";
import { RiskDashboardView } from "@/components/risk/risk-dashboard-view";
import { InfoBanner } from "@/components/info-banner";

export default function RiskDashboardPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-primary-100 rounded-lg">
          <ShieldAlert className="h-6 w-6 text-primary-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">
            Risk Dashboard
          </h1>
          <p className="text-sm text-neutral-500 mt-0.5">
            Portfolio-wide risk monitoring, mitigation strategies and development advisor
          </p>
        </div>
      </div>

      <InfoBanner>
        The <strong>Risk Dashboard</strong> provides a unified view of all risk factors across
        your portfolio — from critical alerts and severity breakdowns to AI-generated mitigation
        strategies. Select a project to drill into individual risk items, generate targeted
        mitigation plans, or run the development advisor.
      </InfoBanner>

      <RiskDashboardView />
    </div>
  );
}
