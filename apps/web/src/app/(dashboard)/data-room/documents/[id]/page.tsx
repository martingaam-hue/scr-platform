"use client";

import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Clock,
  Download,
  FileText,
  GitBranch,
  HardDrive,
  Shield,
  Upload,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
} from "@scr/ui";
import {
  useDocument,
  useDocumentVersions,
  type DocumentVersionResponse,
} from "@/lib/dataroom";

// ── Helpers ────────────────────────────────────────────────────────────────

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function VersionRow({ version }: { version: DocumentVersionResponse }) {
  const isLatest = version.version === 1;
  return (
    <div className="flex items-center gap-4 py-3 border-b last:border-0 hover:bg-neutral-50 px-4 -mx-4">
      <div className="h-9 w-9 rounded-lg bg-primary-50 flex items-center justify-center flex-shrink-0">
        <GitBranch className="h-4 w-4 text-primary-600" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-neutral-900 truncate">
            Version {version.version}
          </p>
          {isLatest && (
            <Badge variant="success" className="text-[10px]">
              Latest
            </Badge>
          )}
        </div>
        <p className="text-xs text-neutral-500 truncate">{version.name}</p>
      </div>
      <div className="flex items-center gap-6 text-xs text-neutral-500 flex-shrink-0">
        <span className="flex items-center gap-1">
          <HardDrive className="h-3 w-3" />
          {formatBytes(version.file_size_bytes)}
        </span>
        <span className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          {new Date(version.created_at).toLocaleDateString(undefined, {
            year: "numeric",
            month: "short",
            day: "numeric",
          })}
        </span>
        <span className="flex items-center gap-1 font-mono text-[10px]">
          <Shield className="h-3 w-3" />
          {version.checksum_sha256.slice(0, 8)}...
        </span>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function DocumentVersionsPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const { data: doc, isLoading: docLoading } = useDocument(id);
  const { data: versions, isLoading: versionsLoading } =
    useDocumentVersions(id);

  const isLoading = docLoading || versionsLoading;

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <button
          onClick={() => router.back()}
          className="mb-4 flex items-center gap-1 text-sm text-neutral-500 hover:text-neutral-700"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Data Room
        </button>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-100 rounded-lg">
              <FileText className="h-6 w-6 text-primary-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-neutral-900">
                {doc?.name ?? "Document"}
              </h1>
              <p className="text-sm text-neutral-500 mt-0.5">
                Version history — {versions?.length ?? 0} version
                {versions?.length !== 1 ? "s" : ""}
              </p>
            </div>
          </div>
          <Button variant="outline">
            <Upload className="mr-2 h-4 w-4" />
            Upload New Version
          </Button>
        </div>
      </div>

      {/* Current version summary */}
      {doc && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-5">
              <p className="text-xs text-neutral-500">Current Version</p>
              <p className="text-2xl font-bold text-neutral-800">
                v{doc.version}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <p className="text-xs text-neutral-500">File Size</p>
              <p className="text-2xl font-bold text-neutral-800">
                {formatBytes(doc.file_size_bytes)}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <p className="text-xs text-neutral-500">File Type</p>
              <p className="text-2xl font-bold text-neutral-800 uppercase">
                {doc.file_type}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <p className="text-xs text-neutral-500">Status</p>
              <div className="mt-1">
                <Badge
                  variant={
                    doc.status === "ready"
                      ? "success"
                      : doc.status === "error"
                      ? "error"
                      : "neutral"
                  }
                >
                  {doc.status}
                </Badge>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Version list */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">Version History</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          {!versions || versions.length === 0 ? (
            <EmptyState
              icon={<GitBranch className="h-10 w-10 text-neutral-400" />}
              title="No versions"
              description="Upload a new version to create a version history."
            />
          ) : (
            <div>
              {versions.map((v) => (
                <VersionRow key={v.id} version={v} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Checksum verification note */}
      {versions && versions.length > 0 && (
        <Card>
          <CardContent className="p-5">
            <div className="flex items-start gap-3">
              <Shield className="h-5 w-5 text-primary-600 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-semibold text-neutral-800">
                  Integrity Verification
                </p>
                <p className="text-xs text-neutral-500 mt-1">
                  Each version is stored with a SHA-256 checksum for tamper
                  detection. The checksum is verified on every download.
                </p>
                <p className="text-xs font-mono text-neutral-600 mt-2 bg-neutral-50 px-2 py-1 rounded">
                  Current: {versions[0]?.checksum_sha256}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
