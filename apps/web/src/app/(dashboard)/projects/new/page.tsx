"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Sun,
  Wind,
  Droplets,
  Leaf,
  Flame,
  Battery,
  Atom,
  Network,
  Gauge,
  TreePine,
  Boxes,
  Building,
  Building2,
  Home,
  TrendingUp,
  Mountain,
  CreditCard,
  Cpu,
  Heart,
  Star,
  Wheat,
} from "lucide-react";
import { Button, Card, CardContent, cn } from "@scr/ui";
import {
  useCreateProject,
  type ProjectType,
  type ProjectStage,
  type ProjectStatus,
  projectTypeLabel,
} from "@/lib/projects";

// ── Types ───────────────────────────────────────────────────────────────────

interface FormData {
  // Step 1: Basic Info
  name: string;
  project_type: ProjectType | "";
  description: string;
  // Step 2: Location
  geography_country: string;
  geography_region: string;
  // Step 3: Technical
  stage: ProjectStage;
  capacity_mw: string;
  // Step 4: Financial
  total_investment_required: string;
  currency: string;
  target_close_date: string;
}

const INITIAL_FORM: FormData = {
  name: "",
  project_type: "",
  description: "",
  geography_country: "",
  geography_region: "",
  stage: "concept",
  capacity_mw: "",
  total_investment_required: "",
  currency: "USD",
  target_close_date: "",
};

const STEPS = [
  { label: "Basic Info", number: 1 },
  { label: "Location", number: 2 },
  { label: "Technical", number: 3 },
  { label: "Financial", number: 4 },
  { label: "Review", number: 5 },
];

const TYPE_ICONS: Record<string, React.ElementType> = {
  // Legacy renewable types
  solar: Sun,
  wind: Wind,
  hydro: Droplets,
  biomass: Leaf,
  geothermal: Flame,
  energy_efficiency: Gauge,
  green_building: Building2,
  sustainable_agriculture: Wheat,
  storage: Battery,
  hydrogen: Atom,
  nuclear: Atom,
  grid: Network,
  efficiency: Gauge,
  carbon_capture: Network,
  nature_based: TreePine,
  // Alternative investment asset classes
  infrastructure: Building,
  real_estate: Home,
  private_equity: TrendingUp,
  natural_resources: Mountain,
  private_credit: CreditCard,
  digital_assets: Cpu,
  impact: Heart,
  specialty: Star,
  other: Boxes,
};

const PROJECT_TYPES: ProjectType[] = [
  // Alternative investment asset classes (primary)
  "infrastructure",
  "real_estate",
  "private_equity",
  "natural_resources",
  "private_credit",
  "digital_assets",
  "impact",
  "specialty",
  // Legacy renewable types
  "solar",
  "wind",
  "hydro",
  "storage",
  "hydrogen",
  "biomass",
  "geothermal",
  "carbon_capture",
  "nature_based",
  "other",
];

const STAGE_OPTIONS: { label: string; value: ProjectStage }[] = [
  { label: "Concept", value: "concept" },
  { label: "Pre-Feasibility", value: "pre_feasibility" },
  { label: "Feasibility", value: "feasibility" },
  { label: "Development", value: "development" },
  { label: "Permitting", value: "permitting" },
  { label: "Financing", value: "financing" },
  { label: "Construction", value: "construction" },
  { label: "Commissioning", value: "commissioning" },
  { label: "Operational", value: "operational" },
];

const CURRENCIES = ["USD", "EUR", "GBP", "CHF", "JPY", "AUD", "CAD"];

// ── Page ────────────────────────────────────────────────────────────────────

export default function NewProjectPage() {
  const router = useRouter();
  const createProject = useCreateProject();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState<FormData>(INITIAL_FORM);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const update = (field: keyof FormData, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: "" }));
  };

  const validateStep = (): boolean => {
    const errs: Record<string, string> = {};
    if (step === 1) {
      if (!form.name.trim()) errs.name = "Project name is required";
      if (!form.project_type) errs.project_type = "Select a project type";
    }
    if (step === 2) {
      if (!form.geography_country.trim())
        errs.geography_country = "Country is required";
    }
    if (step === 4) {
      if (!form.total_investment_required.trim())
        errs.total_investment_required = "Investment amount is required";
      const amount = parseFloat(form.total_investment_required);
      if (isNaN(amount) || amount <= 0)
        errs.total_investment_required = "Must be a positive number";
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleNext = () => {
    if (validateStep()) {
      setStep((s) => Math.min(s + 1, 5));
    }
  };

  const handleBack = () => {
    setStep((s) => Math.max(s - 1, 1));
  };

  const handleSubmit = (asDraft: boolean) => {
    createProject.mutate(
      {
        name: form.name,
        project_type: form.project_type as ProjectType,
        description: form.description,
        geography_country: form.geography_country,
        geography_region: form.geography_region || undefined,
        stage: form.stage,
        capacity_mw: form.capacity_mw || undefined,
        total_investment_required: form.total_investment_required,
        currency: form.currency,
        target_close_date: form.target_close_date || undefined,
        status: (asDraft ? "draft" : "active") as ProjectStatus,
      },
      {
        onSuccess: (project) => {
          router.push(`/projects/${project.id}`);
        },
      }
    );
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Back */}
      <button
        onClick={() => router.push("/projects")}
        className="flex items-center gap-1 text-sm text-neutral-500 hover:text-neutral-700"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Projects
      </button>

      <h1 className="text-2xl font-bold text-neutral-900">New Project</h1>

      {/* Step indicator */}
      <div className="flex items-center gap-2">
        {STEPS.map((s) => (
          <div key={s.number} className="flex items-center gap-2">
            <button
              onClick={() => {
                if (s.number < step) setStep(s.number);
              }}
              className={cn(
                "flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium transition-colors",
                step === s.number
                  ? "bg-primary-600 text-white"
                  : step > s.number
                    ? "bg-primary-100 text-primary-700"
                    : "bg-neutral-100 text-neutral-400"
              )}
            >
              {step > s.number ? (
                <Check className="h-4 w-4" />
              ) : (
                s.number
              )}
            </button>
            <span
              className={cn(
                "hidden text-sm sm:inline",
                step === s.number
                  ? "font-medium text-neutral-900"
                  : "text-neutral-400"
              )}
            >
              {s.label}
            </span>
            {s.number < STEPS.length && (
              <div className="mx-2 h-px w-8 bg-neutral-200" />
            )}
          </div>
        ))}
      </div>

      {/* Form */}
      <Card>
        <CardContent className="p-6">
          {/* Step 1: Basic Info */}
          {step === 1 && (
            <div className="space-y-6">
              <div>
                <label className="mb-1 block text-sm font-medium text-neutral-700">
                  Project Name *
                </label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => update("name", e.target.value)}
                  className={cn(
                    "w-full rounded-lg border px-3 py-2 text-sm",
                    errors.name ? "border-red-500" : "border-neutral-300"
                  )}
                  placeholder="e.g., Solar Farm Andalusia"
                />
                {errors.name && (
                  <p className="mt-1 text-xs text-red-500">{errors.name}</p>
                )}
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-neutral-700">
                  Project Type *
                </label>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
                  {PROJECT_TYPES.map((type) => {
                    const Icon = TYPE_ICONS[type];
                    return (
                      <button
                        key={type}
                        onClick={() => update("project_type", type)}
                        className={cn(
                          "flex flex-col items-center gap-2 rounded-lg border-2 p-3 text-center transition-colors",
                          form.project_type === type
                            ? "border-primary-600 bg-primary-50"
                            : "border-neutral-200 hover:border-neutral-300"
                        )}
                      >
                        <Icon className="h-6 w-6" />
                        <span className="text-xs">{projectTypeLabel(type)}</span>
                      </button>
                    );
                  })}
                </div>
                {errors.project_type && (
                  <p className="mt-1 text-xs text-red-500">
                    {errors.project_type}
                  </p>
                )}
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-neutral-700">
                  Description
                </label>
                <textarea
                  value={form.description}
                  onChange={(e) => update("description", e.target.value)}
                  rows={4}
                  className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
                  placeholder="Describe the project..."
                />
              </div>
            </div>
          )}

          {/* Step 2: Location */}
          {step === 2 && (
            <div className="space-y-6">
              <div>
                <label className="mb-1 block text-sm font-medium text-neutral-700">
                  Country *
                </label>
                <input
                  type="text"
                  value={form.geography_country}
                  onChange={(e) => update("geography_country", e.target.value)}
                  className={cn(
                    "w-full rounded-lg border px-3 py-2 text-sm",
                    errors.geography_country
                      ? "border-red-500"
                      : "border-neutral-300"
                  )}
                  placeholder="e.g., Spain"
                />
                {errors.geography_country && (
                  <p className="mt-1 text-xs text-red-500">
                    {errors.geography_country}
                  </p>
                )}
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-neutral-700">
                  Region
                </label>
                <input
                  type="text"
                  value={form.geography_region}
                  onChange={(e) => update("geography_region", e.target.value)}
                  className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
                  placeholder="e.g., Andalusia"
                />
              </div>
            </div>
          )}

          {/* Step 3: Technical */}
          {step === 3 && (
            <div className="space-y-6">
              <div>
                <label className="mb-1 block text-sm font-medium text-neutral-700">
                  Project Stage
                </label>
                <select
                  value={form.stage}
                  onChange={(e) =>
                    update("stage", e.target.value)
                  }
                  className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
                >
                  {STAGE_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-neutral-700">
                  Capacity (MW)
                </label>
                <input
                  type="number"
                  value={form.capacity_mw}
                  onChange={(e) => update("capacity_mw", e.target.value)}
                  className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
                  placeholder="e.g., 50"
                  min="0"
                  step="0.1"
                />
              </div>
            </div>
          )}

          {/* Step 4: Financial */}
          {step === 4 && (
            <div className="space-y-6">
              <div>
                <label className="mb-1 block text-sm font-medium text-neutral-700">
                  Total Investment Required *
                </label>
                <div className="flex gap-3">
                  <select
                    value={form.currency}
                    onChange={(e) => update("currency", e.target.value)}
                    className="rounded-lg border border-neutral-300 px-3 py-2 text-sm"
                  >
                    {CURRENCIES.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                  <input
                    type="number"
                    value={form.total_investment_required}
                    onChange={(e) =>
                      update("total_investment_required", e.target.value)
                    }
                    className={cn(
                      "flex-1 rounded-lg border px-3 py-2 text-sm",
                      errors.total_investment_required
                        ? "border-red-500"
                        : "border-neutral-300"
                    )}
                    placeholder="e.g., 25000000"
                    min="0"
                    step="1"
                  />
                </div>
                {errors.total_investment_required && (
                  <p className="mt-1 text-xs text-red-500">
                    {errors.total_investment_required}
                  </p>
                )}
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-neutral-700">
                  Target Close Date
                </label>
                <input
                  type="date"
                  value={form.target_close_date}
                  onChange={(e) =>
                    update("target_close_date", e.target.value)
                  }
                  className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
                />
              </div>
            </div>
          )}

          {/* Step 5: Review */}
          {step === 5 && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-neutral-900">
                Review your project
              </h3>
              <div className="divide-y rounded-lg border">
                <ReviewRow label="Name" value={form.name} />
                <ReviewRow
                  label="Type"
                  value={
                    form.project_type
                      ? projectTypeLabel(form.project_type as ProjectType)
                      : ""
                  }
                />
                <ReviewRow
                  label="Description"
                  value={form.description || "—"}
                />
                <ReviewRow label="Country" value={form.geography_country} />
                <ReviewRow
                  label="Region"
                  value={form.geography_region || "—"}
                />
                <ReviewRow
                  label="Stage"
                  value={
                    STAGE_OPTIONS.find((o) => o.value === form.stage)?.label ??
                    form.stage
                  }
                />
                <ReviewRow
                  label="Capacity"
                  value={form.capacity_mw ? `${form.capacity_mw} MW` : "—"}
                />
                <ReviewRow
                  label="Investment Required"
                  value={`${form.currency} ${Number(form.total_investment_required).toLocaleString()}`}
                />
                <ReviewRow
                  label="Target Close"
                  value={form.target_close_date || "—"}
                />
              </div>
            </div>
          )}

          {/* Navigation buttons */}
          <div className="mt-8 flex items-center justify-between">
            <div>
              {step > 1 && (
                <Button variant="outline" onClick={handleBack}>
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back
                </Button>
              )}
            </div>
            <div className="flex gap-3">
              {step === 5 ? (
                <>
                  <Button
                    variant="outline"
                    onClick={() => handleSubmit(true)}
                    disabled={createProject.isPending}
                  >
                    Save as Draft
                  </Button>
                  <Button
                    onClick={() => handleSubmit(false)}
                    disabled={createProject.isPending}
                  >
                    <Check className="mr-2 h-4 w-4" />
                    Create Project
                  </Button>
                </>
              ) : (
                <Button onClick={handleNext}>
                  Next
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between px-4 py-3">
      <span className="text-sm text-neutral-500">{label}</span>
      <span className="text-sm font-medium text-neutral-900 text-right max-w-[60%]">
        {value}
      </span>
    </div>
  );
}
