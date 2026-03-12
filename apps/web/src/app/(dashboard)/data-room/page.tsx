"use client";

import React, { useState, useCallback, useMemo } from "react";
import {
  Upload,
  LayoutGrid,
  List,
  Trash2,
  Download,
  FileText,
  Image as ImageIcon,
  File,
  Presentation,
  Brain,
  Eye,
  X,
  Loader2,
  MapPin,
  RefreshCw,
  Sparkles,
  Search,
  ChevronRight,
  ZoomIn,
  FileSpreadsheet,
} from "lucide-react";
import {
  Button,
  Badge,
  Card,
  CardContent,
  SearchInput,
  EmptyState,
  StatusDot,
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerBody,
  DrawerFooter,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  DataTable,
  cn,
} from "@scr/ui";
import type { ColumnDef } from "@scr/ui";

import { usePermission } from "@/lib/auth";
import {
  useDocuments,
  useDocument,
  useDocumentDownload,
  useDeleteDocument,
  useAssignDocument,
  useFolderTree,
  useCreateFolder,
  useUpdateFolder,
  useDeleteFolder,
  useBulkDelete,
  useTriggerExtraction,
  useExtractions,
  formatFileSize,
  fileTypeLabel,
  classificationLabel,
  statusColor,
  type DocumentResponse,
  type DocumentListParams,
  type FolderTreeNode,
  type DocumentStatus,
} from "@/lib/dataroom";
import { useProjects, type ProjectResponse } from "@/lib/projects";
import { FolderTree } from "@/components/dataroom/folder-tree";
import { UploadModal } from "@/components/dataroom/upload-modal";
import { DocumentPreview } from "@/components/dataroom/document-preview";
import { ExtractionPanel } from "@/components/dataroom/extraction-panel";
import { InfoBanner } from "@/components/info-banner";

// ── Mock data ──────────────────────────────────────────────────────────────

const MOCK_ABOUT = {
  left: [
    { label: "Project Type", value: "Biochar" },
    { label: "Solution Type", value: "Engineered Carbon Removals" },
    { label: "Standard", value: "Puro Standard" },
    { label: "Co-certification", value: "—" },
    { label: "Registry", value: "Puro Earth" },
    { label: "Registration Number", value: "Not Registered Yet" },
    { label: "Start Date", value: "2025" },
  ],
  right: [
    { label: "Project Length", value: "27 years" },
    { label: "Methodology", value: "Puro Standard Biochar v3", link: true },
    { label: "Annual Credits", value: "139K tCO2e" },
    { label: "Lifetime Credits", value: "3.75M tCO2e" },
    { label: "Vintage Year", value: "2025" },
    { label: "First Year of Delivery", value: "2026" },
    { label: "SDGs", value: "8, 12, 13, 14, 15" },
  ],
  lastAnalyzed: "21 Oct 2025",
};

const MOCK_DOCUMENTS = [
  { id: "d1", name: "View Meeting - OnBase Agenda Online.pdf", date: "17-01-2025", type: "pdf" },
  { id: "d2", name: "Organisation Certification.pdf", date: "27-01-2025", type: "pdf" },
  { id: "d3", name: "Corporate Structure and Bio.pdf", date: "28-01-2025", type: "pdf" },
  { id: "d4", name: "250125DH01 - Org. Structure.pdf", date: "22-10-2025", type: "pdf" },
  { id: "d5", name: "Biochar sampling protocol.pdf", date: "17-01-2025", type: "pdf" },
  { id: "d6", name: "Market Validation.pdf", date: "28-12-2024", type: "pdf" },
  { id: "d7", name: "CO2 Sequestration Calculator.xlsx", date: "17-01-2025", type: "xlsx" },
  { id: "d8", name: "Biochar Analysis.pdf", date: "17-01-2025", type: "pdf" },
  { id: "d9", name: "Biochar Off Take Agreement Full.pdf", date: "21-10-2025", type: "pdf" },
  { id: "d10", name: "MACT Sampling SOP.pdf", date: "21-10-2025", type: "pdf" },
  { id: "d11", name: "Biochar Analysis Report.pdf", date: "21-10-2025", type: "pdf" },
  { id: "d12", name: "250205 - Biochar Analysis.pdf", date: "21-10-2025", type: "pdf" },
  { id: "d13", name: "250122 IBI Biochar Report.pdf", date: "21-10-2025", type: "pdf" },
  { id: "d14", name: "241230 - BET Surface Area for biochar.pdf", date: "21-10-2025", type: "pdf" },
  { id: "d15", name: "241219 - PAH Analysis.pdf", date: "21-10-2025", type: "pdf" },
];

const MOCK_GALLERY = [
  { id: "g1", label: "Site Overview — Aerial", url: "https://placehold.co/300x200/1a2332/ffffff?text=Site+Overview" },
  { id: "g2", label: "Production Facility", url: "https://placehold.co/300x200/1a3322/ffffff?text=Production" },
  { id: "g3", label: "Equipment Installation", url: "https://placehold.co/300x200/1a2332/ffffff?text=Equipment" },
  { id: "g4", label: "Storage Containers", url: "https://placehold.co/300x200/221a33/ffffff?text=Storage" },
  { id: "g5", label: "Pipeline Infrastructure", url: "https://placehold.co/300x200/1a2332/ffffff?text=Pipeline" },
];

// ── Helpers ─────────────────────────────────────────────────────────────────

const IMAGE_EXTENSIONS = new Set(["jpg", "jpeg", "png", "gif", "webp", "svg", "bmp", "tiff"]);

function isImageFile(fileType: string): boolean {
  return IMAGE_EXTENSIONS.has(fileType.toLowerCase());
}

// ── Section heading component ───────────────────────────────────────────────

function SectionHeading({ title, action }: { title: string; action?: React.ReactNode }) {
  return (
    <div className="mb-5">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-xs font-bold uppercase tracking-[0.12em] text-neutral-500">{title}</h2>
        {action}
      </div>
      <div className="h-px bg-gradient-to-r from-primary-200 via-primary-100 to-transparent" />
    </div>
  );
}

// ── File icon helper ────────────────────────────────────────────────────────

function FileTypeIcon({ type, size = "md" }: { type: string; size?: "sm" | "md" | "lg" }) {
  const sizeClass = size === "sm" ? "h-4 w-4" : size === "lg" ? "h-8 w-8" : "h-5 w-5";
  const t = type.toLowerCase();
  if (t === "pdf") return <FileText className={cn(sizeClass, "text-red-500")} />;
  if (t === "xlsx" || t === "xls" || t === "csv" || t === "tsv")
    return <FileSpreadsheet className={cn(sizeClass, "text-green-600")} />;
  if (t === "docx" || t === "doc") return <FileText className={cn(sizeClass, "text-blue-500")} />;
  if (t === "pptx" || t === "ppt") return <Presentation className={cn(sizeClass, "text-orange-500")} />;
  if (isImageFile(t)) return <ImageIcon className={cn(sizeClass, "text-primary-500")} />;
  return <File className={cn(sizeClass, "text-neutral-400")} />;
}

// ── About section ───────────────────────────────────────────────────────────

function AboutSection() {
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState(true);

  const handleRegenerate = () => {
    setGenerating(true);
    setTimeout(() => setGenerating(false), 1800);
  };

  return (
    <section>
      <SectionHeading
        title="About"
        action={
          <div className="flex items-center gap-2">
            <span className="text-xs text-neutral-400">Last analyzed: {MOCK_ABOUT.lastAnalyzed}</span>
            <button
              onClick={handleRegenerate}
              disabled={generating}
              className="flex items-center gap-1.5 rounded-lg border border-neutral-200 bg-white px-2.5 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-50 transition-colors disabled:opacity-50"
            >
              {generating ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <RefreshCw className="h-3 w-3" />
              )}
              Regenerate
            </button>
            {!generated && (
              <button
                onClick={() => setGenerated(true)}
                className="flex items-center gap-1.5 rounded-lg bg-primary-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-primary-700 transition-colors"
              >
                <Sparkles className="h-3 w-3" />
                Generate Summary
              </button>
            )}
          </div>
        }
      />

      <div className="rounded-xl border border-neutral-200 bg-white overflow-hidden">
        {/* Key-value grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-neutral-100">
          {/* Left column */}
          <div className="divide-y divide-neutral-50">
            {MOCK_ABOUT.left.map(({ label, value }) => (
              <div key={label} className="flex items-baseline gap-4 px-5 py-3">
                <span className="w-44 shrink-0 text-xs text-neutral-400 font-medium">{label}</span>
                <span className="text-sm font-semibold text-neutral-900">{value}</span>
              </div>
            ))}
          </div>
          {/* Right column */}
          <div className="divide-y divide-neutral-50">
            {MOCK_ABOUT.right.map(({ label, value, link }) => (
              <div key={label} className="flex items-baseline gap-4 px-5 py-3">
                <span className="w-44 shrink-0 text-xs text-neutral-400 font-medium">{label}</span>
                {link ? (
                  <span className="text-sm font-semibold text-primary-600 underline underline-offset-2 cursor-pointer hover:text-primary-700">
                    {value}
                  </span>
                ) : (
                  <span className="text-sm font-semibold text-neutral-900">{value}</span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Map */}
        <div className="border-t border-neutral-100">
          <div className="relative h-44 bg-neutral-100 overflow-hidden">
            <iframe
              src="https://www.openstreetmap.org/export/embed.html?bbox=-112.3910%2C40.6608%2C-111.3910%2C40.8608&layer=mapnik&marker=40.7608%2C-111.8910"
              className="w-full h-full border-0"
              title="Project location"
            />
            <div className="absolute bottom-3 left-3 flex items-center gap-1.5 rounded-full bg-white/90 px-3 py-1.5 text-xs font-medium text-neutral-700 shadow-sm border border-neutral-200">
              <MapPin className="h-3.5 w-3.5 text-red-500" />
              40.7608°N, 111.8910°W
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// ── Documents section ────────────────────────────────────────────────────────

function MockDocumentsSection() {
  const [search, setSearch] = useState("");
  const [showAll, setShowAll] = useState(false);

  const filtered = MOCK_DOCUMENTS.filter((d) =>
    d.name.toLowerCase().includes(search.toLowerCase())
  );
  const visible = showAll ? filtered : filtered.slice(0, 9);

  return (
    <section>
      <SectionHeading
        title="Documents"
        action={
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-neutral-400" />
            <input
              type="text"
              placeholder="Search files…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8 pr-3 py-1.5 text-xs border border-neutral-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary-300 w-52"
            />
          </div>
        }
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {visible.map((doc) => (
          <div
            key={doc.id}
            className="flex items-center gap-3 rounded-lg border border-neutral-200 bg-white px-4 py-3 hover:bg-neutral-50 hover:border-neutral-300 transition-colors cursor-pointer group"
          >
            <FileTypeIcon type={doc.type} size="md" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-neutral-900 truncate group-hover:text-primary-700 transition-colors">
                {doc.name}
              </p>
              <p className="text-xs text-neutral-400 mt-0.5">{doc.date}</p>
            </div>
          </div>
        ))}
      </div>

      {filtered.length > 9 && (
        <div className="mt-4 flex justify-end">
          <button
            onClick={() => setShowAll(!showAll)}
            className="flex items-center gap-1.5 text-xs font-medium text-primary-600 hover:text-primary-700 transition-colors"
          >
            {showAll ? "Show Less" : `View All (${filtered.length})`}
            <ChevronRight className={cn("h-3.5 w-3.5 transition-transform", showAll && "rotate-90")} />
          </button>
        </div>
      )}

      {filtered.length === 0 && (
        <p className="text-sm text-neutral-400 py-6 text-center">No files match &ldquo;{search}&rdquo;</p>
      )}
    </section>
  );
}

// ── Gallery section ─────────────────────────────────────────────────────────

function GallerySection({ images }: { images: DocumentResponse[] }) {
  const [lightbox, setLightbox] = useState<string | null>(null);
  const [lightboxLabel, setLightboxLabel] = useState<string>("");

  // Merge real images with mock gallery
  const mockItems = MOCK_GALLERY.map((g) => ({ id: g.id, url: g.url, label: g.label }));
  const realItems = images.map((img) => ({ id: img.id, url: null, label: img.name }));
  const allItems = [...realItems, ...mockItems];

  return (
    <section>
      <SectionHeading
        title="Gallery"
        action={
          allItems.length > 6 ? (
            <button className="flex items-center gap-1.5 text-xs font-medium text-primary-600 hover:text-primary-700 transition-colors">
              View All <ChevronRight className="h-3.5 w-3.5" />
            </button>
          ) : undefined
        }
      />

      <div className="flex gap-3 overflow-x-auto pb-2">
        {allItems.slice(0, 6).map((item) => (
          <div
            key={item.id}
            onClick={() => { setLightbox(item.url ?? item.label); setLightboxLabel(item.label); }}
            className="group relative shrink-0 w-40 h-28 rounded-xl overflow-hidden border border-neutral-200 cursor-pointer shadow-sm hover:shadow-md transition-shadow"
          >
            {item.url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={item.url} alt={item.label} className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full bg-neutral-100 flex items-center justify-center">
                <ImageIcon className="h-8 w-8 text-neutral-300" />
              </div>
            )}
            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/25 transition-colors flex items-center justify-center">
              <ZoomIn className="h-5 w-5 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
            <div className="absolute bottom-0 inset-x-0 px-2 py-1.5 bg-gradient-to-t from-black/60 to-transparent">
              <p className="text-[10px] font-medium text-white truncate">{item.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Lightbox */}
      {lightbox && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
          onClick={() => setLightbox(null)}
        >
          <button
            className="absolute top-4 right-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20 transition-colors"
            onClick={() => setLightbox(null)}
          >
            <X className="h-5 w-5" />
          </button>
          <div className="max-w-3xl max-h-[80vh] overflow-hidden rounded-xl" onClick={(e) => e.stopPropagation()}>
            {lightbox.startsWith("http") ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={lightbox} alt={lightboxLabel} className="max-w-full max-h-[80vh] object-contain rounded-xl" />
            ) : (
              <div className="w-96 h-64 bg-neutral-800 rounded-xl flex items-center justify-center">
                <div className="text-center">
                  <ImageIcon className="h-12 w-12 text-neutral-500 mx-auto mb-3" />
                  <p className="text-sm text-neutral-400">{lightboxLabel}</p>
                </div>
              </div>
            )}
            <p className="text-center text-sm text-white/70 mt-3">{lightboxLabel}</p>
          </div>
        </div>
      )}
    </section>
  );
}

// ── Folder name dialog ─────────────────────────────────────────────────────

function FolderNameDialog({
  open,
  title,
  initialValue,
  onSubmit,
  onClose,
}: {
  open: boolean;
  title: string;
  initialValue: string;
  onSubmit: (name: string) => void;
  onClose: () => void;
}) {
  const [name, setName] = useState(initialValue);

  React.useEffect(() => {
    setName(initialValue);
  }, [initialValue, open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-sm rounded-lg border border-neutral-200 bg-white p-6 shadow-xl">
        <h3 className="text-lg font-semibold text-neutral-900">{title}</h3>
        <input
          autoFocus
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && name.trim()) onSubmit(name.trim());
            if (e.key === "Escape") onClose();
          }}
          placeholder="Folder name"
          className="mt-3 w-full rounded-md border border-neutral-300 px-3 py-2 text-sm outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
        />
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="outline" size="sm" onClick={onClose}>Cancel</Button>
          <Button size="sm" disabled={!name.trim()} onClick={() => onSubmit(name.trim())}>Save</Button>
        </div>
      </div>
    </div>
  );
}

// ── Table columns ──────────────────────────────────────────────────────────

function useTableColumns(): ColumnDef<DocumentResponse, unknown>[] {
  return useMemo(
    () => [
      {
        id: "name",
        header: "Name",
        accessorKey: "name",
        cell: ({ row }) => (
          <div className="flex items-center gap-2">
            <FileTypeIcon type={row.original.file_type} size="sm" />
            <span className="truncate font-medium">{row.original.name}</span>
          </div>
        ),
      },
      {
        id: "file_type",
        header: "Type",
        accessorKey: "file_type",
        cell: ({ row }) => (
          <Badge variant="neutral">{fileTypeLabel(row.original.file_type)}</Badge>
        ),
      },
      {
        id: "status",
        header: "Status",
        accessorKey: "status",
        cell: ({ row }) => (
          <StatusDot status={statusColor(row.original.status)} label={row.original.status} />
        ),
      },
      {
        id: "classification",
        header: "Classification",
        accessorKey: "classification",
        cell: ({ row }) =>
          row.original.classification ? (
            <Badge variant="info">{classificationLabel(row.original.classification)}</Badge>
          ) : (
            <span className="text-neutral-400">—</span>
          ),
      },
      {
        id: "file_size_bytes",
        header: "Size",
        accessorKey: "file_size_bytes",
        cell: ({ row }) => (
          <span className="text-neutral-500">{formatFileSize(row.original.file_size_bytes)}</span>
        ),
      },
      {
        id: "created_at",
        header: "Uploaded",
        accessorKey: "created_at",
        cell: ({ row }) => (
          <span className="text-neutral-500">
            {new Date(row.original.created_at).toLocaleDateString()}
          </span>
        ),
      },
    ],
    []
  );
}

// ── Document detail drawer ─────────────────────────────────────────────────

function DetailDrawer({
  documentId,
  onClose,
  canEdit,
  projects,
}: {
  documentId: string;
  onClose: () => void;
  canEdit: boolean;
  projects: ProjectResponse[];
}) {
  const { data: doc, isLoading } = useDocument(documentId);
  const download = useDocumentDownload();
  const deleteDoc = useDeleteDocument();
  const assignDoc = useAssignDocument();
  const [assignProjectId, setAssignProjectId] = React.useState<string>("");
  const triggerExtraction = useTriggerExtraction();
  const { data: extractions, isLoading: extractionsLoading } = useExtractions(documentId);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const handleDownload = useCallback(async () => {
    const result = await download.mutateAsync(documentId);
    window.open(result.download_url, "_blank");
  }, [download, documentId]);

  React.useEffect(() => {
    if (doc && !previewUrl) {
      download.mutateAsync(documentId)
        .then((r) => setPreviewUrl(r.download_url))
        .catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId, doc]);

  if (isLoading || !doc) {
    return (
      <DrawerContent side="right" className="w-full max-w-lg">
        <div className="flex h-full items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
        </div>
      </DrawerContent>
    );
  }

  return (
    <DrawerContent side="right" className="w-full max-w-lg">
      <DrawerHeader>
        <div className="flex items-center justify-between">
          <DrawerTitle className="truncate pr-4">{doc.name}</DrawerTitle>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-neutral-400 hover:text-neutral-600"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <Badge variant="neutral">{fileTypeLabel(doc.file_type)}</Badge>
          <StatusDot status={statusColor(doc.status)} label={doc.status} />
          {doc.classification && (
            <Badge variant="info">{classificationLabel(doc.classification)}</Badge>
          )}
          <span className="text-xs text-neutral-500">
            v{doc.version} &middot; {formatFileSize(doc.file_size_bytes)}
          </span>
        </div>
      </DrawerHeader>

      <DrawerBody>
        <Tabs defaultValue="preview">
          <TabsList>
            <TabsTrigger value="preview">
              <Eye className="mr-1 h-3.5 w-3.5" />
              Preview
            </TabsTrigger>
            <TabsTrigger value="extractions" badge={extractions?.length}>
              <Brain className="mr-1 h-3.5 w-3.5" />
              AI Insights
            </TabsTrigger>
            <TabsTrigger value="details">
              <FileText className="mr-1 h-3.5 w-3.5" />
              Details
            </TabsTrigger>
          </TabsList>

          <TabsContent value="preview" className="mt-3">
            <div className="h-[400px]">
              <DocumentPreview url={previewUrl} fileType={doc.file_type} fileName={doc.name} />
            </div>
          </TabsContent>

          <TabsContent value="extractions" className="mt-3">
            <ExtractionPanel
              extractions={extractions ?? doc.extractions}
              loading={extractionsLoading}
              onReExtract={
                canEdit
                  ? (types) => triggerExtraction.mutate({ documentId, extraction_types: types })
                  : undefined
              }
              reExtracting={triggerExtraction.isPending}
            />
          </TabsContent>

          <TabsContent value="details" className="mt-3">
            <div className="space-y-4">
              <DrawerDetailRow label="File type" value={doc.file_type.toUpperCase()} />
              <DrawerDetailRow label="MIME type" value={doc.mime_type} />
              <DrawerDetailRow label="Size" value={formatFileSize(doc.file_size_bytes)} />
              <DrawerDetailRow label="Version" value={`v${doc.version}`} />
              <DrawerDetailRow label="Uploaded" value={new Date(doc.created_at).toLocaleString()} />
              <DrawerDetailRow label="Updated" value={new Date(doc.updated_at).toLocaleString()} />
              <DrawerDetailRow label="Watermark" value={doc.watermark_enabled ? "Enabled" : "Disabled"} />
              <DrawerDetailRow label="Checksum" value={doc.checksum_sha256.slice(0, 16) + "..."} />
              {doc.version_count > 1 && (
                <DrawerDetailRow label="Versions" value={`${doc.version_count} versions`} />
              )}
            </div>
          </TabsContent>
        </Tabs>
      </DrawerBody>

      <DrawerFooter>
        {canEdit && !doc.project_id && projects.length > 0 && (
          <div className="flex w-full items-center gap-2 pb-2 border-b border-neutral-200">
            <select
              value={assignProjectId}
              onChange={(e) => setAssignProjectId(e.target.value)}
              className="flex-1 rounded-md border border-neutral-300 bg-white px-2 py-1.5 text-xs"
            >
              <option value="">Assign to project…</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            <Button
              size="sm"
              disabled={!assignProjectId}
              loading={assignDoc.isPending}
              onClick={async () => {
                if (!assignProjectId) return;
                await assignDoc.mutateAsync({ documentId, project_id: assignProjectId });
                onClose();
              }}
            >
              Assign
            </Button>
          </div>
        )}
        <Button
          variant="outline"
          size="sm"
          onClick={handleDownload}
          loading={download.isPending}
          iconLeft={<Download className="h-3.5 w-3.5" />}
        >
          Download
        </Button>
        {canEdit && (
          <Button
            variant="destructive"
            size="sm"
            onClick={async () => {
              await deleteDoc.mutateAsync(documentId);
              onClose();
            }}
            loading={deleteDoc.isPending}
            iconLeft={<Trash2 className="h-3.5 w-3.5" />}
          >
            Delete
          </Button>
        )}
      </DrawerFooter>
    </DrawerContent>
  );
}

function DrawerDetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-neutral-500">{label}</span>
      <span className="font-medium text-neutral-900">{value}</span>
    </div>
  );
}

// ── Folder structure section ────────────────────────────────────────────────

function FolderTreeSkeleton() {
  return (
    <div className="space-y-2 p-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="h-6 animate-pulse rounded bg-neutral-100" style={{ width: `${70 + i * 5}%` }} />
      ))}
    </div>
  );
}

function GridSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="h-40 animate-pulse rounded-lg border border-neutral-200 bg-neutral-100" />
      ))}
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────

export default function DataRoomPage() {
  const canUpload = usePermission("upload", "document");
  const canEdit = usePermission("edit", "document");
  const canDelete = usePermission("delete", "document");

  const [projectId, setProjectId] = useState<string>("");
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"grid" | "list">("list");
  const [search, setSearch] = useState("");
  const [selectedDocIds, setSelectedDocIds] = useState<Set<string>>(new Set());
  const [detailDocId, setDetailDocId] = useState<string | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [folderDialog, setFolderDialog] = useState<{
    open: boolean;
    title: string;
    initialValue: string;
    parentId: string | null;
    folderId?: string;
  }>({ open: false, title: "", initialValue: "", parentId: null });
  const [page, setPage] = useState(1);
  const [sortBy] = useState("created_at");
  const [sortOrder] = useState<"asc" | "desc">("desc");
  const [statusFilter, setStatusFilter] = useState<DocumentStatus | undefined>();

  const { data: projectList } = useProjects({ page_size: 100 });
  const projects: ProjectResponse[] = projectList?.items ?? [];

  const isUnassigned = projectId === "UNASSIGNED";

  const params: DocumentListParams = {
    project_id: !isUnassigned ? (projectId || undefined) : undefined,
    unassigned: isUnassigned ? true : undefined,
    folder_id: isUnassigned ? undefined : selectedFolderId,
    search: search || undefined,
    page,
    page_size: 20,
    sort_by: sortBy,
    sort_order: sortOrder,
    status: statusFilter,
  };

  const { data: docList, isLoading: docsLoading, isFetching: docsFetching } = useDocuments(params);
  const { data: folders, isLoading: foldersLoading } = useFolderTree(projectId || undefined);

  const createFolder = useCreateFolder();
  const updateFolder = useUpdateFolder();
  const deleteFolder = useDeleteFolder();
  const bulkDelete = useBulkDelete();
  const columns = useTableColumns();

  const handleSelectDoc = useCallback((id: string) => {
    setSelectedDocIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleBulkDelete = useCallback(async () => {
    if (selectedDocIds.size === 0) return;
    await bulkDelete.mutateAsync({ document_ids: Array.from(selectedDocIds) });
    setSelectedDocIds(new Set());
  }, [selectedDocIds, bulkDelete]);

  const handleCreateFolder = useCallback((parentId: string | null) => {
    setFolderDialog({ open: true, title: "New Folder", initialValue: "", parentId });
  }, []);

  const handleRenameFolder = useCallback((folder: FolderTreeNode) => {
    setFolderDialog({
      open: true,
      title: "Rename Folder",
      initialValue: folder.name,
      parentId: folder.parent_folder_id,
      folderId: folder.id,
    });
  }, []);

  const handleFolderDialogSubmit = useCallback(
    async (name: string) => {
      if (folderDialog.folderId) {
        await updateFolder.mutateAsync({ folderId: folderDialog.folderId, name });
      } else {
        await createFolder.mutateAsync({ name, project_id: projectId, parent_folder_id: folderDialog.parentId });
      }
      setFolderDialog((prev) => ({ ...prev, open: false }));
    },
    [folderDialog, createFolder, updateFolder, projectId]
  );

  const handleDeleteFolder = useCallback(
    async (folderId: string) => { await deleteFolder.mutateAsync(folderId); },
    [deleteFolder]
  );

  const documents = docList?.items ?? [];
  const totalDocs = docList?.total ?? 0;
  const totalPages = docList?.total_pages ?? 0;

  // Separate docs and images from API data
  const imageDocs = documents.filter((d) => isImageFile(d.file_type));
  const textDocs = documents.filter((d) => !isImageFile(d.file_type));

  // ── No project selected ─────────────────────────────────────────────────
  if (!projectId) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-100 rounded-lg">
            <Brain className="h-6 w-6 text-primary-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">Data Room</h1>
            <p className="mt-1 text-sm text-neutral-500">
              AI-powered document management with auto-detection and project summaries
            </p>
          </div>
        </div>

        <InfoBanner>
          The <strong>Virtual Data Room</strong> provides secure document sharing with AI-generated project summaries,
          automatic file categorization, and engagement analytics. Track who viewed which documents and for how long.
        </InfoBanner>

        <EmptyState
          icon={<Brain className="h-8 w-8" />}
          title="Select a project"
          description="Choose a project to view its AI summary, documents, and gallery."
          action={
            <select
              className="border border-neutral-300 rounded-lg px-3 py-2 text-sm bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 min-w-[260px]"
              value=""
              onChange={(e) => e.target.value && setProjectId(e.target.value)}
            >
              <option value="">— Select a project —</option>
              <option value="UNASSIGNED">📥 Unassigned Documents</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          }
        />
      </div>
    );
  }

  // ── Main layout ─────────────────────────────────────────────────────────
  return (
    <div className="space-y-8">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-100 rounded-lg shrink-0">
            <Brain className="h-6 w-6 text-primary-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">Data Room</h1>
            <p className="mt-1 text-sm text-neutral-500">
              {totalDocs} document{totalDocs !== 1 ? "s" : ""}{selectedFolderId ? " in folder" : " total"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <select
            className="border border-neutral-300 rounded-lg px-3 py-1.5 text-sm bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            value={projectId}
            onChange={(e) => { setProjectId(e.target.value); setSelectedFolderId(null); setPage(1); }}
          >
            <option value="UNASSIGNED">📥 Unassigned</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          {canUpload && (
            <Button onClick={() => setUploadOpen(true)} iconLeft={<Upload className="h-4 w-4" />}>
              Upload
            </Button>
          )}
        </div>
      </div>

      {/* ── ABOUT ──────────────────────────────────────────────────────────── */}
      {!isUnassigned && <AboutSection />}

      {/* ── DOCUMENTS ──────────────────────────────────────────────────────── */}
      <MockDocumentsSection />

      {/* ── GALLERY ────────────────────────────────────────────────────────── */}
      <GallerySection images={imageDocs} />

      {/* ── FOLDER STRUCTURE ───────────────────────────────────────────────── */}
      {!isUnassigned && (
        <section>
          <SectionHeading
            title="Folder Structure"
            action={
              <div className="flex items-center gap-3">
                <select
                  value={statusFilter ?? ""}
                  onChange={(e) => { setStatusFilter((e.target.value as DocumentStatus) || undefined); setPage(1); }}
                  className="rounded-md border border-neutral-300 bg-white px-3 py-1.5 text-xs text-neutral-700"
                >
                  <option value="">All statuses</option>
                  <option value="ready">Ready</option>
                  <option value="processing">Processing</option>
                  <option value="uploading">Uploading</option>
                  <option value="error">Error</option>
                </select>
                <div className="flex rounded-md border border-neutral-200">
                  <button
                    onClick={() => setViewMode("grid")}
                    className={cn("rounded-l-md p-1.5 transition-colors",
                      viewMode === "grid" ? "bg-primary-50 text-primary-600" : "text-neutral-400 hover:text-neutral-600"
                    )}
                  ><LayoutGrid className="h-4 w-4" /></button>
                  <button
                    onClick={() => setViewMode("list")}
                    className={cn("rounded-r-md p-1.5 transition-colors",
                      viewMode === "list" ? "bg-primary-50 text-primary-600" : "text-neutral-400 hover:text-neutral-600"
                    )}
                  ><List className="h-4 w-4" /></button>
                </div>
              </div>
            }
          />

          <div className="flex gap-4">
            {/* Folder tree */}
            <div className="w-[220px] shrink-0 overflow-hidden rounded-lg border border-neutral-200 bg-white">
              {foldersLoading ? (
                <FolderTreeSkeleton />
              ) : (
                <FolderTree
                  folders={folders ?? []}
                  selectedFolderId={selectedFolderId}
                  onSelectFolder={(id) => { setSelectedFolderId(id); setPage(1); }}
                  onCreateFolder={handleCreateFolder}
                  onRenameFolder={handleRenameFolder}
                  onDeleteFolder={handleDeleteFolder}
                  canEdit={canEdit}
                />
              )}
            </div>

            {/* Document browser */}
            <div className="min-w-0 flex-1">
              {/* Toolbar */}
              <div className="mb-4 flex flex-wrap items-center gap-3">
                <SearchInput
                  value={search}
                  onValueChange={(v) => { setSearch(v); setPage(1); }}
                  placeholder="Search documents..."
                  shortcutHint=""
                  className="w-56"
                />
                <div className="flex-1" />
                {selectedDocIds.size > 0 && (
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-neutral-500">{selectedDocIds.size} selected</span>
                    {canDelete && (
                      <Button
                        variant="destructive" size="sm"
                        onClick={handleBulkDelete} loading={bulkDelete.isPending}
                        iconLeft={<Trash2 className="h-3.5 w-3.5" />}
                      >
                        Delete
                      </Button>
                    )}
                    <Button variant="ghost" size="sm" onClick={() => setSelectedDocIds(new Set())}>Clear</Button>
                  </div>
                )}
              </div>

              {docsLoading ? (
                <GridSkeleton />
              ) : documents.length === 0 ? (
                <EmptyState
                  icon={<FileText className="h-8 w-8" />}
                  title="No documents found"
                  description={search ? `No documents match \u201c${search}\u201d.` : "Upload your first document to get started."}
                  action={
                    canUpload ? (
                      <Button onClick={() => setUploadOpen(true)} iconLeft={<Upload className="h-4 w-4" />}>
                        Upload
                      </Button>
                    ) : undefined
                  }
                />
              ) : viewMode === "grid" ? (
                <>
                  <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
                    {textDocs.map((doc) => (
                      <Card
                        key={doc.id}
                        hover
                        className={cn("cursor-pointer transition-all", selectedDocIds.has(doc.id) && "ring-2 ring-primary-500")}
                      >
                        <CardContent className="flex flex-col gap-3 p-4" onClick={() => setDetailDocId(doc.id)}>
                          <div className="flex items-start justify-between">
                            <FileTypeIcon type={doc.file_type} size="lg" />
                            <div className="flex items-center gap-1">
                              <StatusDot status={statusColor(doc.status)} />
                              <input
                                type="checkbox" checked={selectedDocIds.has(doc.id)}
                                onChange={(e) => { e.stopPropagation(); handleSelectDoc(doc.id); }}
                                onClick={(e) => e.stopPropagation()}
                                className="h-3.5 w-3.5 rounded border-neutral-300"
                              />
                            </div>
                          </div>
                          <p className="truncate text-sm font-medium text-neutral-900">{doc.name}</p>
                          <div className="flex items-center gap-2 text-xs text-neutral-500">
                            <Badge variant="neutral">{fileTypeLabel(doc.file_type)}</Badge>
                            <span>{formatFileSize(doc.file_size_bytes)}</span>
                          </div>
                          {doc.classification && (
                            <Badge variant="info">{classificationLabel(doc.classification)}</Badge>
                          )}
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                  {totalPages > 1 && (
                    <div className="mt-4 flex items-center justify-between">
                      <span className="text-sm text-neutral-500">Page {page} of {totalPages} ({totalDocs} total)</span>
                      <div className="flex gap-2">
                        <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Previous</Button>
                        <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Next</Button>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <DataTable
                  columns={columns}
                  data={documents}
                  pagination={{ page, limit: 20, total: totalDocs }}
                  onPaginationChange={(newPage) => setPage(newPage)}
                  enableRowSelection
                  onRowSelectionChange={(rows) => setSelectedDocIds(new Set(rows.map((r) => r.id)))}
                  getRowId={(row) => row.id}
                  loading={docsFetching}
                  emptyState={
                    <EmptyState icon={<FileText className="h-8 w-8" />} title="No documents" description="Upload your first document." />
                  }
                />
              )}
            </div>
          </div>
        </section>
      )}

      {/* Detail drawer */}
      <Drawer open={!!detailDocId} onOpenChange={(open) => { if (!open) setDetailDocId(null); }}>
        {detailDocId && (
          <DetailDrawer
            documentId={detailDocId}
            onClose={() => setDetailDocId(null)}
            canEdit={canEdit}
            projects={projects}
          />
        )}
      </Drawer>

      {/* Upload modal */}
      <UploadModal
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        projectId={projectId}
        folderId={selectedFolderId}
      />

      {/* Folder name dialog */}
      <FolderNameDialog
        open={folderDialog.open}
        title={folderDialog.title}
        initialValue={folderDialog.initialValue}
        onSubmit={handleFolderDialogSubmit}
        onClose={() => setFolderDialog((prev) => ({ ...prev, open: false }))}
      />
    </div>
  );
}
