"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────────

export interface TaxonomyNode {
  code: string;
  name: string;
  level: number;
  parent_code: string | null;
  sector: string;
  description: string | null;
  is_leaf: boolean;
}

export interface FinancialTemplate {
  id: string;
  name: string;
  taxonomy_code: string;
  description: string | null;
  assumptions: Record<string, unknown>;
  is_system: boolean;
  created_at: string;
}

export interface DCFInput {
  capacity_mw?: number;
  capex_per_mw?: number;
  discount_rate?: number;
  [key: string]: unknown;
}

export interface DCFCashflowRow {
  year: number;
  revenue: number;
  opex: number;
  net: number;
  levered_net?: number;
}

export interface DCFResult {
  npv: number;
  irr: number;
  payback_years: number;
  cashflows: DCFCashflowRow[];
  assumptions_used: Record<string, unknown>;
}

// ── Hooks ──────────────────────────────────────────────────────────────────────

export function useTaxonomy(parentCode?: string, leafOnly?: boolean) {
  return useQuery<TaxonomyNode[]>({
    queryKey: ["taxonomy", parentCode ?? null, leafOnly ?? null],
    queryFn: async () => {
      const params: Record<string, unknown> = {};
      if (parentCode) params.parent_code = parentCode;
      if (leafOnly !== undefined) params.leaf_only = leafOnly;
      const { data } = await api.get("/taxonomy", { params });
      return data;
    },
  });
}

export function useTemplates(taxonomyCode?: string) {
  return useQuery<FinancialTemplate[]>({
    queryKey: ["financial-templates", taxonomyCode ?? null],
    queryFn: async () => {
      const params = taxonomyCode ? { taxonomy_code: taxonomyCode } : {};
      const { data } = await api.get("/financial-templates", { params });
      return data;
    },
  });
}

export function useTemplate(templateId: string) {
  return useQuery<FinancialTemplate>({
    queryKey: ["financial-template-detail", templateId],
    queryFn: async () => {
      const { data } = await api.get(`/financial-templates/${templateId}`);
      return data;
    },
    enabled: !!templateId,
  });
}

export function useComputeDCF() {
  return useMutation({
    mutationFn: async ({
      templateId,
      inputs,
    }: {
      templateId: string;
      inputs: DCFInput;
    }) => {
      const { data } = await api.post(
        `/financial-templates/${templateId}/compute`,
        inputs
      );
      return data as DCFResult;
    },
  });
}
