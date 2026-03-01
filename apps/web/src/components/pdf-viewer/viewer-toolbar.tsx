"use client";

import {
  Bookmark,
  Highlighter,
  MessageSquare,
  PanelRight,
  ZoomIn,
  ZoomOut,
} from "lucide-react";

interface ViewerToolbarProps {
  currentPage: number;
  zoom: number;
  onZoomChange: (zoom: number) => void;
  selectedTool: "highlight" | "note" | "bookmark" | null;
  onToolChange: (tool: "highlight" | "note" | "bookmark" | null) => void;
  onToggleSidebar: () => void;
  documentName: string;
}

const TOOLS: Array<{
  id: "highlight" | "note" | "bookmark";
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  icon: any;
  label: string;
}> = [
  { id: "highlight", icon: Highlighter, label: "Highlight" },
  { id: "note", icon: MessageSquare, label: "Note" },
  { id: "bookmark", icon: Bookmark, label: "Bookmark" },
];

export function ViewerToolbar({
  zoom,
  onZoomChange,
  selectedTool,
  onToolChange,
  onToggleSidebar,
  documentName,
}: ViewerToolbarProps) {
  return (
    <div className="flex items-center gap-2 p-2 border-b bg-white text-sm flex-shrink-0">
      {/* Document name */}
      <span
        className="font-medium truncate flex-1 max-w-xs text-neutral-700"
        title={documentName}
      >
        {documentName}
      </span>

      {/* Annotation tools */}
      <div className="flex gap-1">
        {TOOLS.map((t) => {
          const Icon = t.icon;
          const active = selectedTool === t.id;
          return (
            <button
              key={t.id}
              onClick={() => onToolChange(active ? null : t.id)}
              className={`p-1.5 rounded transition-colors ${
                active
                  ? "bg-primary-100 text-primary-600"
                  : "hover:bg-neutral-100 text-neutral-600"
              }`}
              title={t.label}
            >
              <Icon className="w-4 h-4" />
            </button>
          );
        })}
      </div>

      {/* Zoom controls */}
      <div className="flex items-center gap-1 border rounded px-1">
        <button
          onClick={() => onZoomChange(Math.max(50, zoom - 10))}
          className="p-1 hover:bg-neutral-100 rounded"
          title="Zoom out"
        >
          <ZoomOut className="w-3 h-3" />
        </button>
        <span className="text-xs w-10 text-center text-neutral-600">
          {zoom}%
        </span>
        <button
          onClick={() => onZoomChange(Math.min(200, zoom + 10))}
          className="p-1 hover:bg-neutral-100 rounded"
          title="Zoom in"
        >
          <ZoomIn className="w-3 h-3" />
        </button>
      </div>

      {/* Toggle sidebar */}
      <button
        onClick={onToggleSidebar}
        className="p-1.5 hover:bg-neutral-100 rounded text-neutral-600"
        title="Toggle annotations panel"
      >
        <PanelRight className="w-4 h-4" />
      </button>
    </div>
  );
}
