/**
 * Marketplace & Liquidity module — types and React Query hooks.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

export type ListingType = "equity_sale" | "debt_sale" | "co_investment" | "carbon_credit";
export type ListingStatus =
  | "draft"
  | "active"
  | "under_negotiation"
  | "sold"
  | "withdrawn"
  | "expired";
export type ListingVisibility = "public" | "qualified_only" | "invite_only";
export type RFQStatus =
  | "submitted"
  | "under_review"
  | "countered"
  | "accepted"
  | "rejected"
  | "withdrawn";
export type TransactionStatus =
  | "pending"
  | "processing"
  | "completed"
  | "cancelled"
  | "disputed";

export interface ListingResponse {
  id: string;
  org_id: string;
  project_id: string | null;
  title: string;
  description: string;
  listing_type: ListingType;
  status: ListingStatus;
  visibility: ListingVisibility;
  asking_price: string | null;
  minimum_investment: string | null;
  currency: string;
  details: Record<string, unknown>;
  expires_at: string | null;
  project_name: string | null;
  project_type: string | null;
  geography_country: string | null;
  signal_score: number | null;
  rfq_count: number;
  created_at: string;
  updated_at: string;
}

export interface ListingListResponse {
  items: ListingResponse[];
  total: number;
}

export interface ListingCreateRequest {
  project_id?: string | null;
  title: string;
  description?: string;
  listing_type: ListingType;
  visibility?: ListingVisibility;
  asking_price?: number | null;
  minimum_investment?: number | null;
  currency?: string;
  details?: Record<string, unknown>;
  expires_at?: string | null;
}

export interface ListingUpdateRequest {
  title?: string;
  description?: string;
  visibility?: ListingVisibility;
  asking_price?: number | null;
  minimum_investment?: number | null;
  details?: Record<string, unknown>;
  expires_at?: string | null;
}

export interface RFQCreateRequest {
  proposed_price: number;
  currency?: string;
  message?: string;
  proposed_terms?: Record<string, unknown>;
}

export interface RFQRespondRequest {
  action: "accept" | "reject" | "counter";
  counter_price?: number | null;
  counter_terms?: Record<string, unknown>;
  message?: string;
}

export interface RFQResponse {
  id: string;
  listing_id: string;
  buyer_org_id: string;
  proposed_price: string;
  currency: string;
  status: RFQStatus;
  message: string;
  counter_price: string | null;
  counter_terms: Record<string, unknown> | null;
  submitted_by: string;
  listing_title: string | null;
  created_at: string;
  updated_at: string;
}

export interface RFQListResponse {
  items: RFQResponse[];
  total: number;
}

export interface TransactionResponse {
  id: string;
  listing_id: string;
  buyer_org_id: string;
  seller_org_id: string;
  rfq_id: string | null;
  amount: string;
  currency: string;
  status: TransactionStatus;
  terms: Record<string, unknown> | null;
  settlement_details: Record<string, unknown> | null;
  completed_at: string | null;
  listing_title: string | null;
  created_at: string;
  updated_at: string;
}

export interface TransactionListResponse {
  items: TransactionResponse[];
  total: number;
}

export interface PriceSuggestion {
  suggested_price: number;
  price_range_min: number;
  price_range_max: number;
  basis: string;
  comparable_count: number;
}

export interface ListingFilters {
  listing_type?: string;
  sector?: string;
  geography?: string;
  price_min?: number;
  price_max?: number;
  status?: string;
}

// ── Query Keys ───────────────────────────────────────────────────────────────

export const marketplaceKeys = {
  all: ["marketplace"] as const,
  listings: (filters?: ListingFilters) =>
    [...marketplaceKeys.all, "listings", filters ?? {}] as const,
  listing: (id: string) => [...marketplaceKeys.all, "listing", id] as const,
  sentRfqs: () => [...marketplaceKeys.all, "rfqs", "sent"] as const,
  receivedRfqs: () => [...marketplaceKeys.all, "rfqs", "received"] as const,
  transactions: () => [...marketplaceKeys.all, "transactions"] as const,
};

// ── Hooks ────────────────────────────────────────────────────────────────────

export function useListings(filters?: ListingFilters) {
  const params = new URLSearchParams();
  if (filters?.listing_type) params.set("listing_type", filters.listing_type);
  if (filters?.sector) params.set("sector", filters.sector);
  if (filters?.geography) params.set("geography", filters.geography);
  if (filters?.price_min != null) params.set("price_min", String(filters.price_min));
  if (filters?.price_max != null) params.set("price_max", String(filters.price_max));
  if (filters?.status) params.set("status", filters.status);
  const qs = params.toString();

  return useQuery({
    queryKey: marketplaceKeys.listings(filters),
    queryFn: () =>
      api
        .get<ListingListResponse>(`/marketplace/listings${qs ? `?${qs}` : ""}`)
        .then((r) => r.data),
  });
}

export function useListing(id: string | undefined) {
  return useQuery({
    queryKey: marketplaceKeys.listing(id ?? ""),
    queryFn: () =>
      api.get<ListingResponse>(`/marketplace/listings/${id}`).then((r) => r.data),
    enabled: !!id,
  });
}

export function useCreateListing() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ListingCreateRequest) =>
      api.post<ListingResponse>("/marketplace/listings", data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: marketplaceKeys.listings() });
    },
  });
}

export function useUpdateListing() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      listingId,
      ...data
    }: ListingUpdateRequest & { listingId: string }) =>
      api
        .put<ListingResponse>(`/marketplace/listings/${listingId}`, data)
        .then((r) => r.data),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: marketplaceKeys.listing(data.id) });
      qc.invalidateQueries({ queryKey: marketplaceKeys.listings() });
    },
  });
}

export function useWithdrawListing() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (listingId: string) =>
      api.delete(`/marketplace/listings/${listingId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: marketplaceKeys.listings() });
    },
  });
}

export function useSubmitRFQ() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      listingId,
      ...data
    }: RFQCreateRequest & { listingId: string }) =>
      api
        .post<RFQResponse>(`/marketplace/listings/${listingId}/rfq`, data)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: marketplaceKeys.sentRfqs() });
    },
  });
}

export function useSentRFQs() {
  return useQuery({
    queryKey: marketplaceKeys.sentRfqs(),
    queryFn: () =>
      api.get<RFQListResponse>("/marketplace/rfqs/sent").then((r) => r.data),
  });
}

export function useReceivedRFQs() {
  return useQuery({
    queryKey: marketplaceKeys.receivedRfqs(),
    queryFn: () =>
      api.get<RFQListResponse>("/marketplace/rfqs/received").then((r) => r.data),
  });
}

export function useRespondRFQ() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      rfqId,
      ...data
    }: RFQRespondRequest & { rfqId: string }) =>
      api
        .put<RFQResponse>(`/marketplace/rfqs/${rfqId}/respond`, data)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: marketplaceKeys.receivedRfqs() });
      qc.invalidateQueries({ queryKey: marketplaceKeys.listings() });
    },
  });
}

export function useTransactions() {
  return useQuery({
    queryKey: marketplaceKeys.transactions(),
    queryFn: () =>
      api
        .get<TransactionListResponse>("/marketplace/transactions")
        .then((r) => r.data),
  });
}

export function useCompleteTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (transactionId: string) =>
      api
        .post<TransactionResponse>(
          `/marketplace/transactions/${transactionId}/complete`,
          {}
        )
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: marketplaceKeys.transactions() });
    },
  });
}

// ── Helpers ──────────────────────────────────────────────────────────────────

export const LISTING_TYPE_LABELS: Record<ListingType, string> = {
  equity_sale: "Equity Sale",
  debt_sale: "Debt Sale",
  co_investment: "Co-Investment",
  carbon_credit: "Carbon Credits",
};

export const RFQ_STATUS_LABELS: Record<RFQStatus, string> = {
  submitted: "Submitted",
  under_review: "Under Review",
  countered: "Countered",
  accepted: "Accepted",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

export const TX_STATUS_LABELS: Record<TransactionStatus, string> = {
  pending: "Pending",
  processing: "Processing",
  completed: "Completed",
  cancelled: "Cancelled",
  disputed: "Disputed",
};

export function rfqStatusVariant(
  status: RFQStatus
): "success" | "error" | "warning" | "info" | "neutral" {
  if (status === "accepted") return "success";
  if (status === "rejected" || status === "withdrawn") return "error";
  if (status === "countered") return "warning";
  if (status === "submitted") return "info";
  return "neutral";
}

export function txStatusVariant(
  status: TransactionStatus
): "success" | "error" | "warning" | "info" | "neutral" {
  if (status === "completed") return "success";
  if (status === "cancelled" || status === "disputed") return "error";
  if (status === "processing") return "info";
  if (status === "pending") return "warning";
  return "neutral";
}

export function listingStatusVariant(
  status: ListingStatus
): "success" | "error" | "warning" | "info" | "neutral" {
  if (status === "sold") return "success";
  if (status === "withdrawn" || status === "expired") return "neutral";
  if (status === "under_negotiation") return "warning";
  if (status === "active") return "info";
  return "neutral";
}

export function formatPrice(value: string | null, currency: string): string {
  if (!value) return "—";
  const n = parseFloat(value);
  if (isNaN(n)) return "—";
  if (Math.abs(n) >= 1_000_000) return `${currency} ${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 1_000) return `${currency} ${(n / 1_000).toFixed(0)}K`;
  return `${currency} ${n.toFixed(2)}`;
}
