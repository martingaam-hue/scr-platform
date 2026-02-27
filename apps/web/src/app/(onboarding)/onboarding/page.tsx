"use client";

import { useState } from "react";
import {
  Briefcase,
  FolderKanban,
  ArrowRight,
  ArrowLeft,
  Check,
  Building2,
  Rocket,
  Sparkles,
} from "lucide-react";
import { Button, Card, CardContent, Badge, cn } from "@scr/ui";
import { useCompleteOnboarding, type OnboardingData } from "@/lib/onboarding";

// ── Step indicator ──────────────────────────────────────────────────────

const STEPS = [
  { label: "Role", icon: Briefcase },
  { label: "Organization", icon: Building2 },
  { label: "Preferences", icon: Sparkles },
  { label: "First Action", icon: Rocket },
  { label: "All Set!", icon: Check },
];

function StepIndicator({ current }: { current: number }) {
  return (
    <div className="mb-8 flex items-center justify-center gap-2">
      {STEPS.map((s, i) => (
        <div key={s.label} className="flex items-center gap-2">
          <div
            className={cn(
              "flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium transition-colors",
              i < current
                ? "bg-primary-600 text-white"
                : i === current
                  ? "bg-primary-100 text-primary-700 ring-2 ring-primary-600"
                  : "bg-neutral-100 text-neutral-400"
            )}
          >
            {i < current ? (
              <Check className="h-4 w-4" />
            ) : (
              i + 1
            )}
          </div>
          {i < STEPS.length - 1 && (
            <div
              className={cn(
                "h-0.5 w-8",
                i < current ? "bg-primary-600" : "bg-neutral-200"
              )}
            />
          )}
        </div>
      ))}
    </div>
  );
}

// ── Form state ──────────────────────────────────────────────────────────

interface FormState {
  orgType: "investor" | "ally" | null;
  orgName: string;
  orgIndustry: string;
  orgGeography: string;
  orgSize: string;
  orgAum: string;
  // Investor preferences
  sectors: string[];
  geographies: string[];
  stages: string[];
  ticketSizeMin: string;
  ticketSizeMax: string;
  riskTolerance: string;
  // Ally preferences
  primaryTechnology: string;
  targetMarkets: string[];
  developmentStage: string;
  fundingNeeds: string;
  // First action
  firstActionName: string;
  firstActionType: string;
  firstActionGeography: string;
  firstActionInvestment: string;
  skipFirstAction: boolean;
}

const initialState: FormState = {
  orgType: null,
  orgName: "",
  orgIndustry: "",
  orgGeography: "",
  orgSize: "",
  orgAum: "",
  sectors: [],
  geographies: [],
  stages: [],
  ticketSizeMin: "",
  ticketSizeMax: "",
  riskTolerance: "moderate",
  primaryTechnology: "infrastructure",
  targetMarkets: [],
  developmentStage: "concept",
  fundingNeeds: "",
  firstActionName: "",
  firstActionType: "infrastructure",
  firstActionGeography: "",
  firstActionInvestment: "",
  skipFirstAction: false,
};

// ── Option sets ─────────────────────────────────────────────────────────

const INDUSTRY_OPTIONS = [
  "Energy",
  "Infrastructure",
  "Technology",
  "Agriculture",
  "Real Estate",
  "Other",
];

const GEOGRAPHY_OPTIONS = [
  "North America",
  "Europe",
  "Asia Pacific",
  "Latin America",
  "Middle East & Africa",
  "Global",
];

const SECTOR_CHIPS = [
  "Infrastructure",
  "Real Estate",
  "Private Equity",
  "Natural Resources",
  "Private Credit",
  "Digital Assets",
  "Impact Investments",
  "Specialty",
  "Other",
];

const STAGE_CHIPS = [
  "Concept",
  "Development",
  "Construction",
  "Operational",
];

const TECHNOLOGY_OPTIONS = [
  { label: "Infrastructure", value: "infrastructure" },
  { label: "Real Estate", value: "real_estate" },
  { label: "Private Equity", value: "private_equity" },
  { label: "Natural Resources", value: "natural_resources" },
  { label: "Private Credit", value: "private_credit" },
  { label: "Digital Assets", value: "digital_assets" },
  { label: "Impact Investments", value: "impact" },
  { label: "Specialty", value: "specialty" },
  { label: "Other", value: "other" },
];

const STRATEGY_OPTIONS = [
  { label: "Impact", value: "impact" },
  { label: "Growth", value: "growth" },
  { label: "Income", value: "income" },
  { label: "Balanced", value: "balanced" },
];

// ── Main page ───────────────────────────────────────────────────────────

export default function OnboardingPage() {
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<FormState>(initialState);
  const [firstActionStrategy, setFirstActionStrategy] = useState("balanced");
  const completeMutation = useCompleteOnboarding();

  const update = (partial: Partial<FormState>) =>
    setForm((prev) => ({ ...prev, ...partial }));

  const toggleChip = (field: "sectors" | "geographies" | "stages" | "targetMarkets", value: string) => {
    setForm((prev) => {
      const arr = prev[field];
      return {
        ...prev,
        [field]: arr.includes(value)
          ? arr.filter((v) => v !== value)
          : [...arr, value],
      };
    });
  };

  const canAdvance = (): boolean => {
    switch (step) {
      case 0:
        return form.orgType !== null;
      case 1:
        return form.orgName.trim().length > 0;
      case 2:
        return true; // preferences are optional
      case 3:
        return true; // can skip
      case 4:
        return true;
      default:
        return false;
    }
  };

  const handleComplete = () => {
    const data: OnboardingData = {
      org_type: form.orgType!,
      org_name: form.orgName,
      org_industry: form.orgIndustry || undefined,
      org_geography: form.orgGeography || undefined,
      org_size: form.orgType === "ally" ? form.orgSize || undefined : undefined,
      org_aum: form.orgType === "investor" ? form.orgAum || undefined : undefined,
      preferences:
        form.orgType === "investor"
          ? {
              sectors: form.sectors,
              geographies: form.geographies,
              stages: form.stages,
              ticket_size_min: form.ticketSizeMin || "0",
              ticket_size_max: form.ticketSizeMax || "0",
              risk_tolerance: form.riskTolerance,
            }
          : {
              primary_technology: form.primaryTechnology,
              target_markets: form.targetMarkets,
              development_stage: form.developmentStage,
              funding_needs: form.fundingNeeds,
            },
      first_action: form.skipFirstAction
        ? null
        : form.orgType === "investor"
          ? null // investor first action is portfolio — handled backend
          : form.firstActionName
            ? {
                name: form.firstActionName,
                project_type: form.firstActionType,
                geography_country: form.firstActionGeography,
                total_investment_required: form.firstActionInvestment || "0",
              }
            : null,
    };

    // For investor first action, add portfolio data to first_action if not skipped
    if (form.orgType === "investor" && !form.skipFirstAction && form.firstActionName) {
      data.first_action = null; // portfolio is auto-created by backend
      // Override preferences to include portfolio name hint
      data.preferences = {
        ...data.preferences,
        portfolio_name: form.firstActionName,
        portfolio_strategy: firstActionStrategy,
      };
    }

    completeMutation.mutate(data);
  };

  return (
    <div>
      <StepIndicator current={step} />

      {/* Step 1: Role Selection */}
      {step === 0 && (
        <div className="space-y-6">
          <div className="text-center">
            <h1 className="text-3xl font-bold text-neutral-900">
              Welcome to SCR Platform
            </h1>
            <p className="mt-2 text-neutral-500">
              Let&apos;s get you set up. How will you be using the platform?
            </p>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <button
              onClick={() => { update({ orgType: "investor" }); setStep(1); }}
              className={cn(
                "group rounded-xl border-2 p-6 text-left transition-all hover:border-primary-600 hover:shadow-md",
                form.orgType === "investor"
                  ? "border-primary-600 bg-primary-50 shadow-md"
                  : "border-neutral-200 bg-white"
              )}
            >
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-primary-100 text-primary-600">
                <Briefcase className="h-7 w-7" />
              </div>
              <h3 className="text-lg font-semibold text-neutral-900">
                I&apos;m an Investor
              </h3>
              <p className="mt-1 text-sm text-neutral-500">
                Manage portfolios, discover deals, and track investments in
                alternative investment assets.
              </p>
            </button>
            <button
              onClick={() => { update({ orgType: "ally" }); setStep(1); }}
              className={cn(
                "group rounded-xl border-2 p-6 text-left transition-all hover:border-primary-600 hover:shadow-md",
                form.orgType === "ally"
                  ? "border-primary-600 bg-primary-50 shadow-md"
                  : "border-neutral-200 bg-white"
              )}
            >
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-secondary-100 text-secondary-600">
                <FolderKanban className="h-7 w-7" />
              </div>
              <h3 className="text-lg font-semibold text-neutral-900">
                I&apos;m a Project Developer
              </h3>
              <p className="mt-1 text-sm text-neutral-500">
                Showcase your alternative investment assets, manage documents, and
                connect with investors.
              </p>
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Organization Setup */}
      {step === 1 && (
        <div className="space-y-6">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-neutral-900">
              Set up your organization
            </h2>
            <p className="mt-1 text-neutral-500">
              Tell us a bit about your company.
            </p>
          </div>
          <Card>
            <CardContent className="space-y-4 p-6">
              <div>
                <label className="mb-1 block text-sm font-medium text-neutral-700">
                  Organization name *
                </label>
                <input
                  type="text"
                  className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  placeholder="e.g. Acme Capital"
                  value={form.orgName}
                  onChange={(e) => update({ orgName: e.target.value })}
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-neutral-700">
                  Industry
                </label>
                <select
                  className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
                  value={form.orgIndustry}
                  onChange={(e) => update({ orgIndustry: e.target.value })}
                >
                  <option value="">Select industry</option>
                  {INDUSTRY_OPTIONS.map((o) => (
                    <option key={o} value={o.toLowerCase()}>
                      {o}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-neutral-700">
                  Primary geography
                </label>
                <select
                  className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
                  value={form.orgGeography}
                  onChange={(e) => update({ orgGeography: e.target.value })}
                >
                  <option value="">Select geography</option>
                  {GEOGRAPHY_OPTIONS.map((o) => (
                    <option key={o} value={o}>
                      {o}
                    </option>
                  ))}
                </select>
              </div>
              {form.orgType === "investor" ? (
                <div>
                  <label className="mb-1 block text-sm font-medium text-neutral-700">
                    Assets Under Management (AUM)
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-2 text-sm text-neutral-400">
                      $
                    </span>
                    <input
                      type="text"
                      className="w-full rounded-lg border border-neutral-300 py-2 pl-7 pr-3 text-sm"
                      placeholder="e.g. 50,000,000"
                      value={form.orgAum}
                      onChange={(e) => update({ orgAum: e.target.value.replace(/[^0-9]/g, "") })}
                    />
                  </div>
                </div>
              ) : (
                <div>
                  <label className="mb-1 block text-sm font-medium text-neutral-700">
                    Team size
                  </label>
                  <select
                    className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
                    value={form.orgSize}
                    onChange={(e) => update({ orgSize: e.target.value })}
                  >
                    <option value="">Select size</option>
                    <option value="1-10">1–10</option>
                    <option value="11-50">11–50</option>
                    <option value="51-200">51–200</option>
                    <option value="200+">200+</option>
                  </select>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Step 3: Preferences */}
      {step === 2 && (
        <div className="space-y-6">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-neutral-900">
              {form.orgType === "investor"
                ? "Your investment mandate"
                : "Your project focus"}
            </h2>
            <p className="mt-1 text-neutral-500">
              {form.orgType === "investor"
                ? "Help us match you with the right opportunities."
                : "Tell us about your development focus."}
            </p>
          </div>

          {form.orgType === "investor" ? (
            <Card>
              <CardContent className="space-y-5 p-6">
                {/* Sectors */}
                <div>
                  <label className="mb-2 block text-sm font-medium text-neutral-700">
                    Sectors of interest
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {SECTOR_CHIPS.map((s) => (
                      <button
                        key={s}
                        onClick={() => toggleChip("sectors", s.toLowerCase())}
                        className={cn(
                          "rounded-full border px-3 py-1.5 text-sm font-medium transition-colors",
                          form.sectors.includes(s.toLowerCase())
                            ? "border-primary-600 bg-primary-50 text-primary-700"
                            : "border-neutral-200 text-neutral-600 hover:border-neutral-300"
                        )}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Geographies */}
                <div>
                  <label className="mb-2 block text-sm font-medium text-neutral-700">
                    Geographies of interest
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {GEOGRAPHY_OPTIONS.map((g) => (
                      <button
                        key={g}
                        onClick={() => toggleChip("geographies", g)}
                        className={cn(
                          "rounded-full border px-3 py-1.5 text-sm font-medium transition-colors",
                          form.geographies.includes(g)
                            ? "border-primary-600 bg-primary-50 text-primary-700"
                            : "border-neutral-200 text-neutral-600 hover:border-neutral-300"
                        )}
                      >
                        {g}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Stage preference */}
                <div>
                  <label className="mb-2 block text-sm font-medium text-neutral-700">
                    Stage preference
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {STAGE_CHIPS.map((s) => (
                      <button
                        key={s}
                        onClick={() => toggleChip("stages", s.toLowerCase())}
                        className={cn(
                          "rounded-full border px-3 py-1.5 text-sm font-medium transition-colors",
                          form.stages.includes(s.toLowerCase())
                            ? "border-primary-600 bg-primary-50 text-primary-700"
                            : "border-neutral-200 text-neutral-600 hover:border-neutral-300"
                        )}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Ticket size */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="mb-1 block text-sm font-medium text-neutral-700">
                      Min ticket size ($)
                    </label>
                    <input
                      type="text"
                      className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
                      placeholder="e.g. 1,000,000"
                      value={form.ticketSizeMin}
                      onChange={(e) =>
                        update({ ticketSizeMin: e.target.value.replace(/[^0-9]/g, "") })
                      }
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-neutral-700">
                      Max ticket size ($)
                    </label>
                    <input
                      type="text"
                      className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
                      placeholder="e.g. 10,000,000"
                      value={form.ticketSizeMax}
                      onChange={(e) =>
                        update({ ticketSizeMax: e.target.value.replace(/[^0-9]/g, "") })
                      }
                    />
                  </div>
                </div>

                {/* Risk tolerance */}
                <div>
                  <label className="mb-1 block text-sm font-medium text-neutral-700">
                    Risk tolerance
                  </label>
                  <select
                    className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
                    value={form.riskTolerance}
                    onChange={(e) => update({ riskTolerance: e.target.value })}
                  >
                    <option value="conservative">Conservative</option>
                    <option value="moderate">Moderate</option>
                    <option value="aggressive">Aggressive</option>
                  </select>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="space-y-5 p-6">
                {/* Primary technology */}
                <div>
                  <label className="mb-1 block text-sm font-medium text-neutral-700">
                    Primary asset class
                  </label>
                  <select
                    className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
                    value={form.primaryTechnology}
                    onChange={(e) =>
                      update({ primaryTechnology: e.target.value })
                    }
                  >
                    {TECHNOLOGY_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Target markets */}
                <div>
                  <label className="mb-2 block text-sm font-medium text-neutral-700">
                    Target markets
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {GEOGRAPHY_OPTIONS.map((g) => (
                      <button
                        key={g}
                        onClick={() => toggleChip("targetMarkets", g)}
                        className={cn(
                          "rounded-full border px-3 py-1.5 text-sm font-medium transition-colors",
                          form.targetMarkets.includes(g)
                            ? "border-primary-600 bg-primary-50 text-primary-700"
                            : "border-neutral-200 text-neutral-600 hover:border-neutral-300"
                        )}
                      >
                        {g}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Development stage */}
                <div>
                  <label className="mb-1 block text-sm font-medium text-neutral-700">
                    Current development stage
                  </label>
                  <select
                    className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
                    value={form.developmentStage}
                    onChange={(e) =>
                      update({ developmentStage: e.target.value })
                    }
                  >
                    <option value="concept">Concept</option>
                    <option value="pre_development">Pre-development</option>
                    <option value="development">Development</option>
                    <option value="construction_ready">Construction Ready</option>
                    <option value="under_construction">Under Construction</option>
                    <option value="operational">Operational</option>
                  </select>
                </div>

                {/* Funding needs */}
                <div>
                  <label className="mb-1 block text-sm font-medium text-neutral-700">
                    Total funding needs ($)
                  </label>
                  <input
                    type="text"
                    className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
                    placeholder="e.g. 5,000,000"
                    value={form.fundingNeeds}
                    onChange={(e) =>
                      update({ fundingNeeds: e.target.value.replace(/[^0-9]/g, "") })
                    }
                  />
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Step 4: First Action */}
      {step === 3 && (
        <div className="space-y-6">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-neutral-900">
              {form.orgType === "investor"
                ? "Create your first portfolio"
                : "Create your first project"}
            </h2>
            <p className="mt-1 text-neutral-500">
              Get a head start — or skip this for now.
            </p>
          </div>

          {form.orgType === "investor" ? (
            <Card>
              <CardContent className="space-y-4 p-6">
                <div>
                  <label className="mb-1 block text-sm font-medium text-neutral-700">
                    Portfolio name
                  </label>
                  <input
                    type="text"
                    className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
                    placeholder="e.g. Alternative Assets Fund I"
                    value={form.firstActionName}
                    onChange={(e) =>
                      update({ firstActionName: e.target.value })
                    }
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-neutral-700">
                    Strategy
                  </label>
                  <select
                    className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
                    value={firstActionStrategy}
                    onChange={(e) => setFirstActionStrategy(e.target.value)}
                  >
                    {STRATEGY_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-neutral-700">
                    Target AUM ($)
                  </label>
                  <input
                    type="text"
                    className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
                    placeholder="e.g. 50,000,000"
                    value={form.orgAum}
                    onChange={(e) =>
                      update({ orgAum: e.target.value.replace(/[^0-9]/g, "") })
                    }
                  />
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="space-y-4 p-6">
                <div>
                  <label className="mb-1 block text-sm font-medium text-neutral-700">
                    Project name
                  </label>
                  <input
                    type="text"
                    className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
                    placeholder="e.g. Infrastructure Asset Alpha"
                    value={form.firstActionName}
                    onChange={(e) =>
                      update({ firstActionName: e.target.value })
                    }
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-neutral-700">
                    Project type
                  </label>
                  <select
                    className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
                    value={form.firstActionType}
                    onChange={(e) =>
                      update({ firstActionType: e.target.value })
                    }
                  >
                    {TECHNOLOGY_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-neutral-700">
                    Country
                  </label>
                  <input
                    type="text"
                    className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
                    placeholder="e.g. Germany"
                    value={form.firstActionGeography}
                    onChange={(e) =>
                      update({ firstActionGeography: e.target.value })
                    }
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-neutral-700">
                    Total investment required ($)
                  </label>
                  <input
                    type="text"
                    className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
                    placeholder="e.g. 5,000,000"
                    value={form.firstActionInvestment}
                    onChange={(e) =>
                      update({
                        firstActionInvestment: e.target.value.replace(/[^0-9]/g, ""),
                      })
                    }
                  />
                </div>
              </CardContent>
            </Card>
          )}

          <button
            onClick={() => {
              update({ skipFirstAction: true });
              setStep(4);
            }}
            className="mx-auto block text-sm text-neutral-500 underline hover:text-neutral-700"
          >
            Skip for now
          </button>
        </div>
      )}

      {/* Step 5: All Set */}
      {step === 4 && (
        <div className="space-y-6 text-center">
          <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-green-100">
            <Check className="h-10 w-10 text-green-600" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-neutral-900">
              You&apos;re all set!
            </h2>
            <p className="mt-2 text-neutral-500">
              Your workspace has been configured. Here&apos;s a summary:
            </p>
          </div>
          <Card>
            <CardContent className="space-y-3 p-6 text-left">
              <SummaryRow
                label="Role"
                value={form.orgType === "investor" ? "Investor" : "Project Developer"}
              />
              <SummaryRow label="Organization" value={form.orgName} />
              {form.orgIndustry && (
                <SummaryRow label="Industry" value={form.orgIndustry} />
              )}
              {form.orgGeography && (
                <SummaryRow label="Geography" value={form.orgGeography} />
              )}
              {form.orgType === "investor" && form.sectors.length > 0 && (
                <SummaryRow
                  label="Sectors"
                  value={form.sectors.join(", ")}
                />
              )}
              {!form.skipFirstAction && form.firstActionName && (
                <SummaryRow
                  label={form.orgType === "investor" ? "Portfolio" : "Project"}
                  value={form.firstActionName}
                />
              )}
            </CardContent>
          </Card>
          <Button
            size="lg"
            className="w-full"
            onClick={handleComplete}
            disabled={completeMutation.isPending}
          >
            {completeMutation.isPending ? "Setting up..." : "Go to Dashboard"}
            {!completeMutation.isPending && (
              <ArrowRight className="ml-2 h-4 w-4" />
            )}
          </Button>
          {completeMutation.isError && (
            <p className="text-sm text-red-600">
              Something went wrong. Please try again.
            </p>
          )}
        </div>
      )}

      {/* Navigation buttons (steps 1-3) */}
      {step >= 1 && step <= 3 && (
        <div className="mt-8 flex items-center justify-between">
          <Button
            variant="outline"
            onClick={() => setStep((s) => s - 1)}
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <Button
            onClick={() => setStep((s) => s + 1)}
            disabled={!canAdvance()}
          >
            Continue
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-neutral-100 pb-2 last:border-0">
      <span className="text-sm text-neutral-500">{label}</span>
      <span className="text-sm font-medium text-neutral-900 capitalize">
        {value}
      </span>
    </div>
  );
}
