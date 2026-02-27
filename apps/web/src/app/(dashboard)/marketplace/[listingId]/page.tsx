"use client";

import { useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Loader2, Send, Building2, MapPin, Tag } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  ScoreGauge,
} from "@scr/ui";
import {
  useListing,
  useListings,
  useSubmitRFQ,
  listingStatusVariant,
  LISTING_TYPE_LABELS,
  formatPrice,
  type ListingResponse,
} from "@/lib/marketplace";

// ── RFQ form ──────────────────────────────────────────────────────────────────

function RFQForm({
  listingId,
  currency,
  onClose,
}: {
  listingId: string;
  currency: string;
  onClose: () => void;
}) {
  const submitRFQ = useSubmitRFQ();
  const [form, setForm] = useState({ proposed_price: "", message: "" });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.proposed_price) return;
    await submitRFQ.mutateAsync({
      listingId,
      proposed_price: Number(form.proposed_price),
      currency,
      message: form.message,
    });
    onClose();
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Submit Request for Quote</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">
              Proposed Price ({currency})
            </label>
            <input
              type="number"
              required
              value={form.proposed_price}
              onChange={(e) =>
                setForm({ ...form, proposed_price: e.target.value })
              }
              placeholder="Enter your offer"
              className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">
              Message to Seller
            </label>
            <textarea
              rows={4}
              value={form.message}
              onChange={(e) =>
                setForm({ ...form, message: e.target.value })
              }
              placeholder="Introduce your organisation, investment thesis, or any questions..."
              className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitRFQ.isPending}>
              {submitRFQ.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Send className="h-4 w-4 mr-2" />
              )}
              Submit RFQ
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

// ── Similar listings ──────────────────────────────────────────────────────────

function SimilarListings({
  currentId,
  listingType,
}: {
  currentId: string;
  listingType: string;
}) {
  const router = useRouter();
  const { data } = useListings({ listing_type: listingType });
  const similar = data?.items.filter((l) => l.id !== currentId).slice(0, 3) ?? [];

  if (!similar.length) return null;

  return (
    <div>
      <h3 className="text-sm font-semibold text-neutral-900 mb-3">
        Similar Listings
      </h3>
      <div className="space-y-3">
        {similar.map((l) => (
          <button
            key={l.id}
            onClick={() => router.push(`/marketplace/${l.id}`)}
            className="w-full text-left rounded-lg border border-neutral-200 p-3 hover:border-blue-300 hover:bg-blue-50 transition-all"
          >
            <div className="font-medium text-sm text-neutral-900 line-clamp-1 mb-1">
              {l.title}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-neutral-500">
                {l.geography_country ?? "—"}
              </span>
              <span className="text-sm font-semibold text-neutral-700">
                {formatPrice(l.asking_price, l.currency)}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ListingDetailPage() {
  const { listingId } = useParams<{ listingId: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [showRFQForm, setShowRFQForm] = useState(searchParams.get("rfq") === "1");

  const { data: listing, isLoading } = useListing(listingId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-neutral-400" />
      </div>
    );
  }

  if (!listing) {
    return (
      <EmptyState
        title="Listing not found"
        description="This listing may have been withdrawn or does not exist."
        icon={<Building2 className="h-8 w-8 text-neutral-400" />}
      />
    );
  }

  const canSubmitRFQ =
    listing.status === "active" || listing.status === "under_negotiation";

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Back */}
      <button
        onClick={() => router.push("/marketplace")}
        className="flex items-center gap-1 text-sm text-neutral-500 hover:text-neutral-900"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Marketplace
      </button>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        {/* Main content */}
        <div className="space-y-6">
          {/* Header card */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-start justify-between gap-4 mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap mb-2">
                    <Badge variant="neutral">
                      {LISTING_TYPE_LABELS[listing.listing_type]}
                    </Badge>
                    <Badge variant={listingStatusVariant(listing.status)}>
                      {listing.status.replace("_", " ")}
                    </Badge>
                    <Badge variant="neutral">
                      {listing.visibility.replace("_", " ")}
                    </Badge>
                  </div>
                  <h1 className="text-xl font-bold text-neutral-900">
                    {listing.title}
                  </h1>
                </div>
                {listing.signal_score != null && (
                  <ScoreGauge score={listing.signal_score} size={72} />
                )}
              </div>

              {listing.description && (
                <p className="text-sm text-neutral-600 leading-relaxed mb-4">
                  {listing.description}
                </p>
              )}

              <dl className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm">
                <div className="flex items-center gap-2">
                  <Tag className="h-4 w-4 text-neutral-400" />
                  <dt className="text-neutral-500">Asking Price</dt>
                  <dd className="font-semibold ml-auto">
                    {formatPrice(listing.asking_price, listing.currency)}
                  </dd>
                </div>
                {listing.minimum_investment && (
                  <div className="flex items-center gap-2">
                    <Tag className="h-4 w-4 text-neutral-400" />
                    <dt className="text-neutral-500">Min. Investment</dt>
                    <dd className="font-semibold ml-auto">
                      {formatPrice(listing.minimum_investment, listing.currency)}
                    </dd>
                  </div>
                )}
                {listing.project_type && (
                  <div className="flex items-center gap-2">
                    <Building2 className="h-4 w-4 text-neutral-400" />
                    <dt className="text-neutral-500">Asset Type</dt>
                    <dd className="font-medium ml-auto">
                      {listing.project_type
                        .split("_")
                        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                        .join(" ")}
                    </dd>
                  </div>
                )}
                {listing.geography_country && (
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-neutral-400" />
                    <dt className="text-neutral-500">Geography</dt>
                    <dd className="font-medium ml-auto">
                      {listing.geography_country}
                    </dd>
                  </div>
                )}
              </dl>
            </CardContent>
          </Card>

          {/* Additional details */}
          {Object.keys(listing.details).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Additional Details</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="space-y-2">
                  {Object.entries(listing.details).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-sm">
                      <dt className="text-neutral-500 capitalize">
                        {k.replace(/_/g, " ")}
                      </dt>
                      <dd className="font-medium text-neutral-900">
                        {String(v)}
                      </dd>
                    </div>
                  ))}
                </dl>
              </CardContent>
            </Card>
          )}

          {/* RFQ form */}
          {showRFQForm && canSubmitRFQ && (
            <RFQForm
              listingId={listingId}
              currency={listing.currency}
              onClose={() => setShowRFQForm(false)}
            />
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* CTA */}
          {canSubmitRFQ && !showRFQForm && (
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-neutral-600 mb-4">
                  Interested in this asset? Submit a non-binding request for
                  quote to start the conversation.
                </p>
                <Button
                  className="w-full"
                  onClick={() => setShowRFQForm(true)}
                >
                  <Send className="h-4 w-4 mr-2" />
                  Submit RFQ
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Listing meta */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Listing Info</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-neutral-500">Listed</span>
                <span>{new Date(listing.created_at).toLocaleDateString()}</span>
              </div>
              {listing.expires_at && (
                <div className="flex justify-between">
                  <span className="text-neutral-500">Expires</span>
                  <span>{new Date(listing.expires_at).toLocaleDateString()}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-neutral-500">RFQs received</span>
                <span className="font-medium">{listing.rfq_count}</span>
              </div>
            </CardContent>
          </Card>

          {/* Similar listings */}
          <SimilarListings
            currentId={listingId}
            listingType={listing.listing_type}
          />
        </div>
      </div>
    </div>
  );
}
