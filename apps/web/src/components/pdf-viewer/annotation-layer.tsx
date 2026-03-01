"use client";

import { useCreateAnnotation } from "@/lib/document-annotations";

interface AnnotationLayerProps {
  documentId: string;
  currentPage: number;
  selectedTool: "highlight" | "note" | "bookmark" | null;
  onAnnotationCreated: () => void;
}

const TOOL_COLORS: Record<string, string> = {
  highlight: "#FFFF00",
  note: "#3B82F6",
  bookmark: "#10B981",
};

export function AnnotationLayer({
  documentId,
  currentPage,
  selectedTool,
  onAnnotationCreated,
}: AnnotationLayerProps) {
  const createAnnotation = useCreateAnnotation();

  if (!selectedTool) return null;

  return (
    <div
      className="absolute inset-0 cursor-crosshair"
      style={{ zIndex: 10 }}
      onClick={(e) => {
        const rect = e.currentTarget.getBoundingClientRect();
        const x = ((e.clientX - rect.left) / rect.width) * 100;
        const y = ((e.clientY - rect.top) / rect.height) * 100;

        createAnnotation.mutate({
          document_id: documentId,
          annotation_type: selectedTool,
          page_number: currentPage,
          position: { x, y, width: 5, height: 2 },
          color: TOOL_COLORS[selectedTool] ?? "#FFFF00",
        });

        onAnnotationCreated();
      }}
    />
  );
}
