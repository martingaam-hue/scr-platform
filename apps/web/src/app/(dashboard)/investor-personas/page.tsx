"use client";

import { useState } from "react";
import { ChevronRight, Sparkles, Target, X } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  EmptyState,
} from "@scr/ui";
import {
  STRATEGY_LABELS,
  useGeneratePersona,
  useInvestorPersonas,
  usePersonaMatches,
  type InvestorPersona,
  type PersonaMatch,
} from "@/lib/investor-personas";

function PersonaCard({
  persona,
  selected,
  onSelect,
}: {
  persona: InvestorPersona;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <Card
      className={`cursor-pointer transition-all ${
        selected
          ? "ring-2 ring-primary-500"
          : "hover:border-neutral-300"
      }`}
      onClick={onSelect}
    >
      <CardContent className="p-5">
        <div className="flex items-start justify-between mb-2">
          <p className="text-sm font-semibold text-neutral-800">
            {persona.persona_name}
          </p>
          <Badge variant="neutral">
            {STRATEGY_LABELS[persona.strategy_type] ?? persona.strategy_type}
          </Badge>
        </div>
        <div className="space-y-1 text-xs text-neutral-500">
          {(persona.target_irr_min != null || persona.target_irr_max != null) && (
            <p>
              IRR: {persona.target_irr_min ?? "—"}% –{" "}
              {persona.target_irr_max ?? "—"}%
            </p>
          )}
          {persona.ticket_size_min != null && (
            <p>
              Ticket: ${(persona.ticket_size_min / 1e6).toFixed(1)}M – $
              {(
                ((persona.ticket_size_max ?? persona.ticket_size_min * 3) /
                  1e6)
              ).toFixed(1)}
              M
            </p>
          )}
          {persona.preferred_asset_types &&
            persona.preferred_asset_types.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {persona.preferred_asset_types.slice(0, 3).map((t) => (
                  <Badge key={t} variant="neutral" className="text-xs">
                    {t}
                  </Badge>
                ))}
              </div>
            )}
        </div>
        <div className="flex items-center gap-1 mt-3 text-xs text-primary-600 font-medium">
          View matches <ChevronRight className="h-3 w-3" />
        </div>
      </CardContent>
    </Card>
  );
}

function MatchList({ personaId }: { personaId: string }) {
  const { data: matches = [], isLoading } = usePersonaMatches(personaId);

  if (isLoading) {
    return (
      <div className="flex justify-center py-4">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    );
  }

  if (matches.length === 0) {
    return (
      <p className="text-sm text-neutral-400 text-center py-4">
        No matching projects found for this persona.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {matches.map((m: PersonaMatch) => (
        <div
          key={m.project_id}
          className="flex items-center justify-between p-3 rounded-lg border border-neutral-100 hover:bg-neutral-50"
        >
          <div>
            <p className="text-sm font-medium text-neutral-800">
              {m.project_name}
            </p>
            <p className="text-xs text-neutral-500">
              {m.project_type} · {m.geography_country} · {m.stage}
            </p>
            <div className="flex flex-wrap gap-2 mt-1">
              {m.alignment_reasons.slice(0, 2).map((r, i) => (
                <span key={i} className="text-xs text-green-600">
                  ✓ {r}
                </span>
              ))}
            </div>
          </div>
          <div className="text-right ml-4 shrink-0">
            <p className="text-lg font-bold text-primary-600">
              {m.alignment_score}
            </p>
            <p className="text-xs text-neutral-400">alignment</p>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function InvestorPersonasPage() {
  const { data: personas = [], isLoading } = useInvestorPersonas();
  const generatePersona = useGeneratePersona();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showGenerate, setShowGenerate] = useState(false);
  const [description, setDescription] = useState("");

  const handleGenerate = () => {
    if (!description.trim()) return;
    generatePersona.mutate(description, {
      onSuccess: (p) => {
        setShowGenerate(false);
        setDescription("");
        setSelectedId(p.id);
      },
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">
            Investor Personas
          </h1>
          <p className="text-sm text-neutral-500 mt-1">
            Define and manage your investment personas to discover matching
            opportunities.
          </p>
        </div>
        <Button onClick={() => setShowGenerate(!showGenerate)}>
          <Sparkles className="mr-2 h-4 w-4" />
          Generate with AI
        </Button>
      </div>

      {showGenerate && (
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm font-semibold text-neutral-700">
                Generate Persona from Description
              </p>
              <button onClick={() => setShowGenerate(false)}>
                <X className="h-4 w-4 text-neutral-400" />
              </button>
            </div>
            <textarea
              className="w-full rounded-md border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              rows={3}
              placeholder="E.g. We are a mid-market impact fund focused on early-stage solar and wind projects in Southeast Asia, targeting IRR of 15-20%, ticket size $5M-$20M..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            <div className="flex justify-end mt-3">
              <Button
                onClick={handleGenerate}
                disabled={generatePersona.isPending || !description.trim()}
              >
                {generatePersona.isPending ? "Generating..." : "Generate Persona"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="flex h-40 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
        </div>
      ) : personas.length === 0 ? (
        <EmptyState
          icon={<Target className="h-12 w-12 text-neutral-400" />}
          title="No investor personas"
          description="Generate a persona with AI or create one manually to discover matching projects."
          action={
            <Button onClick={() => setShowGenerate(true)}>
              <Sparkles className="mr-2 h-4 w-4" />
              Generate with AI
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="space-y-3">
            {personas.map((p) => (
              <PersonaCard
                key={p.id}
                persona={p}
                selected={selectedId === p.id}
                onSelect={() =>
                  setSelectedId(selectedId === p.id ? null : p.id)
                }
              />
            ))}
          </div>
          {selectedId && (
            <div className="lg:col-span-2">
              <Card>
                <CardContent className="p-5">
                  <p className="text-sm font-semibold text-neutral-700 mb-4">
                    Matching Projects
                  </p>
                  <MatchList personaId={selectedId} />
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
