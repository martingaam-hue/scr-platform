"use client";

import { useState } from "react";
import {
  ArrowLeftRight,
  Globe,
  Loader2,
  RefreshCw,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  EmptyState,
  cn,
} from "@scr/ui";
import {
  useFXRates,
  useFXExposure,
  useConvertCurrency,
  useRefreshFXRates,
  flagEmoji,
  MAJOR_CURRENCIES,
  type CurrencyExposureItem,
} from "@/lib/fx";

// ── Exposure Bar ──────────────────────────────────────────────────────────────

function ExposureBar({ item, max }: { item: CurrencyExposureItem; max: number }) {
  const barWidth = max > 0 ? (item.value_eur / max) * 100 : 0;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="flex items-center gap-1.5 font-medium">
          <span>{flagEmoji(item.currency)}</span>
          <span>{item.currency}</span>
          <span className="text-xs text-gray-400 font-normal">{item.project_count} project{item.project_count !== 1 ? "s" : ""}</span>
        </span>
        <span className="tabular-nums text-gray-700">
          {item.pct.toFixed(1)}%
        </span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-indigo-500 rounded-full transition-all"
          style={{ width: `${barWidth}%` }}
        />
      </div>
      <p className="text-xs text-gray-400 text-right">
        €{(item.value_eur / 1_000_000).toFixed(1)}M
      </p>
    </div>
  );
}

// ── Currency Converter ────────────────────────────────────────────────────────

function CurrencyConverter() {
  const { data: rates } = useFXRates();
  const { mutate: convert, isPending, data: result, reset } = useConvertCurrency();

  const [amount, setAmount] = useState("10000");
  const [from, setFrom] = useState("USD");
  const [to, setTo] = useState("EUR");

  const handleConvert = () => {
    const n = parseFloat(amount);
    if (!isNaN(n)) convert({ amount: n, from_currency: from, to_currency: to });
  };

  const allCurrencies = rates ? Object.keys(rates).sort() : MAJOR_CURRENCIES;

  const CurrencySelect = ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <select
      value={value}
      onChange={(e) => { onChange(e.target.value); reset(); }}
      className="border border-gray-300 rounded-md px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
    >
      {allCurrencies.map((c) => (
        <option key={c} value={c}>{c}</option>
      ))}
    </select>
  );

  return (
    <Card>
      <CardContent className="p-4 space-y-4">
        <p className="text-sm font-medium text-gray-700 flex items-center gap-2">
          <ArrowLeftRight className="h-4 w-4 text-indigo-500" />
          Currency Converter
        </p>
        <div className="flex items-center gap-2 flex-wrap">
          <input
            type="number"
            value={amount}
            onChange={(e) => { setAmount(e.target.value); reset(); }}
            className="w-28 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <CurrencySelect value={from} onChange={setFrom} />
          <span className="text-gray-400">→</span>
          <CurrencySelect value={to} onChange={setTo} />
          <Button size="sm" onClick={handleConvert} disabled={isPending}>
            {isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : "Convert"}
          </Button>
        </div>
        {result && (
          <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3 text-sm">
            <span className="font-semibold text-indigo-800">
              {result.converted_amount.toLocaleString(undefined, { maximumFractionDigits: 2 })} {result.to_currency}
            </span>
            {result.rate && (
              <span className="text-indigo-500 ml-2">
                (rate: {result.rate.toFixed(4)})
              </span>
            )}
            {result.rate_date && (
              <span className="text-gray-400 ml-2 text-xs">as of {result.rate_date}</span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Rate Table ────────────────────────────────────────────────────────────────

function RateTable() {
  const { data, isLoading } = useFXRates();
  const { mutate: refresh, isPending } = useRefreshFXRates();

  if (isLoading) return <Loader2 className="h-5 w-5 animate-spin text-gray-400 m-4" />;

  const rates = data?.rates ?? {};
  const displayed = MAJOR_CURRENCIES.filter((c) => c !== "EUR" && rates[c]);

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm font-medium text-gray-700">ECB Reference Rates</p>
          <div className="flex items-center gap-2">
            {data?.rate_date && (
              <span className="text-xs text-gray-400">as of {data.rate_date}</span>
            )}
            <Button size="sm" variant="outline" onClick={() => refresh()} disabled={isPending}>
              {isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
            </Button>
          </div>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {displayed.map((currency) => (
            <div key={currency} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg text-sm">
              <span className="flex items-center gap-1">
                <span>{flagEmoji(currency)}</span>
                <span className="font-medium">{currency}</span>
              </span>
              <span className="tabular-nums text-gray-700">{rates[currency]?.toFixed(4)}</span>
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-400 mt-2">Base: 1 EUR = x {"{currency}"} — ECB daily fix</p>
      </CardContent>
    </Card>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function FXPage() {
  const [baseCurrency, setBaseCurrency] = useState("EUR");
  const { data: exposure, isLoading } = useFXExposure(undefined, baseCurrency);

  const maxExposure = Math.max(...(exposure?.exposure.map((e) => e.value_eur) ?? [1]));

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">FX Exposure</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Portfolio currency breakdown and ECB reference rates
          </p>
        </div>
        <select
          value={baseCurrency}
          onChange={(e) => setBaseCurrency(e.target.value)}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          {["EUR", "USD", "GBP"].map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Exposure breakdown */}
        <Card>
          <CardContent className="p-4 space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-gray-700 flex items-center gap-2">
                <Globe className="h-4 w-4 text-indigo-500" />
                Currency Exposure
              </p>
              {exposure && (
                <span className="text-xs text-gray-400">
                  Total: €{(exposure.total_value_base / 1_000_000).toFixed(1)}M
                </span>
              )}
            </div>

            {isLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
              </div>
            ) : !exposure || exposure.exposure.length === 0 ? (
              <EmptyState title="No exposure data" description="Add holdings to your portfolios to see currency exposure." />
            ) : (
              <div className="space-y-4">
                {exposure.exposure.map((item) => (
                  <ExposureBar key={item.currency} item={item} max={maxExposure} />
                ))}
              </div>
            )}

            {exposure?.hedging_recommendation && (
              <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
                <strong>Hedging note:</strong> {exposure.hedging_recommendation}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Right column: rates + converter */}
        <div className="space-y-4">
          <RateTable />
          <CurrencyConverter />
        </div>
      </div>
    </div>
  );
}
