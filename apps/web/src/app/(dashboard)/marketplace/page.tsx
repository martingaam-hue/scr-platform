"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  SlidersHorizontal,
  Plus,
  ChevronRight,
  Loader2,
  ArrowLeftRight,
  FileText,
  CheckCircle,
  XCircle,
  RefreshCw,
  Globe,
  TrendingUp,
  BarChart2,
  Zap,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  DataTable,
  EmptyState,
  ScoreGauge,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  type ColumnDef,
} from "@scr/ui";
import {
  useListings,
  useCreateListing,
  useWithdrawListing,
  useSentRFQs,
  useReceivedRFQs,
  useRespondRFQ,
  useTransactions,
  useCompleteTransaction,
  listingStatusVariant,
  rfqStatusVariant,
  txStatusVariant,
  LISTING_TYPE_LABELS,
  RFQ_STATUS_LABELS,
  TX_STATUS_LABELS,
  formatPrice,
  type ListingResponse,
  type RFQResponse,
  type TransactionResponse,
  type ListingFilters,
  type ListingType,
} from "@/lib/marketplace";
import { InfoBanner } from "@/components/info-banner";

// ── Mock listings ──────────────────────────────────────────────────────────────

const MOCK_LISTINGS: ListingResponse[] = [
  {
    id: "l1", title: "Helios Solar Portfolio Iberia — 35% Equity Stake",
    description: "Operational 120 MW solar portfolio across southern Spain. DSCR 1.42, 15-year PPA with Iberdrola.",
    listing_type: "equity_sale", project_type: "solar",
    geography_country: "Spain", asking_price: "48500000", currency: "EUR",
    status: "active", signal_score: 87, rfq_count: 4,
    created_at: new Date(Date.now() - 5 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 1 * 86400000).toISOString(),
    visibility: "qualified_only",
  } as unknown as ListingResponse,
  {
    id: "l2", title: "Nordvik Offshore Wind II — Senior Green Bond",
    description: "EUR 60M senior secured green bond at 5.8% coupon. Norwegian offshore wind, COD Q3 2025.",
    listing_type: "debt_sale", project_type: "wind",
    geography_country: "Norway", asking_price: "60000000", currency: "EUR",
    status: "active", signal_score: 82, rfq_count: 2,
    created_at: new Date(Date.now() - 8 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 2 * 86400000).toISOString(),
    visibility: "qualified_only",
  } as unknown as ListingResponse,
  {
    id: "l3", title: "Alpine Hydro Partners — Co-Investment Opportunity",
    description: "Co-invest alongside lead LP in 52 MW run-of-river hydro in Switzerland. Target IRR 14.2%, 8-year hold.",
    listing_type: "co_investment", project_type: "hydro",
    geography_country: "Switzerland", asking_price: "12000000", currency: "EUR",
    status: "active", signal_score: 91, rfq_count: 7,
    created_at: new Date(Date.now() - 3 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 1 * 86400000).toISOString(),
    visibility: "invite_only",
  } as unknown as ListingResponse,
  {
    id: "l4", title: "Baltic BESS Grid Storage — Carbon Credits Tranche",
    description: "Verified carbon reduction credits from 180 MWh grid-scale BESS in Lithuania. Gold Standard certified.",
    listing_type: "carbon_credit", project_type: "other",
    geography_country: "Lithuania", asking_price: "3200000", currency: "EUR",
    status: "active", signal_score: 65, rfq_count: 1,
    created_at: new Date(Date.now() - 12 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 3 * 86400000).toISOString(),
    visibility: "public",
  } as unknown as ListingResponse,
  {
    id: "l5", title: "Thames Clean Energy Hub — 20% Equity Divestment",
    description: "Partial exit from 80 MW mixed wind/solar hub in UK. CfD-backed revenue stream, operational since 2022.",
    listing_type: "equity_sale", project_type: "wind",
    geography_country: "UK", asking_price: "22000000", currency: "GBP",
    status: "under_negotiation", signal_score: 78, rfq_count: 3,
    created_at: new Date(Date.now() - 20 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 4 * 86400000).toISOString(),
    visibility: "qualified_only",
  } as unknown as ListingResponse,
  {
    id: "l6", title: "Nordic Biomass Energy — Project Finance Mezzanine",
    description: "Mezzanine tranche in 18 MW biomass-to-energy plant in Sweden. 12% target return, 5-year tenor.",
    listing_type: "debt_sale", project_type: "biomass",
    geography_country: "Sweden", asking_price: "8000000", currency: "EUR",
    status: "active", signal_score: 71, rfq_count: 0,
    created_at: new Date(Date.now() - 6 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 1 * 86400000).toISOString(),
    visibility: "public",
  } as unknown as ListingResponse,
];

// ── Helpers ────────────────────────────────────────────────────────────────────

const TYPE_GRADIENTS: Record<string, string> = {
  solar: "from-amber-400 to-orange-500",
  wind: "from-sky-400 to-blue-500",
  hydro: "from-blue-400 to-cyan-500",
  biomass: "from-green-500 to-emerald-600",
  geothermal: "from-red-400 to-orange-600",
  energy_efficiency: "from-purple-400 to-violet-600",
  other: "from-neutral-400 to-neutral-600",
};

const LISTING_TYPE_BADGES: Record<string, { label: string; color: string }> = {
  equity_sale:   { label: "Equity Sale",   color: "bg-indigo-100 text-indigo-700" },
  debt_sale:     { label: "Debt / Bond",   color: "bg-blue-100 text-blue-700" },
  co_investment: { label: "Co-Investment", color: "bg-purple-100 text-purple-700" },
  carbon_credit: { label: "Carbon Credits", color: "bg-green-100 text-green-700" },
};

function typeGradient(type: string | null): string {
  return TYPE_GRADIENTS[type ?? "other"] ?? TYPE_GRADIENTS.other;
}

function typeLabel(type: string): string {
  return type.split("_").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

// ── Listing card ──────────────────────────────────────────────────────────────

function ListingCard({ listing }: { listing: ListingResponse }) {
  const router = useRouter();
  const typeBadge = LISTING_TYPE_BADGES[listing.listing_type] ?? { label: listing.listing_type, color: "bg-neutral-100 text-neutral-600" };

  return (
    <Card className="overflow-hidden hover:shadow-lg transition-all border-neutral-200 hover:border-primary-200">
      {/* Cover gradient with type overlay */}
      <div className={`h-28 bg-gradient-to-br ${typeGradient(listing.project_type)} relative`}>
        <div className="absolute inset-0 bg-black/10" />
        <div className="absolute top-3 left-3">
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${typeBadge.color}`}>
            {typeBadge.label}
          </span>
        </div>
        {listing.visibility === "invite_only" && (
          <div className="absolute top-3 right-3">
            <span className="text-[10px] font-semibold bg-white/90 text-neutral-600 px-1.5 py-0.5 rounded">
              Invite Only
            </span>
          </div>
        )}
        <div className="absolute bottom-3 left-3 right-3">
          {listing.project_type && (
            <span className="text-xs font-medium text-white/90">
              {typeLabel(listing.project_type)}
            </span>
          )}
        </div>
      </div>

      <CardContent className="p-4">
        {/* Title + status */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="font-semibold text-sm text-neutral-900 line-clamp-2 flex-1 leading-snug">
            {listing.title}
          </h3>
          <Badge variant={listingStatusVariant(listing.status)} className="shrink-0 text-xs">
            {listing.status.replace("_", " ")}
          </Badge>
        </div>

        {/* Description */}
        {listing.description && (
          <p className="text-xs text-neutral-500 line-clamp-2 mb-3 leading-relaxed">
            {listing.description}
          </p>
        )}

        {/* Geography */}
        {listing.geography_country && (
          <div className="flex items-center gap-1 text-xs text-neutral-400 mb-3">
            <Globe className="h-3 w-3" />
            <span>{listing.geography_country}</span>
          </div>
        )}

        {/* Price + Score */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-[10px] text-neutral-400 font-medium uppercase tracking-wide mb-0.5">Asking Price</div>
            <div className="text-lg font-bold text-neutral-900">
              {formatPrice(listing.asking_price, listing.currency)}
            </div>
          </div>
          {listing.signal_score != null && (
            <ScoreGauge score={listing.signal_score} size={52} strokeWidth={6} fullCircle label="" />
          )}
        </div>

        {/* RFQ count */}
        {listing.rfq_count > 0 && (
          <p className="text-xs text-neutral-400 mb-3 flex items-center gap-1">
            <ArrowLeftRight className="h-3 w-3" />
            {listing.rfq_count} RFQ{listing.rfq_count !== 1 ? "s" : ""} received
          </p>
        )}

        <div className="flex gap-2">
          <Button
            size="sm"
            className="flex-1 text-xs"
            onClick={() => router.push(`/marketplace/${listing.id}`)}
          >
            View Details <ChevronRight className="h-3 w-3 ml-1" />
          </Button>
          {listing.status === "active" && (
            <Button
              size="sm"
              variant="outline"
              className="text-xs"
              onClick={() => router.push(`/marketplace/${listing.id}?rfq=1`)}
            >
              RFQ
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Filter sidebar ────────────────────────────────────────────────────────────

function FilterSidebar({
  filters,
  onChange,
}: {
  filters: ListingFilters;
  onChange: (f: ListingFilters) => void;
}) {
  return (
    <div className="space-y-5 w-56 shrink-0">
      <div>
        <label className="block text-xs font-semibold text-neutral-600 mb-2 uppercase tracking-wide">
          Listing Type
        </label>
        <select
          value={filters.listing_type ?? ""}
          onChange={(e) => onChange({ ...filters, listing_type: e.target.value || undefined })}
          className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
        >
          <option value="">All types</option>
          <option value="equity_sale">Equity Sale</option>
          <option value="debt_sale">Debt / Bond</option>
          <option value="co_investment">Co-Investment</option>
          <option value="carbon_credit">Carbon Credits</option>
        </select>
      </div>

      <div>
        <label className="block text-xs font-semibold text-neutral-600 mb-2 uppercase tracking-wide">
          Sector
        </label>
        <select
          value={filters.sector ?? ""}
          onChange={(e) => onChange({ ...filters, sector: e.target.value || undefined })}
          className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
        >
          <option value="">All sectors</option>
          <option value="solar">Solar</option>
          <option value="wind">Wind</option>
          <option value="hydro">Hydro</option>
          <option value="biomass">Biomass</option>
          <option value="geothermal">Geothermal</option>
          <option value="energy_efficiency">Energy Efficiency</option>
        </select>
      </div>

      <div>
        <label className="block text-xs font-semibold text-neutral-600 mb-2 uppercase tracking-wide">
          Geography
        </label>
        <input
          value={filters.geography ?? ""}
          onChange={(e) => onChange({ ...filters, geography: e.target.value || undefined })}
          placeholder="Country or region"
          className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
        />
      </div>

      <div>
        <label className="block text-xs font-semibold text-neutral-600 mb-2 uppercase tracking-wide">
          Price Range (EUR)
        </label>
        <div className="flex items-center gap-2">
          <input
            type="number"
            placeholder="Min"
            value={filters.price_min ?? ""}
            onChange={(e) => onChange({ ...filters, price_min: e.target.value ? Number(e.target.value) : undefined })}
            className="w-full rounded-lg border border-neutral-300 px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
          />
          <span className="text-neutral-400 text-xs">–</span>
          <input
            type="number"
            placeholder="Max"
            value={filters.price_max ?? ""}
            onChange={(e) => onChange({ ...filters, price_max: e.target.value ? Number(e.target.value) : undefined })}
            className="w-full rounded-lg border border-neutral-300 px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
          />
        </div>
      </div>

      <Button variant="outline" size="sm" className="w-full" onClick={() => onChange({})}>
        Clear Filters
      </Button>
    </div>
  );
}

// ── Browse tab ────────────────────────────────────────────────────────────────

function BrowseTab() {
  const [filters, setFilters] = useState<ListingFilters>({});
  const [showFilters, setShowFilters] = useState(false);
  const { data, isLoading } = useListings(filters);

  // Merge API data with mock listings; if API has nothing, show mock
  const displayItems = (data?.items?.length ? data.items : MOCK_LISTINGS).filter((l) => {
    if (filters.listing_type && l.listing_type !== filters.listing_type) return false;
    if (filters.sector && l.project_type !== filters.sector) return false;
    if (filters.geography && !l.geography_country?.toLowerCase().includes(filters.geography.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowFilters(!showFilters)}
        >
          <SlidersHorizontal className="h-4 w-4 mr-2" />
          Filters
          {Object.keys(filters).length > 0 && (
            <Badge variant="info" className="ml-2">{Object.keys(filters).length}</Badge>
          )}
        </Button>
        <span className="text-sm text-neutral-500">
          {displayItems.length} listing{displayItems.length !== 1 ? "s" : ""}
        </span>
      </div>

      <div className="flex gap-6">
        {showFilters && (
          <FilterSidebar filters={filters} onChange={setFilters} />
        )}

        <div className="flex-1">
          {isLoading && !data ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
            </div>
          ) : displayItems.length === 0 ? (
            <EmptyState
              title="No listings match"
              description="Try adjusting your filters."
              icon={<Search className="h-8 w-8 text-neutral-400" />}
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {displayItems.map((listing) => (
                <ListingCard key={listing.id} listing={listing} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Create listing modal ──────────────────────────────────────────────────────

function CreateListingModal({ onClose }: { onClose: () => void }) {
  const createListing = useCreateListing();
  const [form, setForm] = useState({
    title: "",
    description: "",
    listing_type: "equity_sale" as ListingType,
    visibility: "qualified_only" as const,
    asking_price: "",
    currency: "EUR",
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await createListing.mutateAsync({
      title: form.title,
      description: form.description,
      listing_type: form.listing_type,
      visibility: form.visibility,
      asking_price: form.asking_price ? Number(form.asking_price) : null,
      currency: form.currency,
    });
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
        <h2 className="text-lg font-bold mb-4 text-neutral-900">Create Listing</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1 text-neutral-700">Title</label>
            <input
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              required
              placeholder="e.g. Alpine Hydro Partners — Co-Investment Opportunity"
              className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1 text-neutral-700">Listing Type</label>
            <select
              value={form.listing_type}
              onChange={(e) => setForm({ ...form, listing_type: e.target.value as ListingType })}
              className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
            >
              <option value="equity_sale">Equity Sale</option>
              <option value="debt_sale">Debt / Bond</option>
              <option value="co_investment">Co-Investment</option>
              <option value="carbon_credit">Carbon Credits</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium mb-1 text-neutral-700">Asking Price</label>
              <input
                type="number"
                value={form.asking_price}
                onChange={(e) => setForm({ ...form, asking_price: e.target.value })}
                placeholder="0"
                className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-neutral-700">Currency</label>
              <select
                value={form.currency}
                onChange={(e) => setForm({ ...form, currency: e.target.value })}
                className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
              >
                {["EUR", "USD", "GBP", "KES", "NGN"].map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1 text-neutral-700">Visibility</label>
            <select
              value={form.visibility}
              onChange={(e) => setForm({ ...form, visibility: e.target.value as typeof form.visibility })}
              className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
            >
              <option value="public">Public</option>
              <option value="qualified_only">Qualified Investors Only</option>
              <option value="invite_only">Invite Only</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1 text-neutral-700">Description</label>
            <textarea
              rows={3}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Briefly describe the asset, key terms, and investment highlights..."
              className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={createListing.isPending}>
              {createListing.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Create Listing
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── My Listings tab ───────────────────────────────────────────────────────────

function MyListingsTab() {
  const { data, isLoading } = useListings({ status: "active" });
  const withdraw = useWithdrawListing();
  const [showCreate, setShowCreate] = useState(false);

  const columns: ColumnDef<ListingResponse>[] = [
    {
      accessorKey: "title",
      header: "Title",
      cell: ({ row }) => <span className="font-medium">{row.original.title}</span>,
    },
    {
      accessorKey: "listing_type",
      header: "Type",
      cell: ({ row }) => (
        <Badge variant="neutral">{LISTING_TYPE_LABELS[row.original.listing_type]}</Badge>
      ),
    },
    {
      accessorKey: "asking_price",
      header: "Asking Price",
      cell: ({ row }) => formatPrice(row.original.asking_price, row.original.currency),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => (
        <Badge variant={listingStatusVariant(row.original.status)}>
          {row.original.status.replace("_", " ")}
        </Badge>
      ),
    },
    {
      accessorKey: "rfq_count",
      header: "RFQs",
      cell: ({ row }) => row.original.rfq_count,
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => (
        <Button
          size="sm"
          variant="ghost"
          onClick={() => withdraw.mutate(row.original.id)}
          disabled={
            withdraw.isPending ||
            row.original.status === "sold" ||
            row.original.status === "withdrawn"
          }
        >
          Withdraw
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Listing
        </Button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
        </div>
      ) : !data?.items?.length ? (
        <EmptyState
          title="No listings yet"
          description="Create a listing to sell or co-invest in your assets."
          icon={<FileText className="h-8 w-8 text-neutral-400" />}
        />
      ) : (
        <DataTable data={data.items} columns={columns} />
      )}

      {showCreate && <CreateListingModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}

// ── RFQs tab ──────────────────────────────────────────────────────────────────

function RFQsTab() {
  const [view, setView] = useState<"received" | "sent">("received");
  const { data: received, isLoading: loadingReceived } = useReceivedRFQs();
  const { data: sent, isLoading: loadingSent } = useSentRFQs();
  const respond = useRespondRFQ();

  const data = view === "received" ? received : sent;
  const isLoading = view === "received" ? loadingReceived : loadingSent;

  const columns: ColumnDef<RFQResponse>[] = [
    {
      accessorKey: "listing_title",
      header: "Listing",
      cell: ({ row }) => <span className="font-medium">{row.original.listing_title ?? "—"}</span>,
    },
    {
      accessorKey: "proposed_price",
      header: "Proposed Price",
      cell: ({ row }) => formatPrice(row.original.proposed_price, row.original.currency),
    },
    {
      accessorKey: "counter_price",
      header: "Counter",
      cell: ({ row }) =>
        row.original.counter_price
          ? formatPrice(row.original.counter_price, row.original.currency)
          : "—",
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => (
        <Badge variant={rfqStatusVariant(row.original.status)}>
          {RFQ_STATUS_LABELS[row.original.status]}
        </Badge>
      ),
    },
    {
      accessorKey: "message",
      header: "Message",
      cell: ({ row }) => (
        <span className="text-neutral-500 text-xs line-clamp-1 max-w-xs">
          {row.original.message || "—"}
        </span>
      ),
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => {
        if (view !== "received" || !["submitted", "countered"].includes(row.original.status)) return null;
        return (
          <div className="flex gap-1">
            <Button
              size="sm"
              variant="ghost"
              className="text-green-600 hover:bg-green-50"
              onClick={() => respond.mutate({ rfqId: row.original.id, action: "accept" })}
              title="Accept"
            >
              <CheckCircle className="h-4 w-4" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="text-red-600 hover:bg-red-50"
              onClick={() => respond.mutate({ rfqId: row.original.id, action: "reject" })}
              title="Reject"
            >
              <XCircle className="h-4 w-4" />
            </Button>
          </div>
        );
      },
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Button variant={view === "received" ? "default" : "outline"} size="sm" onClick={() => setView("received")}>
          Received ({received?.total ?? 0})
        </Button>
        <Button variant={view === "sent" ? "default" : "outline"} size="sm" onClick={() => setView("sent")}>
          Sent ({sent?.total ?? 0})
        </Button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
        </div>
      ) : !data?.items?.length ? (
        <EmptyState
          title="No RFQs"
          description={view === "received" ? "No requests for quote received yet." : "You haven't submitted any RFQs."}
          icon={<ArrowLeftRight className="h-8 w-8 text-neutral-400" />}
        />
      ) : (
        <DataTable data={data.items} columns={columns} />
      )}
    </div>
  );
}

// ── Transactions tab ──────────────────────────────────────────────────────────

function TransactionsTab() {
  const { data, isLoading } = useTransactions();
  const complete = useCompleteTransaction();

  const columns: ColumnDef<TransactionResponse>[] = [
    {
      accessorKey: "listing_title",
      header: "Asset",
      cell: ({ row }) => <span className="font-medium">{row.original.listing_title ?? "—"}</span>,
    },
    {
      accessorKey: "amount",
      header: "Amount",
      cell: ({ row }) => formatPrice(row.original.amount, row.original.currency),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => (
        <Badge variant={txStatusVariant(row.original.status)}>
          {TX_STATUS_LABELS[row.original.status]}
        </Badge>
      ),
    },
    {
      accessorKey: "completed_at",
      header: "Completed",
      cell: ({ row }) =>
        row.original.completed_at
          ? new Date(row.original.completed_at).toLocaleDateString()
          : "—",
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => {
        if (row.original.status !== "pending") return null;
        return (
          <Button size="sm" variant="outline" onClick={() => complete.mutate(row.original.id)} disabled={complete.isPending}>
            <RefreshCw className="h-3 w-3 mr-1" />
            Complete
          </Button>
        );
      },
    },
  ];

  return isLoading ? (
    <div className="flex items-center justify-center py-12">
      <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
    </div>
  ) : !data?.items?.length ? (
    <EmptyState
      title="No transactions"
      description="Completed transactions will appear here."
      icon={<CheckCircle className="h-8 w-8 text-neutral-400" />}
    />
  ) : (
    <DataTable data={data.items} columns={columns} />
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function MarketplacePage() {
  const { data: apiListings } = useListings();
  const displayListings = apiListings?.items?.length ? apiListings.items : MOCK_LISTINGS;

  const active = displayListings.filter((l) => l.status === "active").length;
  const negotiating = displayListings.filter((l) => l.status === "under_negotiation").length;
  const totalVolume = displayListings
    .filter((l) => l.status === "sold")
    .reduce((acc, l) => acc + (l.asking_price ? parseFloat(l.asking_price) : 0), 0);
  const avgScore = Math.round(
    displayListings.reduce((s, l) => s + (l.signal_score ?? 0), 0) / (displayListings.length || 1)
  );

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Marketplace</h1>
          <p className="text-sm text-neutral-500 mt-1">
            Secondary market for private impact assets — equity, debt, co-investment, carbon credits
          </p>
        </div>
      </div>

      <InfoBanner>
        <strong>Marketplace</strong> surfaces curated investment opportunities matched to your fund&apos;s
        mandate and risk profile. Browse listings, review AI-scored projects, and connect directly with
        deal sponsors through the platform&apos;s warm introduction system.
      </InfoBanner>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-4">
        {[
          { label: "Active Listings",   value: active,     sub: "open for RFQs",        icon: BarChart2,  color: "text-primary-600" },
          { label: "In Negotiation",    value: negotiating, sub: "term sheet stage",     icon: ArrowLeftRight, color: "text-amber-600" },
          { label: "Volume Transacted", value: totalVolume >= 1_000_000
              ? `€${(totalVolume / 1_000_000).toFixed(1)}M`
              : `€${totalVolume.toFixed(0)}`,
            sub: "closed this period", icon: TrendingUp, color: "text-green-600" },
          { label: "Avg Signal Score",  value: avgScore,   sub: "across active listings", icon: Zap,        color: "text-indigo-600" },
        ].map(({ label, value, sub, icon: Icon, color }) => (
          <Card key={label}>
            <CardContent className="pt-4 pb-4">
              <div className="flex items-center gap-2 mb-2">
                <Icon className={`h-4 w-4 ${color}`} />
                <div className="text-xs font-semibold text-neutral-500 uppercase tracking-wide">{label}</div>
              </div>
              <div className={`text-2xl font-bold ${color}`}>{value}</div>
              <div className="text-xs text-neutral-400 mt-0.5">{sub}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Tabs */}
      <Tabs defaultValue="browse">
        <TabsList>
          <TabsTrigger value="browse">
            <Search className="h-4 w-4 mr-2" />
            Browse
          </TabsTrigger>
          <TabsTrigger value="my-listings">
            <FileText className="h-4 w-4 mr-2" />
            My Listings
          </TabsTrigger>
          <TabsTrigger value="rfqs">
            <ArrowLeftRight className="h-4 w-4 mr-2" />
            RFQs
          </TabsTrigger>
          <TabsTrigger value="transactions">
            <CheckCircle className="h-4 w-4 mr-2" />
            Transactions
          </TabsTrigger>
        </TabsList>

        <TabsContent value="browse" className="mt-6">
          <BrowseTab />
        </TabsContent>
        <TabsContent value="my-listings" className="mt-6">
          <MyListingsTab />
        </TabsContent>
        <TabsContent value="rfqs" className="mt-6">
          <RFQsTab />
        </TabsContent>
        <TabsContent value="transactions" className="mt-6">
          <TransactionsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
