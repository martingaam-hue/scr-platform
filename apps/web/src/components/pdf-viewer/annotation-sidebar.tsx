"use client";

import { Badge } from "@scr/ui";
import {
  useAnnotations,
  useDeleteAnnotation,
  type Annotation,
} from "@/lib/document-annotations";

interface AnnotationSidebarProps {
  documentId: string;
  currentPage: number;
  onPageJump: (page: number) => void;
}

interface AnnotationCardProps {
  annotation: Annotation;
  onPageJump: (page: number) => void;
}

const TYPE_STYLES: Record<string, string> = {
  highlight: "bg-yellow-50 border-yellow-300",
  note: "bg-blue-50 border-blue-200",
  bookmark: "bg-green-50 border-green-200",
  question_link: "bg-purple-50 border-purple-200",
};

function AnnotationCard({ annotation, onPageJump }: AnnotationCardProps) {
  const deleteAnnotation = useDeleteAnnotation();
  const containerClass =
    TYPE_STYLES[annotation.annotation_type] ?? "bg-neutral-50 border-neutral-200";

  return (
    <div className={`rounded border p-2 mb-1 text-sm ${containerClass}`}>
      <div className="flex justify-between items-start gap-1">
        <Badge variant="neutral" className="text-[10px] capitalize shrink-0">
          {annotation.annotation_type.replace("_", " ")}
        </Badge>
        <button
          onClick={() =>
            deleteAnnotation.mutate({
              annotationId: annotation.id,
              document_id: annotation.document_id,
            })
          }
          disabled={deleteAnnotation.isPending}
          className="text-neutral-400 hover:text-red-500 text-xs leading-none ml-auto"
          title="Delete annotation"
        >
          ✕
        </button>
      </div>

      {annotation.content && (
        <p className="mt-1 text-neutral-700 text-xs leading-snug break-words">
          {annotation.content}
        </p>
      )}

      <button
        onClick={() => onPageJump(annotation.page_number)}
        className="text-xs text-primary-600 mt-1 hover:underline block"
      >
        Go to page {annotation.page_number}
      </button>

      {annotation.linked_qa_question_id && (
        <p className="text-xs text-purple-600 mt-1">Linked to Q&amp;A</p>
      )}
    </div>
  );
}

export function AnnotationSidebar({
  documentId,
  currentPage: _currentPage,
  onPageJump,
}: AnnotationSidebarProps) {
  const { data: annotations = [], isLoading } = useAnnotations(documentId);

  // Group by page number
  const grouped = annotations.reduce<Record<number, Annotation[]>>(
    (acc, ann) => {
      const pg = ann.page_number;
      if (!acc[pg]) acc[pg] = [];
      acc[pg].push(ann);
      return acc;
    },
    {}
  );

  const sortedPages = Object.keys(grouped)
    .map(Number)
    .sort((a, b) => a - b);

  return (
    <div className="w-72 border-l flex flex-col bg-white flex-shrink-0">
      <div className="p-3 border-b font-medium text-sm text-neutral-800 flex items-center justify-between">
        <span>Annotations</span>
        <span className="text-xs text-neutral-500 font-normal">
          {annotations.length}
        </span>
      </div>

      <div className="flex-1 overflow-auto p-2 space-y-3">
        {isLoading && (
          <div className="flex justify-center mt-8">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
          </div>
        )}

        {!isLoading && annotations.length === 0 && (
          <p className="text-sm text-neutral-400 text-center mt-8 px-2">
            No annotations yet. Select a tool and click on the document to add
            one.
          </p>
        )}

        {sortedPages.map((page) => (
          <div key={page}>
            <p className="text-xs text-neutral-500 mb-1 font-medium">
              Page {page}
            </p>
            {grouped[page].map((ann) => (
              <AnnotationCard
                key={ann.id}
                annotation={ann}
                onPageJump={onPageJump}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
