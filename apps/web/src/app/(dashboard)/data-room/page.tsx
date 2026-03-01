"use client";

import React, { useState, useCallback, useMemo } from "react";
import {
  Upload,
  LayoutGrid,
  List,
  Search,
  Filter,
  Trash2,
  FolderInput,
  Download,
  MoreHorizontal,
  FileText,
  Image as ImageIcon,
  Table2,
  File,
  Presentation,
  Share2,
  Brain,
  Eye,
  Pencil,
  X,
  Plus,
  Loader2,
  ChevronDown,
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
import { useQueryClient } from "@tanstack/react-query";

import { useSCRUser, usePermission } from "@/lib/auth";
import {
  useDocuments,
  useDocument,
  useDocumentDownload,
  useDeleteDocument,
  useFolderTree,
  useCreateFolder,
  useUpdateFolder,
  useDeleteFolder,
  useBulkDelete,
  useBulkMove,
  useTriggerExtraction,
  useExtractions,
  dataroomKeys,
  formatFileSize,
  fileTypeLabel,
  classificationLabel,
  statusColor,
  type DocumentResponse,
  type DocumentListParams,
  type FolderTreeNode,
  type DocumentClassification,
  type DocumentStatus,
} from "@/lib/dataroom";
import { useProjects, type ProjectResponse } from "@/lib/projects";
import { FolderTree } from "@/components/dataroom/folder-tree";
import { UploadModal } from "@/components/dataroom/upload-modal";
import { DocumentPreview } from "@/components/dataroom/document-preview";
import { ExtractionPanel } from "@/components/dataroom/extraction-panel";

// ── File icon helper ───────────────────────────────────────────────────────

function FileIcon({
  fileType,
  className,
}: {
  fileType: string;
  className?: string;
}) {
  switch (fileType) {
    case "pdf":
      return <FileText className={cn("text-error-500", className)} />;
    case "jpg":
    case "png":
      return <ImageIcon className={cn("text-primary-500", className)} />;
    case "xlsx":
    case "csv":
      return <Table2 className={cn("text-success-500", className)} />;
    case "pptx":
      return <Presentation className={cn("text-warning-500", className)} />;
    case "docx":
      return <FileText className={cn("text-primary-400", className)} />;
    default:
      return <File className={cn("text-neutral-400", className)} />;
  }
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
      <div className="w-full max-w-sm rounded-lg border border-neutral-200 bg-white p-6 shadow-xl dark:border-neutral-700 dark:bg-neutral-800">
        <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
          {title}
        </h3>
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
          className="mt-3 w-full rounded-md border border-neutral-300 px-3 py-2 text-sm outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 dark:border-neutral-600 dark:bg-neutral-700 dark:text-neutral-100"
        />
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="outline" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button
            size="sm"
            disabled={!name.trim()}
            onClick={() => onSubmit(name.trim())}
          >
            Save
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Document grid card ─────────────────────────────────────────────────────

function DocumentCard({
  doc,
  selected,
  onSelect,
  onClick,
}: {
  doc: DocumentResponse;
  selected: boolean;
  onSelect: (id: string) => void;
  onClick: (id: string) => void;
}) {
  return (
    <Card
      hover
      className={cn(
        "cursor-pointer transition-all",
        selected && "ring-2 ring-primary-500"
      )}
    >
      <CardContent
        className="flex flex-col gap-3 p-4"
        onClick={() => onClick(doc.id)}
      >
        {/* Header row */}
        <div className="flex items-start justify-between">
          <FileIcon fileType={doc.file_type} className="h-8 w-8" />
          <div className="flex items-center gap-1">
            <StatusDot status={statusColor(doc.status)} />
            <input
              type="checkbox"
              checked={selected}
              onChange={(e) => {
                e.stopPropagation();
                onSelect(doc.id);
              }}
              onClick={(e) => e.stopPropagation()}
              className="h-3.5 w-3.5 rounded border-neutral-300"
            />
          </div>
        </div>

        {/* Name */}
        <p className="truncate text-sm font-medium text-neutral-900 dark:text-neutral-100">
          {doc.name}
        </p>

        {/* Meta */}
        <div className="flex items-center gap-2 text-xs text-neutral-500">
          <Badge variant="neutral">{fileTypeLabel(doc.file_type)}</Badge>
          <span>{formatFileSize(doc.file_size_bytes)}</span>
        </div>

        {/* Classification */}
        {doc.classification && (
          <Badge variant="info">
            {classificationLabel(doc.classification)}
          </Badge>
        )}
      </CardContent>
    </Card>
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
            <FileIcon
              fileType={row.original.file_type}
              className="h-4 w-4"
            />
            <span className="truncate font-medium">{row.original.name}</span>
          </div>
        ),
      },
      {
        id: "file_type",
        header: "Type",
        accessorKey: "file_type",
        cell: ({ row }) => (
          <Badge variant="neutral">
            {fileTypeLabel(row.original.file_type)}
          </Badge>
        ),
      },
      {
        id: "status",
        header: "Status",
        accessorKey: "status",
        cell: ({ row }) => (
          <StatusDot
            status={statusColor(row.original.status)}
            label={row.original.status}
          />
        ),
      },
      {
        id: "classification",
        header: "Classification",
        accessorKey: "classification",
        cell: ({ row }) =>
          row.original.classification ? (
            <Badge variant="info">
              {classificationLabel(row.original.classification)}
            </Badge>
          ) : (
            <span className="text-neutral-400">—</span>
          ),
      },
      {
        id: "file_size_bytes",
        header: "Size",
        accessorKey: "file_size_bytes",
        cell: ({ row }) => (
          <span className="text-neutral-500">
            {formatFileSize(row.original.file_size_bytes)}
          </span>
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
}: {
  documentId: string;
  onClose: () => void;
  canEdit: boolean;
}) {
  const { data: doc, isLoading } = useDocument(documentId);
  const download = useDocumentDownload();
  const deleteDoc = useDeleteDocument();
  const triggerExtraction = useTriggerExtraction();
  const { data: extractions, isLoading: extractionsLoading } =
    useExtractions(documentId);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const handleDownload = useCallback(async () => {
    const result = await download.mutateAsync(documentId);
    window.open(result.download_url, "_blank");
  }, [download, documentId]);

  const handlePreview = useCallback(async () => {
    if (previewUrl) return;
    const result = await download.mutateAsync(documentId);
    setPreviewUrl(result.download_url);
  }, [download, documentId, previewUrl]);

  // Auto-fetch preview URL on mount
  React.useEffect(() => {
    if (doc && !previewUrl) {
      download
        .mutateAsync(documentId)
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
            className="rounded-md p-1 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-200"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <Badge variant="neutral">{fileTypeLabel(doc.file_type)}</Badge>
          <StatusDot
            status={statusColor(doc.status)}
            label={doc.status}
          />
          {doc.classification && (
            <Badge variant="info">
              {classificationLabel(doc.classification)}
            </Badge>
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
              <DocumentPreview
                url={previewUrl}
                fileType={doc.file_type}
                fileName={doc.name}
              />
            </div>
          </TabsContent>

          <TabsContent value="extractions" className="mt-3">
            <ExtractionPanel
              extractions={extractions ?? doc.extractions}
              loading={extractionsLoading}
              onReExtract={
                canEdit
                  ? (types) =>
                      triggerExtraction.mutate({
                        documentId,
                        extraction_types: types,
                      })
                  : undefined
              }
              reExtracting={triggerExtraction.isPending}
            />
          </TabsContent>

          <TabsContent value="details" className="mt-3">
            <div className="space-y-4">
              <DetailRow label="File type" value={doc.file_type.toUpperCase()} />
              <DetailRow label="MIME type" value={doc.mime_type} />
              <DetailRow
                label="Size"
                value={formatFileSize(doc.file_size_bytes)}
              />
              <DetailRow label="Version" value={`v${doc.version}`} />
              <DetailRow
                label="Uploaded"
                value={new Date(doc.created_at).toLocaleString()}
              />
              <DetailRow
                label="Updated"
                value={new Date(doc.updated_at).toLocaleString()}
              />
              <DetailRow
                label="Watermark"
                value={doc.watermark_enabled ? "Enabled" : "Disabled"}
              />
              <DetailRow
                label="Checksum"
                value={doc.checksum_sha256.slice(0, 16) + "..."}
              />
              {doc.version_count > 1 && (
                <DetailRow
                  label="Versions"
                  value={`${doc.version_count} versions`}
                />
              )}
            </div>
          </TabsContent>
        </Tabs>
      </DrawerBody>

      <DrawerFooter>
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

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-neutral-500">{label}</span>
      <span className="font-medium text-neutral-900 dark:text-neutral-100">
        {value}
      </span>
    </div>
  );
}

// ── Skeleton loading ───────────────────────────────────────────────────────

function GridSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-4">
      {Array.from({ length: 8 }).map((_, i) => (
        <div
          key={i}
          className="h-40 animate-pulse rounded-lg border border-neutral-200 bg-neutral-100 dark:border-neutral-700 dark:bg-neutral-800"
        />
      ))}
    </div>
  );
}

function FolderTreeSkeleton() {
  return (
    <div className="space-y-2 p-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="h-6 animate-pulse rounded bg-neutral-100 dark:bg-neutral-800"
          style={{ width: `${70 + Math.random() * 30}%` }}
        />
      ))}
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────

export default function DataRoomPage() {
  const { user } = useSCRUser();
  const canUpload = usePermission("upload", "document");
  const canEdit = usePermission("edit", "document");
  const canDelete = usePermission("delete", "document");

  // ── State ──────────────────────────────────────────────────────────────
  const [projectId, setProjectId] = useState<string>("");
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(
    null
  );
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [search, setSearch] = useState("");
  const [selectedDocIds, setSelectedDocIds] = useState<Set<string>>(
    new Set()
  );
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
  const [sortBy, setSortBy] = useState("created_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [statusFilter, setStatusFilter] = useState<DocumentStatus | undefined>();

  // ── Projects (for selector) ────────────────────────────────────────────
  const { data: projectList } = useProjects({ page_size: 100 });
  const projects: ProjectResponse[] = projectList?.items ?? [];
  const activeProject = projects.find((p) => p.id === projectId);

  // ── Queries ────────────────────────────────────────────────────────────
  const params: DocumentListParams = {
    project_id: projectId || undefined,
    folder_id: selectedFolderId,
    search: search || undefined,
    page,
    page_size: 20,
    sort_by: sortBy,
    sort_order: sortOrder,
    status: statusFilter,
  };

  const {
    data: docList,
    isLoading: docsLoading,
    isFetching: docsFetching,
  } = useDocuments(params);

  const {
    data: folders,
    isLoading: foldersLoading,
  } = useFolderTree(projectId || undefined);

  // ── Mutations ──────────────────────────────────────────────────────────
  const createFolder = useCreateFolder();
  const updateFolder = useUpdateFolder();
  const deleteFolder = useDeleteFolder();
  const bulkDelete = useBulkDelete();
  const bulkMove = useBulkMove();
  const columns = useTableColumns();
  const qc = useQueryClient();

  // ── Handlers ───────────────────────────────────────────────────────────
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
    await bulkDelete.mutateAsync({
      document_ids: Array.from(selectedDocIds),
    });
    setSelectedDocIds(new Set());
  }, [selectedDocIds, bulkDelete]);

  const handleCreateFolder = useCallback(
    (parentId: string | null) => {
      setFolderDialog({
        open: true,
        title: "New Folder",
        initialValue: "",
        parentId,
      });
    },
    []
  );

  const handleRenameFolder = useCallback(
    (folder: FolderTreeNode) => {
      setFolderDialog({
        open: true,
        title: "Rename Folder",
        initialValue: folder.name,
        parentId: folder.parent_folder_id,
        folderId: folder.id,
      });
    },
    []
  );

  const handleFolderDialogSubmit = useCallback(
    async (name: string) => {
      if (folderDialog.folderId) {
        await updateFolder.mutateAsync({
          folderId: folderDialog.folderId,
          name,
        });
      } else {
        await createFolder.mutateAsync({
          name,
          project_id: projectId,
          parent_folder_id: folderDialog.parentId,
        });
      }
      setFolderDialog((prev) => ({ ...prev, open: false }));
    },
    [folderDialog, createFolder, updateFolder, projectId]
  );

  const handleDeleteFolder = useCallback(
    async (folderId: string) => {
      await deleteFolder.mutateAsync(folderId);
    },
    [deleteFolder]
  );

  const documents = docList?.items ?? [];
  const totalDocs = docList?.total ?? 0;
  const totalPages = docList?.total_pages ?? 0;

  // ── No project selected state ──────────────────────────────────────────
  if (!projectId) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
            Data Room
          </h1>
          <p className="mt-1 text-sm text-neutral-500">
            Manage and organize your project documents.
          </p>
        </div>

        <EmptyState
          icon={<FileText className="h-8 w-8" />}
          title="Select a project"
          description="Choose a project to view its documents and folders."
          action={
            <select
              className="border border-neutral-300 rounded-lg px-3 py-2 text-sm bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 min-w-[260px]"
              value=""
              onChange={(e) => e.target.value && setProjectId(e.target.value)}
            >
              <option value="">— Select a project —</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          }
        />
      </div>
    );
  }

  // ── Main layout ────────────────────────────────────────────────────────
  return (
    <div className="space-y-4">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
            Data Room
          </h1>
          <p className="mt-1 text-sm text-neutral-500">
            {totalDocs} document{totalDocs !== 1 ? "s" : ""}
            {selectedFolderId ? " in folder" : " total"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            className="border border-neutral-300 rounded-lg px-3 py-1.5 text-sm bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            value={projectId}
            onChange={(e) => { setProjectId(e.target.value); setSelectedFolderId(null); setPage(1); }}
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          {canUpload && (
            <Button
              onClick={() => setUploadOpen(true)}
              iconLeft={<Upload className="h-4 w-4" />}
            >
              Upload
            </Button>
          )}
        </div>
      </div>

      {/* 3-panel layout */}
      <div className="flex gap-4" style={{ minHeight: "calc(100vh - 200px)" }}>
        {/* Left: folder tree */}
        <div className="w-[250px] shrink-0 overflow-hidden rounded-lg border border-neutral-200 bg-white dark:border-neutral-700 dark:bg-neutral-800">
          {foldersLoading ? (
            <FolderTreeSkeleton />
          ) : (
            <FolderTree
              folders={folders ?? []}
              selectedFolderId={selectedFolderId}
              onSelectFolder={(id) => {
                setSelectedFolderId(id);
                setPage(1);
              }}
              onCreateFolder={handleCreateFolder}
              onRenameFolder={handleRenameFolder}
              onDeleteFolder={handleDeleteFolder}
              canEdit={canEdit}
            />
          )}
        </div>

        {/* Center: documents */}
        <div className="min-w-0 flex-1">
          {/* Toolbar */}
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <SearchInput
              value={search}
              onValueChange={(v) => {
                setSearch(v);
                setPage(1);
              }}
              placeholder="Search documents..."
              shortcutHint=""
              className="w-64"
            />

            {/* Status filter */}
            <select
              value={statusFilter ?? ""}
              onChange={(e) => {
                setStatusFilter(
                  (e.target.value as DocumentStatus) || undefined
                );
                setPage(1);
              }}
              className="rounded-md border border-neutral-300 bg-white px-3 py-1.5 text-sm text-neutral-700 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-300"
            >
              <option value="">All statuses</option>
              <option value="ready">Ready</option>
              <option value="processing">Processing</option>
              <option value="uploading">Uploading</option>
              <option value="error">Error</option>
            </select>

            <div className="flex-1" />

            {/* Bulk actions */}
            {selectedDocIds.size > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-neutral-500">
                  {selectedDocIds.size} selected
                </span>
                {canDelete && (
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={handleBulkDelete}
                    loading={bulkDelete.isPending}
                    iconLeft={<Trash2 className="h-3.5 w-3.5" />}
                  >
                    Delete
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedDocIds(new Set())}
                >
                  Clear
                </Button>
              </div>
            )}

            {/* View toggle */}
            <div className="flex rounded-md border border-neutral-200 dark:border-neutral-700">
              <button
                onClick={() => setViewMode("grid")}
                className={cn(
                  "rounded-l-md p-1.5 transition-colors",
                  viewMode === "grid"
                    ? "bg-primary-50 text-primary-600 dark:bg-primary-950 dark:text-primary-400"
                    : "text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
                )}
              >
                <LayoutGrid className="h-4 w-4" />
              </button>
              <button
                onClick={() => setViewMode("list")}
                className={cn(
                  "rounded-r-md p-1.5 transition-colors",
                  viewMode === "list"
                    ? "bg-primary-50 text-primary-600 dark:bg-primary-950 dark:text-primary-400"
                    : "text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
                )}
              >
                <List className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Loading */}
          {docsLoading ? (
            <GridSkeleton />
          ) : documents.length === 0 ? (
            /* Empty state */
            <EmptyState
              icon={<FileText className="h-8 w-8" />}
              title="No documents found"
              description={
                search
                  ? `No documents match "${search}".`
                  : "Upload your first document to get started."
              }
              action={
                canUpload ? (
                  <Button
                    onClick={() => setUploadOpen(true)}
                    iconLeft={<Upload className="h-4 w-4" />}
                  >
                    Upload
                  </Button>
                ) : undefined
              }
            />
          ) : viewMode === "grid" ? (
            /* Grid view */
            <>
              <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-4">
                {documents.map((doc) => (
                  <DocumentCard
                    key={doc.id}
                    doc={doc}
                    selected={selectedDocIds.has(doc.id)}
                    onSelect={handleSelectDoc}
                    onClick={setDetailDocId}
                  />
                ))}
              </div>
              {/* Pagination */}
              {totalPages > 1 && (
                <div className="mt-4 flex items-center justify-between">
                  <span className="text-sm text-neutral-500">
                    Page {page} of {totalPages} ({totalDocs} total)
                  </span>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page <= 1}
                      onClick={() => setPage((p) => p - 1)}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page >= totalPages}
                      onClick={() => setPage((p) => p + 1)}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </>
          ) : (
            /* List (table) view */
            <DataTable
              columns={columns}
              data={documents}
              pagination={{
                page,
                limit: 20,
                total: totalDocs,
              }}
              onPaginationChange={(newPage) => setPage(newPage)}
              enableRowSelection
              onRowSelectionChange={(rows) =>
                setSelectedDocIds(new Set(rows.map((r) => r.id)))
              }
              getRowId={(row) => row.id}
              loading={docsFetching}
              emptyState={
                <EmptyState
                  icon={<FileText className="h-8 w-8" />}
                  title="No documents"
                  description="Upload your first document."
                />
              }
            />
          )}
        </div>
      </div>

      {/* Detail drawer */}
      <Drawer
        open={!!detailDocId}
        onOpenChange={(open) => {
          if (!open) setDetailDocId(null);
        }}
      >
        {detailDocId && (
          <DetailDrawer
            documentId={detailDocId}
            onClose={() => setDetailDocId(null)}
            canEdit={canEdit}
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
