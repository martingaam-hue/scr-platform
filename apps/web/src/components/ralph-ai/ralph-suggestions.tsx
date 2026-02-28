"use client";

import { usePathname } from "next/navigation";

interface SuggestionSet {
  pattern: RegExp;
  suggestions: string[];
}

const SUGGESTIONS: SuggestionSet[] = [
  {
    pattern: /\/portfolio/,
    suggestions: [
      "How is my portfolio performing?",
      "What are my top holdings by IRR?",
      "Show me concentration risk across sectors",
      "Which projects are underperforming?",
    ],
  },
  {
    pattern: /\/projects/,
    suggestions: [
      "Tell me about my active projects",
      "Which projects are ready for fundraising?",
      "What is the signal score breakdown?",
      "Show me improvement recommendations",
    ],
  },
  {
    pattern: /\/matching/,
    suggestions: [
      "Who are my best investor matches?",
      "Find projects matching my mandate",
      "Explain my top match alignment",
      "Which sectors have the most matches?",
    ],
  },
  {
    pattern: /\/risk/,
    suggestions: [
      "What are my highest risk exposures?",
      "Summarize my risk assessments",
      "What mitigation strategies are available?",
      "How does insurance affect my risk profile?",
    ],
  },
  {
    pattern: /\/valuation/,
    suggestions: [
      "What is my latest DCF valuation?",
      "How do I compare to market comps?",
      "Run a scenario for 20% equity at $5M",
      "What affects my capital efficiency?",
    ],
  },
  {
    pattern: /\/dataroom/,
    suggestions: [
      "What documents have been uploaded?",
      "Find financial projections in my documents",
      "Search for offtake agreement terms",
      "Review key legal document clauses",
    ],
  },
  {
    pattern: /.*/,
    suggestions: [
      "Give me an overview of my platform activity",
      "What should I focus on today?",
      "How can I improve my deal readiness?",
      "What are my best investment opportunities?",
    ],
  },
];

function getSuggestions(pathname: string): string[] {
  for (const { pattern, suggestions } of SUGGESTIONS) {
    if (pattern.test(pathname)) {
      return suggestions;
    }
  }
  return SUGGESTIONS[SUGGESTIONS.length - 1].suggestions;
}

interface RalphSuggestionsProps {
  onSelect: (suggestion: string) => void;
}

export function RalphSuggestions({ onSelect }: RalphSuggestionsProps) {
  const pathname = usePathname();
  const suggestions = getSuggestions(pathname);

  return (
    <div className="flex flex-wrap gap-2 p-4">
      {suggestions.map((s) => (
        <button
          key={s}
          onClick={() => onSelect(s)}
          className="rounded-full border border-neutral-200 bg-white px-3 py-1.5 text-xs text-neutral-600 transition-colors hover:border-primary-300 hover:bg-primary-50 hover:text-primary-700 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-400 dark:hover:border-primary-600 dark:hover:bg-primary-900/20 dark:hover:text-primary-300"
        >
          {s}
        </button>
      ))}
    </div>
  );
}
