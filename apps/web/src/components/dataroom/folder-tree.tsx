"use client";

import React, { useState, useCallback } from "react";
import {
  ChevronRight,
  ChevronDown,
  Folder,
  FolderOpen,
  Plus,
  Pencil,
  Trash2,
  MoreHorizontal,
} from "lucide-react";
import { cn, Button } from "@scr/ui";
import type { FolderTreeNode } from "@/lib/dataroom";

// ── Types ──────────────────────────────────────────────────────────────────

interface FolderTreeProps {
  folders: FolderTreeNode[];
  selectedFolderId: string | null;
  onSelectFolder: (folderId: string | null) => void;
  onCreateFolder: (parentId: string | null) => void;
  onRenameFolder: (folder: FolderTreeNode) => void;
  onDeleteFolder: (folderId: string) => void;
  canEdit?: boolean;
}

interface FolderNodeProps {
  node: FolderTreeNode;
  depth: number;
  selectedFolderId: string | null;
  expandedIds: Set<string>;
  onToggle: (id: string) => void;
  onSelect: (id: string) => void;
  onCreateFolder: (parentId: string | null) => void;
  onRenameFolder: (folder: FolderTreeNode) => void;
  onDeleteFolder: (folderId: string) => void;
  canEdit: boolean;
}

// ── Context menu ───────────────────────────────────────────────────────────

function FolderContextMenu({
  node,
  position,
  onClose,
  onCreateFolder,
  onRenameFolder,
  onDeleteFolder,
  canEdit,
}: {
  node: FolderTreeNode;
  position: { x: number; y: number };
  onClose: () => void;
  onCreateFolder: (parentId: string | null) => void;
  onRenameFolder: (folder: FolderTreeNode) => void;
  onDeleteFolder: (folderId: string) => void;
  canEdit: boolean;
}) {
  React.useEffect(() => {
    const handler = () => onClose();
    window.addEventListener("click", handler);
    return () => window.removeEventListener("click", handler);
  }, [onClose]);

  const items = [
    ...(canEdit
      ? [
          {
            label: "New subfolder",
            icon: Plus,
            action: () => onCreateFolder(node.id),
          },
          {
            label: "Rename",
            icon: Pencil,
            action: () => onRenameFolder(node),
          },
        ]
      : []),
    ...(canEdit && node.document_count === 0 && node.children.length === 0
      ? [
          {
            label: "Delete",
            icon: Trash2,
            action: () => onDeleteFolder(node.id),
            destructive: true,
          },
        ]
      : []),
  ];

  if (items.length === 0) return null;

  return (
    <div
      className="fixed z-50 min-w-[160px] rounded-md border border-neutral-200 bg-white py-1 shadow-lg dark:border-neutral-700 dark:bg-neutral-800"
      style={{ top: position.y, left: position.x }}
    >
      {items.map((item) => (
        <button
          key={item.label}
          onClick={(e) => {
            e.stopPropagation();
            item.action();
            onClose();
          }}
          className={cn(
            "flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm transition-colors",
            "destructive" in item && item.destructive
              ? "text-error-600 hover:bg-error-50 dark:text-error-400 dark:hover:bg-error-950"
              : "text-neutral-700 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-700"
          )}
        >
          <item.icon className="h-3.5 w-3.5" />
          {item.label}
        </button>
      ))}
    </div>
  );
}

// ── Single folder node ─────────────────────────────────────────────────────

function FolderNode({
  node,
  depth,
  selectedFolderId,
  expandedIds,
  onToggle,
  onSelect,
  onCreateFolder,
  onRenameFolder,
  onDeleteFolder,
  canEdit,
}: FolderNodeProps) {
  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
  } | null>(null);

  const isExpanded = expandedIds.has(node.id);
  const isSelected = selectedFolderId === node.id;
  const hasChildren = node.children.length > 0;

  const handleContextMenu = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      setContextMenu({ x: e.clientX, y: e.clientY });
    },
    []
  );

  return (
    <>
      <div
        role="treeitem"
        aria-expanded={hasChildren ? isExpanded : undefined}
        aria-selected={isSelected}
        className={cn(
          "group flex items-center gap-1 rounded-md px-2 py-1 text-sm transition-colors cursor-pointer",
          isSelected
            ? "bg-primary-50 text-primary-700 dark:bg-primary-950 dark:text-primary-300"
            : "text-neutral-700 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800"
        )}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onClick={() => onSelect(node.id)}
        onContextMenu={handleContextMenu}
      >
        {/* Expand/collapse chevron */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            if (hasChildren) onToggle(node.id);
          }}
          className={cn(
            "flex h-4 w-4 shrink-0 items-center justify-center rounded-sm",
            hasChildren
              ? "text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-200"
              : "invisible"
          )}
        >
          {isExpanded ? (
            <ChevronDown className="h-3.5 w-3.5" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5" />
          )}
        </button>

        {/* Folder icon */}
        {isExpanded ? (
          <FolderOpen className="h-4 w-4 shrink-0 text-secondary-500" />
        ) : (
          <Folder className="h-4 w-4 shrink-0 text-secondary-500" />
        )}

        {/* Name */}
        <span className="min-w-0 flex-1 truncate">{node.name}</span>

        {/* Doc count */}
        {node.document_count > 0 && (
          <span className="shrink-0 text-xs text-neutral-400">
            {node.document_count}
          </span>
        )}

        {/* More button */}
        {canEdit && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              const rect = e.currentTarget.getBoundingClientRect();
              setContextMenu({ x: rect.right, y: rect.bottom });
            }}
            className="invisible shrink-0 rounded p-0.5 text-neutral-400 hover:text-neutral-700 group-hover:visible dark:hover:text-neutral-200"
          >
            <MoreHorizontal className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {/* Context menu */}
      {contextMenu && (
        <FolderContextMenu
          node={node}
          position={contextMenu}
          onClose={() => setContextMenu(null)}
          onCreateFolder={onCreateFolder}
          onRenameFolder={onRenameFolder}
          onDeleteFolder={onDeleteFolder}
          canEdit={canEdit}
        />
      )}

      {/* Children */}
      {isExpanded &&
        node.children.map((child) => (
          <FolderNode
            key={child.id}
            node={child}
            depth={depth + 1}
            selectedFolderId={selectedFolderId}
            expandedIds={expandedIds}
            onToggle={onToggle}
            onSelect={onSelect}
            onCreateFolder={onCreateFolder}
            onRenameFolder={onRenameFolder}
            onDeleteFolder={onDeleteFolder}
            canEdit={canEdit}
          />
        ))}
    </>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

export function FolderTree({
  folders,
  selectedFolderId,
  onSelectFolder,
  onCreateFolder,
  onRenameFolder,
  onDeleteFolder,
  canEdit = false,
}: FolderTreeProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const handleToggle = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-neutral-200 px-3 py-2 dark:border-neutral-700">
        <span className="text-xs font-semibold uppercase tracking-wider text-neutral-500">
          Folders
        </span>
        {canEdit && (
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onCreateFolder(null)}
            className="h-6 w-6"
          >
            <Plus className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>

      {/* "All files" root option */}
      <div
        role="treeitem"
        aria-selected={selectedFolderId === null}
        className={cn(
          "flex cursor-pointer items-center gap-2 px-3 py-1.5 text-sm transition-colors",
          selectedFolderId === null
            ? "bg-primary-50 text-primary-700 dark:bg-primary-950 dark:text-primary-300"
            : "text-neutral-700 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800"
        )}
        onClick={() => onSelectFolder(null)}
      >
        <Folder className="h-4 w-4 text-neutral-400" />
        <span>All files</span>
      </div>

      {/* Tree */}
      <div role="tree" className="flex-1 overflow-y-auto py-1">
        {folders.map((node) => (
          <FolderNode
            key={node.id}
            node={node}
            depth={0}
            selectedFolderId={selectedFolderId}
            expandedIds={expandedIds}
            onToggle={handleToggle}
            onSelect={onSelectFolder}
            onCreateFolder={onCreateFolder}
            onRenameFolder={onRenameFolder}
            onDeleteFolder={onDeleteFolder}
            canEdit={canEdit}
          />
        ))}
      </div>
    </div>
  );
}
