"use client";

import { useState } from "react";
import { FileText, FileSpreadsheet, Presentation, Loader2 } from "lucide-react";
import {
  Button,
  Modal,
  ModalContent,
  ModalHeader,
  ModalTitle,
  ModalDescription,
  ModalFooter,
  cn,
} from "@scr/ui";
import {
  useGenerateReport,
  type ReportTemplateResponse,
  type OutputFormat,
} from "@/lib/reports";

interface GenerateDialogProps {
  template: ReportTemplateResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const FORMAT_OPTIONS: {
  value: OutputFormat;
  label: string;
  icon: React.ElementType;
}[] = [
  { value: "pdf", label: "PDF", icon: FileText },
  { value: "xlsx", label: "Excel", icon: FileSpreadsheet },
  { value: "pptx", label: "PowerPoint", icon: Presentation },
];

export function GenerateDialog({
  template,
  open,
  onOpenChange,
}: GenerateDialogProps) {
  const [format, setFormat] = useState<OutputFormat>(
    (template.template_config?.default_format as OutputFormat) ?? "pdf"
  );
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const generateMutation = useGenerateReport();

  const supportedFormats = (template.template_config?.supported_formats as string[]) ?? [
    "pdf",
    "xlsx",
    "pptx",
  ];

  function handleGenerate() {
    const parameters: Record<string, unknown> = {};
    if (dateFrom) parameters.date_from = dateFrom;
    if (dateTo) parameters.date_to = dateTo;

    generateMutation.mutate(
      {
        template_id: template.id,
        parameters,
        output_format: format,
      },
      {
        onSuccess: () => {
          onOpenChange(false);
          setDateFrom("");
          setDateTo("");
        },
      }
    );
  }

  return (
    <Modal open={open} onOpenChange={onOpenChange}>
      <ModalContent>
        <ModalHeader>
          <ModalTitle>Generate Report</ModalTitle>
          <ModalDescription>{template.name}</ModalDescription>
        </ModalHeader>

        <div className="space-y-4">
          {/* Format selector */}
          <div>
            <label className="mb-2 block text-sm font-medium text-neutral-700">
              Output Format
            </label>
            <div className="flex gap-2">
              {FORMAT_OPTIONS.filter((f) =>
                supportedFormats.includes(f.value)
              ).map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setFormat(opt.value)}
                  className={cn(
                    "flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors",
                    format === opt.value
                      ? "border-primary-500 bg-primary-50 text-primary-700"
                      : "border-neutral-200 text-neutral-600 hover:border-neutral-300 hover:bg-neutral-50"
                  )}
                >
                  <opt.icon className="h-4 w-4" />
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Date range */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-neutral-700">
                From
              </label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-neutral-700">
                To
              </label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              />
            </div>
          </div>

          {/* Error state */}
          {generateMutation.isError && (
            <p className="text-sm text-red-600">
              Failed to generate report. Please try again.
            </p>
          )}
        </div>

        <ModalFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={generateMutation.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={handleGenerate}
            disabled={generateMutation.isPending}
          >
            {generateMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Generating...
              </>
            ) : (
              "Generate Report"
            )}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}
