"use client";

import React, { useState, useCallback } from "react";
import { Upload, X, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalTitle,
  ModalDescription,
  ModalFooter,
  ModalClose,
  Button,
  FileUploader,
  cn,
} from "@scr/ui";
import type { FileItem } from "@scr/ui";
import {
  usePresignedUpload,
  useConfirmUpload,
  computeSHA256,
  formatFileSize,
} from "@/lib/dataroom";

// ── Types ──────────────────────────────────────────────────────────────────

interface UploadModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  folderId?: string | null;
}

const ALLOWED_EXTENSIONS = ".pdf,.docx,.xlsx,.pptx,.csv,.jpg,.png";

// ── Component ──────────────────────────────────────────────────────────────

export function UploadModal({
  open,
  onOpenChange,
  projectId,
  folderId,
}: UploadModalProps) {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const [completed, setCompleted] = useState(0);

  const presignedUpload = usePresignedUpload();
  const confirmUpload = useConfirmUpload();

  const handleFilesSelected = useCallback((newFiles: File[]) => {
    const items: FileItem[] = newFiles.map((file) => ({
      file,
      progress: 0,
      status: "pending" as const,
    }));
    setFiles((prev) => [...prev, ...items]);
  }, []);

  const handleRemove = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const updateFileStatus = useCallback(
    (
      index: number,
      update: Partial<FileItem>
    ) => {
      setFiles((prev) =>
        prev.map((f, i) => (i === index ? { ...f, ...update } : f))
      );
    },
    []
  );

  const uploadSingleFile = useCallback(
    async (fileItem: FileItem, index: number) => {
      try {
        updateFileStatus(index, { status: "uploading", progress: 10 });

        // 1. Compute SHA-256 hash
        const checksum = await computeSHA256(fileItem.file);
        updateFileStatus(index, { progress: 20 });

        // 2. Get file extension
        const ext = fileItem.file.name.split(".").pop()?.toLowerCase() ?? "";

        // 3. Request pre-signed URL
        const presigned = await presignedUpload.mutateAsync({
          file_name: fileItem.file.name,
          file_type: ext,
          file_size_bytes: fileItem.file.size,
          project_id: projectId,
          folder_id: folderId,
          checksum_sha256: checksum,
        });
        updateFileStatus(index, { progress: 40 });

        // 4. Upload directly to S3
        await fetch(presigned.upload_url, {
          method: "PUT",
          body: fileItem.file,
          headers: { "Content-Type": fileItem.file.type || "application/octet-stream" },
        });
        updateFileStatus(index, { progress: 80 });

        // 5. Confirm upload
        await confirmUpload.mutateAsync({
          document_id: presigned.document_id,
        });
        updateFileStatus(index, { status: "done", progress: 100 });
        setCompleted((p) => p + 1);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Upload failed";
        updateFileStatus(index, { status: "error", error: message });
      }
    },
    [presignedUpload, confirmUpload, projectId, folderId, updateFileStatus]
  );

  const handleUploadAll = useCallback(async () => {
    setUploading(true);
    setCompleted(0);

    const pending = files
      .map((f, i) => ({ f, i }))
      .filter(({ f }) => f.status === "pending" || f.status === "error");

    // Upload up to 3 at a time
    const concurrency = 3;
    for (let i = 0; i < pending.length; i += concurrency) {
      const batch = pending.slice(i, i + concurrency);
      await Promise.all(batch.map(({ f, i: idx }) => uploadSingleFile(f, idx)));
    }

    setUploading(false);
  }, [files, uploadSingleFile]);

  const handleClose = useCallback(() => {
    if (!uploading) {
      setFiles([]);
      setCompleted(0);
      onOpenChange(false);
    }
  }, [uploading, onOpenChange]);

  const pendingCount = files.filter(
    (f) => f.status === "pending" || f.status === "error"
  ).length;
  const allDone =
    files.length > 0 && files.every((f) => f.status === "done");

  return (
    <Modal open={open} onOpenChange={uploading ? undefined : onOpenChange}>
      <ModalContent className="sm:max-w-xl">
        <ModalHeader>
          <ModalTitle>Upload Documents</ModalTitle>
          <ModalDescription>
            Drag and drop files or click to browse. Max 100 MB per file.
          </ModalDescription>
        </ModalHeader>

        <div className="px-6">
          {/* Dropzone */}
          <FileUploader
            accept={ALLOWED_EXTENSIONS}
            multiple
            maxSizeMB={100}
            onFilesSelected={handleFilesSelected}
            files={files}
            onRemove={handleRemove}
            disabled={uploading}
          />

          {/* Summary */}
          {files.length > 0 && (
            <div className="mt-3 flex items-center gap-3 text-sm text-neutral-500">
              <span>
                {files.length} file{files.length !== 1 ? "s" : ""} selected
              </span>
              <span className="text-neutral-300 dark:text-neutral-600">
                |
              </span>
              <span>
                {formatFileSize(
                  files.reduce((sum, f) => sum + f.file.size, 0)
                )}
              </span>
              {uploading && (
                <>
                  <span className="text-neutral-300 dark:text-neutral-600">
                    |
                  </span>
                  <span className="flex items-center gap-1">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    {completed}/{files.length} uploaded
                  </span>
                </>
              )}
            </div>
          )}
        </div>

        <ModalFooter>
          <ModalClose asChild>
            <Button variant="outline" onClick={handleClose} disabled={uploading}>
              {allDone ? "Close" : "Cancel"}
            </Button>
          </ModalClose>
          {!allDone && (
            <Button
              onClick={handleUploadAll}
              disabled={pendingCount === 0 || uploading}
              loading={uploading}
              iconLeft={<Upload className="h-4 w-4" />}
            >
              Upload {pendingCount > 0 ? `(${pendingCount})` : ""}
            </Button>
          )}
          {allDone && (
            <Button onClick={handleClose} iconLeft={<CheckCircle className="h-4 w-4" />}>
              Done
            </Button>
          )}
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}
