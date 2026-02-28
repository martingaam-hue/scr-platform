/**
 * FX Exposure — React Query hooks.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface LatestRatesResponse {
  rates: Record<string, number>;
  rate_date: string | null;
}

export interface CurrencyExposureItem {
  currency: string;
  value_eur: number;
  pct: number;
  project_count: number;
}

export interface FXExposureResponse {
  base_currency: string;
  total_value_base: number;
  exposure: CurrencyExposureItem[];
  hedging_recommendation: string;
}

export interface ConvertRequest {
  amount: number;
  from_currency: string;
  to_currency: string;
  rate_date?: string | null;
}

export interface ConvertResponse {
  amount: number;
  from_currency: string;
  to_currency: string;
  converted_amount: number;
  rate: number | null;
  rate_date: string | null;
}

// ── Query key factories ─────────────────────────────────────────────────────

export const fxKeys = {
  rates: ["fx", "rates"] as const,
  exposure: (portfolioId?: string, baseCurrency?: string) =>
    ["fx", "exposure", portfolioId, baseCurrency] as const,
};

// ── Hooks ───────────────────────────────────────────────────────────────────

export function useFXRates() {
  return useQuery({
    queryKey: fxKeys.rates,
    queryFn: async () => {
      const { data } = await api.get<LatestRatesResponse>("/fx/rates/latest");
      return data;
    },
    staleTime: 60 * 60 * 1000, // 1 hour — ECB rates don't change often
  });
}

export function useFXExposure(portfolioId?: string, baseCurrency: string = "EUR") {
  return useQuery({
    queryKey: fxKeys.exposure(portfolioId, baseCurrency),
    queryFn: async () => {
      const { data } = await api.get<FXExposureResponse>("/fx/exposure", {
        params: { portfolio_id: portfolioId, base_currency: baseCurrency },
      });
      return data;
    },
  });
}

export function useConvertCurrency() {
  return useMutation({
    mutationFn: async (body: ConvertRequest) => {
      const { data } = await api.post<ConvertResponse>("/fx/convert", body);
      return data;
    },
  });
}

export function useRefreshFXRates() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post("/fx/rates/refresh");
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: fxKeys.rates }),
  });
}

// ── Helpers ─────────────────────────────────────────────────────────────────

export const MAJOR_CURRENCIES = ["EUR", "USD", "GBP", "JPY", "CHF", "SEK", "NOK", "DKK"];

export function flagEmoji(currency: string): string {
  const map: Record<string, string> = {
    EUR: "🇪🇺", USD: "🇺🇸", GBP: "🇬🇧", JPY: "🇯🇵",
    CHF: "🇨🇭", SEK: "🇸🇪", NOK: "🇳🇴", DKK: "🇩🇰",
    CAD: "🇨🇦", AUD: "🇦🇺", NZD: "🇳🇿", CNY: "🇨🇳",
    HKD: "🇭🇰", SGD: "🇸🇬", KRW: "🇰🇷", MXN: "🇲🇽",
    BRL: "🇧🇷", INR: "🇮🇳", ZAR: "🇿🇦",
  };
  return map[currency] ?? "🏳️";
}
