"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  SlidersHorizontal,
  Plus,
  ChevronRight,
  Loader2,
  Store,
  ArrowLeftRight,
  FileText,
  CheckCircle,
  XCircle,
  RefreshCw,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
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

// ── Helpers ───────────────────────────────────────────────────────────────────

const TYPE_COLORS: Record<string, string> = {
  solar: "from-amber-400 to-orange-500",
  wind: "from-sky-400 to-blue-500",
  hydro: "from-blue-400 to-cyan-500",
  biomass: "from-green-500 to-emerald-600",
  geothermal: "from-red-400 to-orange-600",
  energy_efficiency: "from-purple-400 to-violet-600",
  other: "from-neutral-400 to-neutral-600",
};

function typeGradient(type: string | null): string {
  return TYPE_COLORS[type ?? "other"] ?? TYPE_COLORS.other;
}

function typeLabel(type: string): string {
  return type.split("_").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

// ── Listing card ──────────────────────────────────────────────────────────────

function ListingCard({ listing }: { listing: ListingResponse }) {
  const router = useRouter();

  return (
    <Card className="overflow-hidden hover:shadow-md transition-shadow">
      {/* Cover gradient */}
      <div
        className={`h-2 bg-gradient-to-r ${typeGradient(listing.project_type)}`}
      />
      <CardContent className="pt-4 pb-4">
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="font-semibold text-sm text-neutral-900 line-clamp-2 flex-1">
            {listing.title}
          </h3>
          <Badge variant={listingStatusVariant(listing.status)} className="shrink-0">
            {listing.status.replace("_", " ")}
          </Badge>
        </div>

        <div className="flex items-center gap-2 flex-wrap mb-3">
          <Badge variant="neutral">
            {LISTING_TYPE_LABELS[listing.listing_type]}
          </Badge>
          {listing.project_type && (
            <span className="text-xs text-neutral-500">
              {typeLabel(listing.project_type)}
            </span>
          )}
          {listing.geography_country && (
            <span className="text-xs text-neutral-500">
              · {listing.geography_country}
            </span>
          )}
        </div>

        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-xs text-neutral-500 mb-0.5">Asking Price</div>
            <div className="text-lg font-bold text-neutral-900">
              {formatPrice(listing.asking_price, listing.currency)}
            </div>
          </div>
          {listing.signal_score != null && (
            <ScoreGauge score={listing.signal_score} size={48} />
          )}
        </div>

        {listing.rfq_count > 0 && (
          <p className="text-xs text-neutral-400 mb-3">
            {listing.rfq_count} RFQ{listing.rfq_count !== 1 ? "s" : ""} received
          </p>
        )}

        <div className="flex gap-2">
          <Button
            size="sm"
            className="flex-1"
            onClick={() => router.push(`/marketplace/${listing.id}`)}
          >
            View <ChevronRight className="h-3 w-3 ml-1" />
          </Button>
          {listing.status === "active" && (
            <Button
              size="sm"
              variant="outline"
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
    <div className="space-y-4 w-56 shrink-0">
      <div>
        <label className="block text-xs font-medium text-neutral-600 mb-1 uppercase tracking-wide">
          Listing Type
        </label>
        <select
          value={filters.listing_type ?? ""}
          onChange={(e) =>
            onChange({ ...filters, listing_type: e.target.value || undefined })
          }
          className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All types</option>
          <option value="equity_sale">Equity Sale</option>
          <option value="debt_sale">Debt Sale</option>
          <option value="co_investment">Co-Investment</option>
          <option value="carbon_credit">Carbon Credits</option>
        </select>
      </div>

      <div>
        <label className="block text-xs font-medium text-neutral-600 mb-1 uppercase tracking-wide">
          Sector
        </label>
        <select
          value={filters.sector ?? ""}
          onChange={(e) =>
            onChange({ ...filters, sector: e.target.value || undefined })
          }
          className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
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
        <label className="block text-xs font-medium text-neutral-600 mb-1 uppercase tracking-wide">
          Geography
        </label>
        <input
          value={filters.geography ?? ""}
          onChange={(e) =>
            onChange({ ...filters, geography: e.target.value || undefined })
          }
          placeholder="Country or region"
          className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-neutral-600 mb-1 uppercase tracking-wide">
          Price Range (USD)
        </label>
        <div className="flex items-center gap-2">
          <input
            type="number"
            placeholder="Min"
            value={filters.price_min ?? ""}
            onChange={(e) =>
              onChange({
                ...filters,
                price_min: e.target.value ? Number(e.target.value) : undefined,
              })
            }
            className="w-full rounded-md border border-neutral-300 px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <span className="text-neutral-400 text-xs">–</span>
          <input
            type="number"
            placeholder="Max"
            value={filters.price_max ?? ""}
            onChange={(e) =>
              onChange({
                ...filters,
                price_max: e.target.value ? Number(e.target.value) : undefined,
              })
            }
            className="w-full rounded-md border border-neutral-300 px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <Button
        variant="outline"
        size="sm"
        className="w-full"
        onClick={() => onChange({})}
      >
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
            <Badge variant="info" className="ml-2">
              {Object.keys(filters).length}
            </Badge>
          )}
        </Button>
        <span className="text-sm text-neutral-500">
          {data?.total ?? 0} listing{data?.total !== 1 ? "s" : ""}
        </span>
      </div>

      <div className="flex gap-6">
        {showFilters && (
          <FilterSidebar filters={filters} onChange={setFilters} />
        )}

        <div className="flex-1">
          {isLoading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
            </div>
          ) : !data?.items?.length ? (
            <EmptyState
              title="No listings found"
              description="Try adjusting your filters or check back later."
              icon={<Store className="h-8 w-8 text-neutral-400" />}
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {data.items.map((listing) => (
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
    currency: "USD",
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
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-lg font-semibold mb-4">Create Listing</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Title</label>
            <input
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              required
              className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">
              Listing Type
            </label>
            <select
              value={form.listing_type}
              onChange={(e) =>
                setForm({ ...form, listing_type: e.target.value as ListingType })
              }
              className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="equity_sale">Equity Sale</option>
              <option value="debt_sale">Debt Sale</option>
              <option value="co_investment">Co-Investment</option>
              <option value="carbon_credit">Carbon Credits</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium mb-1">
                Asking Price
              </label>
              <input
                type="number"
                value={form.asking_price}
                onChange={(e) =>
                  setForm({ ...form, asking_price: e.target.value })
                }
                className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Currency</label>
              <select
                value={form.currency}
                onChange={(e) => setForm({ ...form, currency: e.target.value })}
                className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {["USD", "EUR", "GBP", "KES", "NGN"].map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Visibility</label>
            <select
              value={form.visibility}
              onChange={(e) =>
                setForm({ ...form, visibility: e.target.value as typeof form.visibility })
              }
              className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="public">Public</option>
              <option value="qualified_only">Qualified Investors Only</option>
              <option value="invite_only">Invite Only</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea
              rows={3}
              value={form.description}
              onChange={(e) =>
                setForm({ ...form, description: e.target.value })
              }
              className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={createListing.isPending}>
              {createListing.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : null}
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
      cell: ({ row }) => (
        <span className="font-medium">{row.original.title}</span>
      ),
    },
    {
      accessorKey: "listing_type",
      header: "Type",
      cell: ({ row }) => (
        <Badge variant="neutral">
          {LISTING_TYPE_LABELS[row.original.listing_type]}
        </Badge>
      ),
    },
    {
      accessorKey: "asking_price",
      header: "Asking Price",
      cell: ({ row }) =>
        formatPrice(row.original.asking_price, row.original.currency),
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
        <div className="flex gap-2">
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
        </div>
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
      cell: ({ row }) => (
        <span className="font-medium">{row.original.listing_title ?? "—"}</span>
      ),
    },
    {
      accessorKey: "proposed_price",
      header: "Proposed Price",
      cell: ({ row }) =>
        formatPrice(row.original.proposed_price, row.original.currency),
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
        if (
          view !== "received" ||
          !["submitted", "countered"].includes(row.original.status)
        ) {
          return null;
        }
        return (
          <div className="flex gap-1">
            <Button
              size="sm"
              variant="ghost"
              className="text-green-600 hover:bg-green-50"
              onClick={() =>
                respond.mutate({ rfqId: row.original.id, action: "accept" })
              }
              title="Accept"
            >
              <CheckCircle className="h-4 w-4" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="text-red-600 hover:bg-red-50"
              onClick={() =>
                respond.mutate({ rfqId: row.original.id, action: "reject" })
              }
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
        <Button
          variant={view === "received" ? "default" : "outline"}
          size="sm"
          onClick={() => setView("received")}
        >
          Received ({received?.total ?? 0})
        </Button>
        <Button
          variant={view === "sent" ? "default" : "outline"}
          size="sm"
          onClick={() => setView("sent")}
        >
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
          description={
            view === "received"
              ? "No requests for quote have been received yet."
              : "You haven't submitted any RFQs."
          }
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
      cell: ({ row }) => (
        <span className="font-medium">{row.original.listing_title ?? "—"}</span>
      ),
    },
    {
      accessorKey: "amount",
      header: "Amount",
      cell: ({ row }) =>
        formatPrice(row.original.amount, row.original.currency),
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
          <Button
            size="sm"
            variant="outline"
            onClick={() => complete.mutate(row.original.id)}
            disabled={complete.isPending}
          >
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
  const { data: allListings } = useListings();

  const active = allListings?.items.filter((l) => l.status === "active").length ?? 0;
  const negotiating = allListings?.items.filter((l) => l.status === "under_negotiation").length ?? 0;
  const totalVolume = allListings?.items
    .filter((l) => l.status === "sold")
    .reduce((acc, l) => acc + (l.asking_price ? parseFloat(l.asking_price) : 0), 0) ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-neutral-900">Marketplace</h1>
        <p className="text-sm text-neutral-500 mt-1">
          Secondary market for private impact assets — equity, debt, co-investment, carbon credits
        </p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="text-xs text-neutral-500 mb-1">Active Listings</div>
            <div className="text-2xl font-bold">{active}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="text-xs text-neutral-500 mb-1">In Negotiation</div>
            <div className="text-2xl font-bold text-amber-600">{negotiating}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="text-xs text-neutral-500 mb-1">Volume Transacted</div>
            <div className="text-2xl font-bold text-green-700">
              {totalVolume >= 1_000_000
                ? `$${(totalVolume / 1_000_000).toFixed(1)}M`
                : totalVolume >= 1_000
                ? `$${(totalVolume / 1_000).toFixed(0)}K`
                : `$${totalVolume.toFixed(0)}`}
            </div>
          </CardContent>
        </Card>
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
