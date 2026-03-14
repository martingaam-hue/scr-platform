"use client";

import { useProjects } from "@/lib/projects";

interface ProjectSelectorProps {
  selectedId?: string;
  onChange: (id: string) => void;
  placeholder?: string;
  className?: string;
}

export function ProjectSelector({
  selectedId,
  onChange,
  placeholder = "Select project…",
  className,
}: ProjectSelectorProps) {
  const { data: projects, isLoading } = useProjects();

  return (
    <select
      value={selectedId ?? ""}
      onChange={(e) => onChange(e.target.value)}
      disabled={isLoading}
      className={`rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-700 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 disabled:opacity-50 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-200 ${className ?? ""}`}
    >
      <option value="" disabled>
        {isLoading ? "Loading…" : placeholder}
      </option>
      {projects?.items?.map((p: { id: string; name: string }) => (
        <option key={p.id} value={p.id}>
          {p.name}
        </option>
      ))}
    </select>
  );
}
