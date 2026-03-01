"use client";

import { useState } from "react";
import {
  Calculator,
  Loader2,
  TrendingUp,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  BarChart,
} from "@scr/ui";
import {
  useTaxonomy,
  useTemplates,
  useComputeDCF,
  type FinancialTemplate,
  type DCFInput,
  type DCFResult,
} from "@/lib/financial-templates";

// ── Sector filter ──────────────────────────────────────────────────────────────

const SECTOR_TABS = [
  { code: "", label: "All" },
  { code: "RENEW", label: "Renewables" },
  { code: "INFRA", label: "Infrastructure" },
  { code: "IMPACT", label: "Impact" },
];

function SectorFilter({
  selected,
  onChange,
}: {
  selected: string;
  onChange: (code: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {SECTOR_TABS.map(({ code, label }) => (
        <button
          key={code}
          onClick={() => onChange(code)}
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
            selected === code
              ? "bg-primary-600 text-white"
              : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

// ── Template Card ──────────────────────────────────────────────────────────────

function TemplateCard({
  template,
  selected,
  onClick,
}: {
  template: FinancialTemplate;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left rounded-lg border-2 p-4 transition-all ${
        selected
          ? "border-primary-500 bg-primary-50"
          : "border-neutral-200 bg-white hover:border-neutral-300 hover:shadow-sm"
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <span
          className={`text-sm font-semibold ${
            selected ? "text-primary-800" : "text-neutral-900"
          }`}
        >
          {template.name}
        </span>
        <Badge variant={template.is_system ? "info" : "neutral"}>
          {template.taxonomy_code}
        </Badge>
      </div>
      {template.description && (
        <p className="text-xs text-neutral-500 line-clamp-2">
          {template.description}
        </p>
      )}
    </button>
  );
}

// ── DCF Input Panel ────────────────────────────────────────────────────────────

function DCFPanel({ template }: { template: FinancialTemplate }) {
  const [inputs, setInputs] = useState<DCFInput>({
    capacity_mw: 50,
    capex_per_mw: 1_200_000,
    discount_rate: 8,
  });
  const [result, setResult] = useState<DCFResult | null>(null);
  const { mutate: compute, isPending } = useComputeDCF();

  const setField = (key: keyof DCFInput, value: number) =>
    setInputs((prev) => ({ ...prev, [key]: value }));

  const handleCompute = () => {
    compute(
      { templateId: template.id, inputs },
      { onSuccess: (data) => setResult(data) }
    );
  };

  const cashflowChartData = (result?.cashflows ?? []).map((cf) => ({
    year: cf.year,
    Revenue: cf.revenue / 1_000_000,
    OpEx: cf.opex / 1_000_000,
    "Net CF": cf.net / 1_000_000,
  }));

  return (
    <div className="space-y-6">
      {/* Inputs */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Calculator className="h-4 w-4 text-primary-600" />
            DCF Inputs — {template.name}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <InputField
              label="Capacity (MW)"
              value={inputs.capacity_mw ?? 50}
              min={1}
              max={2000}
              onChange={(v) => setField("capacity_mw", v)}
            />
            <InputField
              label="CapEx per MW (€)"
              value={inputs.capex_per_mw ?? 1_200_000}
              min={100_000}
              max={10_000_000}
              step={50_000}
              onChange={(v) => setField("capex_per_mw", v)}
            />
            <InputField
              label="Discount Rate (%)"
              value={inputs.discount_rate ?? 8}
              min={1}
              max={30}
              step={0.5}
              onChange={(v) => setField("discount_rate", v)}
            />
          </div>
          <Button onClick={handleCompute} disabled={isPending}>
            {isPending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Computing…
              </>
            ) : (
              <>
                <TrendingUp className="h-4 w-4 mr-2" />
                Compute DCF
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Results */}
      {result && (
        <>
          <div className="grid grid-cols-3 gap-4">
            <ResultKPI
              label="NPV"
              value={`€${(result.npv / 1_000_000).toFixed(1)}m`}
              color={result.npv >= 0 ? "text-green-700" : "text-red-700"}
              bg={result.npv >= 0 ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}
            />
            <ResultKPI
              label="IRR"
              value={`${(result.irr * 100).toFixed(1)}%`}
              color="text-primary-700"
              bg="bg-primary-50 border-primary-200"
            />
            <ResultKPI
              label="Payback"
              value={`${result.payback_years.toFixed(1)} yrs`}
              color="text-amber-700"
              bg="bg-amber-50 border-amber-200"
            />
          </div>

          {cashflowChartData.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Cashflows by Year (€m)</CardTitle>
              </CardHeader>
              <CardContent>
                <BarChart
                  data={cashflowChartData}
                  xKey="year"
                  yKeys={["Revenue", "OpEx", "Net CF"]}
                  height={240}
                />
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

function InputField({
  label,
  value,
  min,
  max,
  step = 1,
  onChange,
}: {
  label: string;
  value: number;
  min?: number;
  max?: number;
  step?: number;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-neutral-700 mb-1">
        {label}
      </label>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
      />
    </div>
  );
}

function ResultKPI({
  label,
  value,
  color,
  bg,
}: {
  label: string;
  value: string;
  color: string;
  bg: string;
}) {
  return (
    <div className={`rounded-lg border p-4 ${bg}`}>
      <p className="text-xs font-medium text-neutral-500 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

// ── Taxonomy Tree Panel ────────────────────────────────────────────────────────

function TaxonomyPanel({
  selectedCode,
  onChange,
}: {
  selectedCode: string;
  onChange: (code: string) => void;
}) {
  const { data: nodes, isLoading } = useTaxonomy(undefined, false);

  if (isLoading) {
    return (
      <div className="flex h-24 items-center justify-center">
        <Loader2 className="h-4 w-4 animate-spin text-neutral-400" />
      </div>
    );
  }

  if (!nodes || nodes.length === 0) return null;

  return (
    <div className="space-y-1">
      <p className="text-xs font-semibold uppercase tracking-widest text-neutral-400 mb-2">
        Taxonomy
      </p>
      {nodes.map((node) => (
        <button
          key={node.code}
          onClick={() => onChange(selectedCode === node.code ? "" : node.code)}
          className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
            selectedCode === node.code
              ? "bg-primary-600 text-white font-medium"
              : "text-neutral-600 hover:bg-neutral-100"
          }`}
          style={{ paddingLeft: `${(node.level + 1) * 12}px` }}
        >
          {node.name}
          {node.is_leaf && (
            <span className="ml-1.5 text-xs opacity-60">↳</span>
          )}
        </button>
      ))}
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function FinancialTemplatesPage() {
  const [selectedSector, setSelectedSector] = useState("");
  const [selectedTaxonomyCode, setSelectedTaxonomyCode] = useState("");
  const [selectedTemplate, setSelectedTemplate] =
    useState<FinancialTemplate | null>(null);

  // Use the taxonomy code filter when a taxonomy node is selected,
  // otherwise fall back to the sector tab.
  const filterCode = selectedTaxonomyCode || selectedSector || undefined;

  const { data: templates, isLoading } = useTemplates(filterCode);

  const handleSectorChange = (code: string) => {
    setSelectedSector(code);
    setSelectedTaxonomyCode("");
    setSelectedTemplate(null);
  };

  const handleTaxonomyChange = (code: string) => {
    setSelectedTaxonomyCode(code);
    setSelectedTemplate(null);
  };

  return (
    <div className="p-6 space-y-6 max-w-screen-xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-amber-100 rounded-lg">
          <Calculator className="h-6 w-6 text-amber-700" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">
            Financial Models
          </h1>
          <p className="text-sm text-neutral-500 mt-0.5">
            Sector-specific DCF templates and cashflow models
          </p>
        </div>
      </div>

      {/* Sector filter */}
      <SectorFilter selected={selectedSector} onChange={handleSectorChange} />

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: taxonomy + template list */}
        <div className="lg:col-span-1 space-y-6">
          {/* Taxonomy tree */}
          <Card>
            <CardContent className="p-4">
              <TaxonomyPanel
                selectedCode={selectedTaxonomyCode}
                onChange={handleTaxonomyChange}
              />
            </CardContent>
          </Card>

          {/* Templates list */}
          <div className="space-y-3">
            <p className="text-sm font-semibold text-neutral-700">
              Templates
              {templates && (
                <span className="ml-2 text-neutral-400 font-normal">
                  ({templates.length})
                </span>
              )}
            </p>

            {isLoading ? (
              <div className="flex h-32 items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
              </div>
            ) : !templates || templates.length === 0 ? (
              <EmptyState
                icon={<Calculator className="h-8 w-8 text-neutral-300" />}
                title="No templates"
                description="No templates match the current filter."
              />
            ) : (
              <div className="space-y-2">
                {templates.map((t) => (
                  <TemplateCard
                    key={t.id}
                    template={t}
                    selected={selectedTemplate?.id === t.id}
                    onClick={() => setSelectedTemplate(t)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: DCF panel */}
        <div className="lg:col-span-2">
          {selectedTemplate ? (
            <DCFPanel template={selectedTemplate} />
          ) : (
            <div className="flex h-full min-h-[300px] items-center justify-center rounded-xl border-2 border-dashed border-neutral-200">
              <EmptyState
                icon={<Calculator className="h-10 w-10 text-neutral-300" />}
                title="Select a template"
                description="Choose a financial model from the list to run a DCF analysis."
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
