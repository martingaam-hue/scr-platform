"use client";

import React, { useState } from "react";
import {
  FileText,
  Image as ImageIcon,
  Table2,
  File,
  Download,
  ZoomIn,
  ZoomOut,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { Button, cn } from "@scr/ui";

// ── Types ──────────────────────────────────────────────────────────────────

interface DocumentPreviewProps {
  /** Pre-signed download URL for the file */
  url: string | null;
  /** File extension (pdf, jpg, png, xlsx, etc.) */
  fileType: string;
  /** Original file name */
  fileName: string;
  /** Whether download is allowed (e.g., for shared links) */
  allowDownload?: boolean;
  className?: string;
}

// ── Preview by type ────────────────────────────────────────────────────────

function PDFPreview({ url }: { url: string }) {
  return (
    <iframe
      src={`${url}#toolbar=0`}
      title="PDF preview"
      className="h-full w-full rounded-md border border-neutral-200 dark:border-neutral-700"
    />
  );
}

function ImagePreview({ url, fileName }: { url: string; fileName: string }) {
  const [zoom, setZoom] = useState(1);

  return (
    <div className="relative flex h-full flex-col">
      {/* Zoom controls */}
      <div className="absolute right-2 top-2 z-10 flex gap-1 rounded-md border border-neutral-200 bg-white/90 p-0.5 shadow-sm dark:border-neutral-700 dark:bg-neutral-800/90">
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={() => setZoom((z) => Math.max(0.25, z - 0.25))}
        >
          <ZoomOut className="h-3.5 w-3.5" />
        </Button>
        <span className="flex items-center px-1 text-xs text-neutral-500">
          {Math.round(zoom * 100)}%
        </span>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={() => setZoom((z) => Math.min(4, z + 0.25))}
        >
          <ZoomIn className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Image */}
      <div className="flex-1 overflow-auto rounded-md border border-neutral-200 bg-neutral-100 dark:border-neutral-700 dark:bg-neutral-900">
        <div className="flex min-h-full items-center justify-center p-4">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={url}
            alt={fileName}
            className="max-w-full transition-transform duration-200"
            style={{ transform: `scale(${zoom})` }}
          />
        </div>
      </div>
    </div>
  );
}

function SpreadsheetPreview({ fileName }: { fileName: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 rounded-md border border-neutral-200 bg-neutral-50 dark:border-neutral-700 dark:bg-neutral-900">
      <Table2 className="h-12 w-12 text-success-500" />
      <p className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
        {fileName}
      </p>
      <p className="text-xs text-neutral-500">
        Spreadsheet preview requires download
      </p>
    </div>
  );
}

function GenericPreview({
  fileType,
  fileName,
}: {
  fileType: string;
  fileName: string;
}) {
  const Icon = getFileIcon(fileType);
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 rounded-md border border-neutral-200 bg-neutral-50 dark:border-neutral-700 dark:bg-neutral-900">
      <Icon className="h-12 w-12 text-neutral-400" />
      <p className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
        {fileName}
      </p>
      <p className="text-xs text-neutral-500">
        Preview not available for .{fileType} files
      </p>
    </div>
  );
}

// ── Helpers ────────────────────────────────────────────────────────────────

function getFileIcon(fileType: string) {
  switch (fileType) {
    case "pdf":
      return FileText;
    case "jpg":
    case "png":
      return ImageIcon;
    case "xlsx":
    case "csv":
      return Table2;
    default:
      return File;
  }
}

// ── Main component ─────────────────────────────────────────────────────────

export function DocumentPreview({
  url,
  fileType,
  fileName,
  allowDownload = true,
  className,
}: DocumentPreviewProps) {
  if (!url) {
    return (
      <div
        className={cn(
          "flex h-full items-center justify-center",
          className
        )}
      >
        <div className="flex flex-col items-center gap-2 text-neutral-400">
          <Loader2 className="h-8 w-8 animate-spin" />
          <span className="text-sm">Loading preview...</span>
        </div>
      </div>
    );
  }

  const renderPreview = () => {
    switch (fileType) {
      case "pdf":
        return <PDFPreview url={url} />;
      case "jpg":
      case "png":
        return <ImagePreview url={url} fileName={fileName} />;
      case "xlsx":
      case "csv":
        return <SpreadsheetPreview fileName={fileName} />;
      default:
        return <GenericPreview fileType={fileType} fileName={fileName} />;
    }
  };

  return (
    <div className={cn("flex h-full flex-col gap-2", className)}>
      {renderPreview()}
      {allowDownload && (
        <div className="flex justify-end">
          <Button
            variant="outline"
            size="sm"
            iconLeft={<Download className="h-3.5 w-3.5" />}
            onClick={() => window.open(url, "_blank")}
          >
            Download
          </Button>
        </div>
      )}
    </div>
  );
}

export { getFileIcon };
