"use client";

import { useState } from "react";
import { AnnotationLayer } from "./annotation-layer";
import { AnnotationSidebar } from "./annotation-sidebar";
import { ViewerToolbar } from "./viewer-toolbar";

interface PdfViewerProps {
  documentId: string;
  /** S3 presigned URL or any URL serving the PDF. */
  documentUrl: string;
  documentName: string;
}

export function PdfViewer({
  documentId,
  documentUrl,
  documentName,
}: PdfViewerProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const [zoom, setZoom] = useState(100);
  const [selectedTool, setSelectedTool] = useState<
    "highlight" | "note" | "bookmark" | null
  >(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="flex h-full min-h-0 overflow-hidden border rounded-lg bg-neutral-100">
      {/* Left: toolbar + iframe */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <ViewerToolbar
          currentPage={currentPage}
          zoom={zoom}
          onZoomChange={setZoom}
          selectedTool={selectedTool}
          onToolChange={setSelectedTool}
          onToggleSidebar={() => setSidebarOpen((v) => !v)}
          documentName={documentName}
        />

        {/* PDF + annotation overlay wrapper */}
        <div className="flex-1 relative overflow-auto bg-neutral-200">
          <div
            style={{
              transformOrigin: "top left",
              transform: `scale(${zoom / 100})`,
              width: zoom !== 100 ? `${(100 / zoom) * 100}%` : "100%",
              height: zoom !== 100 ? `${(100 / zoom) * 100}%` : "100%",
            }}
            className="relative"
          >
            <iframe
              src={documentUrl}
              className="w-full h-full border-0"
              title={documentName}
              style={{ minHeight: "600px" }}
            />
            <AnnotationLayer
              documentId={documentId}
              currentPage={currentPage}
              selectedTool={selectedTool}
              onAnnotationCreated={() => setSelectedTool(null)}
            />
          </div>
        </div>

        {/* Simple page indicator */}
        <div className="flex items-center justify-center gap-3 py-1.5 border-t bg-white text-xs text-neutral-500">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            className="px-2 py-0.5 hover:bg-neutral-100 rounded disabled:opacity-40"
            disabled={currentPage <= 1}
          >
            ←
          </button>
          <span>Page {currentPage}</span>
          <button
            onClick={() => setCurrentPage((p) => p + 1)}
            className="px-2 py-0.5 hover:bg-neutral-100 rounded"
          >
            →
          </button>
        </div>
      </div>

      {/* Right: annotation sidebar */}
      {sidebarOpen && (
        <AnnotationSidebar
          documentId={documentId}
          currentPage={currentPage}
          onPageJump={setCurrentPage}
        />
      )}
    </div>
  );
}
