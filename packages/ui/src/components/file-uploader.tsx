"use client";

import * as React from "react";
import { Upload, X, File, CheckCircle } from "lucide-react";
import { cn } from "../lib/utils";

export interface FileItem {
  file: File;
  progress: number;
  status: "pending" | "uploading" | "done" | "error";
  error?: string;
}

export interface FileUploaderProps extends React.HTMLAttributes<HTMLDivElement> {
  accept?: string;
  multiple?: boolean;
  maxSizeMB?: number;
  onFilesSelected?: (files: File[]) => void;
  files?: FileItem[];
  onRemove?: (index: number) => void;
  disabled?: boolean;
}

function FileUploader({
  accept,
  multiple = true,
  maxSizeMB = 50,
  onFilesSelected,
  files = [],
  onRemove,
  disabled = false,
  className,
  ...props
}: FileUploaderProps) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = React.useState(false);

  const handleFiles = (fileList: FileList | null) => {
    if (!fileList) return;
    const valid = Array.from(fileList).filter(
      (f) => f.size <= maxSizeMB * 1024 * 1024
    );
    if (valid.length > 0) onFilesSelected?.(valid);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (!disabled) handleFiles(e.dataTransfer.files);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) setDragOver(true);
  };

  return (
    <div className={cn("space-y-3", className)} {...props}>
      {/* Drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={() => setDragOver(false)}
        onClick={() => !disabled && inputRef.current?.click()}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-10 transition-colors",
          dragOver
            ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20"
            : "border-neutral-300 bg-neutral-50 hover:border-neutral-400 dark:border-neutral-700 dark:bg-neutral-800/50 dark:hover:border-neutral-600",
          disabled && "pointer-events-none opacity-50"
        )}
      >
        <Upload className="mb-3 h-8 w-8 text-neutral-400" />
        <p className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
          Drop files here or click to browse
        </p>
        <p className="mt-1 text-xs text-neutral-400">
          {accept ? `Accepted: ${accept}` : "All file types"} | Max{" "}
          {maxSizeMB}MB
        </p>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />

      {/* File list */}
      {files.length > 0 && (
        <ul className="space-y-2">
          {files.map((item, i) => (
            <li
              key={i}
              className="flex items-center gap-3 rounded-md border border-neutral-200 bg-white px-3 py-2 dark:border-neutral-700 dark:bg-neutral-800"
            >
              {item.status === "done" ? (
                <CheckCircle className="h-4 w-4 shrink-0 text-success-500" />
              ) : (
                <File className="h-4 w-4 shrink-0 text-neutral-400" />
              )}
              <div className="flex-1 min-w-0">
                <p className="truncate text-sm text-neutral-900 dark:text-neutral-100">
                  {item.file.name}
                </p>
                {item.status === "uploading" && (
                  <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-neutral-200 dark:bg-neutral-700">
                    <div
                      className="h-full rounded-full bg-primary-500 transition-all"
                      style={{ width: `${item.progress}%` }}
                    />
                  </div>
                )}
                {item.error && (
                  <p className="text-xs text-error-500">{item.error}</p>
                )}
              </div>
              <span className="shrink-0 text-xs text-neutral-400">
                {(item.file.size / 1024 / 1024).toFixed(1)} MB
              </span>
              {onRemove && (
                <button
                  type="button"
                  onClick={() => onRemove(i)}
                  className="shrink-0 rounded p-0.5 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export { FileUploader };
