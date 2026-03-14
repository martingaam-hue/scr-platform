import * as React from "react";
import {
  FileText,
  FileSpreadsheet,
  FileImage,
  FileAudio,
  FileVideo,
  File,
  type LucideProps,
} from "lucide-react";
import { cn } from "../lib/utils";

type ExtConfig = { bg: string; color: string; Icon: React.ElementType<LucideProps> };

const EXT_CONFIG: Record<string, ExtConfig> = {
  pdf: { bg: "bg-red-50", color: "text-red-600", Icon: FileText },
  doc: { bg: "bg-blue-50", color: "text-blue-600", Icon: FileText },
  docx: { bg: "bg-blue-50", color: "text-blue-600", Icon: FileText },
  xls: { bg: "bg-green-50", color: "text-green-600", Icon: FileSpreadsheet },
  xlsx: { bg: "bg-green-50", color: "text-green-600", Icon: FileSpreadsheet },
  csv: { bg: "bg-emerald-50", color: "text-emerald-600", Icon: FileSpreadsheet },
  ppt: { bg: "bg-orange-50", color: "text-orange-600", Icon: FileText },
  pptx: { bg: "bg-orange-50", color: "text-orange-600", Icon: FileText },
  png: { bg: "bg-purple-50", color: "text-purple-600", Icon: FileImage },
  jpg: { bg: "bg-purple-50", color: "text-purple-600", Icon: FileImage },
  jpeg: { bg: "bg-purple-50", color: "text-purple-600", Icon: FileImage },
  gif: { bg: "bg-purple-50", color: "text-purple-600", Icon: FileImage },
  svg: { bg: "bg-indigo-50", color: "text-indigo-600", Icon: FileImage },
  mp3: { bg: "bg-amber-50", color: "text-amber-600", Icon: FileAudio },
  wav: { bg: "bg-amber-50", color: "text-amber-600", Icon: FileAudio },
  mp4: { bg: "bg-amber-50", color: "text-amber-600", Icon: FileVideo },
  mov: { bg: "bg-amber-50", color: "text-amber-600", Icon: FileVideo },
  txt: { bg: "bg-neutral-50", color: "text-neutral-600", Icon: FileText },
  md: { bg: "bg-neutral-50", color: "text-neutral-600", Icon: FileText },
  json: { bg: "bg-yellow-50", color: "text-yellow-600", Icon: FileText },
  zip: { bg: "bg-neutral-50", color: "text-neutral-600", Icon: File },
};

const FALLBACK: ExtConfig = { bg: "bg-neutral-50", color: "text-neutral-600", Icon: File };

export interface FileTypeIconProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Filename or just extension (e.g. "report.pdf" or "pdf") */
  fileName: string;
  size?: "sm" | "md" | "lg";
}

function FileTypeIcon({ fileName, size = "md", className, ...props }: FileTypeIconProps) {
  const ext = fileName.split(".").pop()?.toLowerCase() ?? "";
  const { bg, color, Icon } = EXT_CONFIG[ext] ?? FALLBACK;
  const sizes = {
    sm: { wrap: "h-7 w-7", icon: "h-3.5 w-3.5" },
    md: { wrap: "h-9 w-9", icon: "h-4 w-4" },
    lg: { wrap: "h-12 w-12", icon: "h-6 w-6" },
  };
  return (
    <div
      className={cn("flex items-center justify-center rounded-md", bg, sizes[size].wrap, className)}
      {...props}
    >
      <Icon className={cn(color, sizes[size].icon)} />
    </div>
  );
}

export { FileTypeIcon };
