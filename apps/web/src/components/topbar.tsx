"use client";

import React from "react";
import { Bell, Moon, Sun, PanelRightOpen } from "lucide-react";
import { useTheme } from "next-themes";
import { cn } from "@scr/ui";
import { SearchInput } from "@scr/ui";
import { useSidebarStore, useGlobalFilterStore } from "@/lib/store";
import { Breadcrumbs } from "@/components/breadcrumbs";

export function Topbar() {
  const { isOpen: sidebarOpen } = useSidebarStore();
  const { search, setSearch } = useGlobalFilterStore();
  const { theme, setTheme } = useTheme();

  return (
    <header
      className={cn(
        "fixed top-0 z-20 flex h-[var(--topbar-height)] items-center gap-4 border-b border-neutral-200 bg-white/80 px-6 backdrop-blur-md transition-all duration-300 dark:border-neutral-800 dark:bg-[hsl(220,56%,7%)]/80",
        sidebarOpen
          ? "left-[var(--sidebar-width)]"
          : "left-[var(--sidebar-collapsed-width)]"
      )}
      style={{ right: 0 }}
    >
      {/* Breadcrumbs */}
      <div className="flex-1">
        <Breadcrumbs />
      </div>

      {/* Search */}
      <div className="hidden w-72 md:block">
        <SearchInput
          value={search}
          onValueChange={setSearch}
          placeholder="Search anything..."
          shortcutHint={"\u2318K"}
        />
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1">
        {/* Notifications */}
        <button className="relative rounded-md p-2 text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700 dark:text-neutral-400 dark:hover:bg-neutral-800 dark:hover:text-neutral-200">
          <Bell className="h-5 w-5" />
          <span className="absolute right-1.5 top-1.5 flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-error-400 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-error-500" />
          </span>
        </button>

        {/* Theme toggle */}
        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="rounded-md p-2 text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700 dark:text-neutral-400 dark:hover:bg-neutral-800 dark:hover:text-neutral-200"
        >
          {theme === "dark" ? (
            <Sun className="h-5 w-5" />
          ) : (
            <Moon className="h-5 w-5" />
          )}
        </button>

        {/* Ralph AI toggle */}
        <button className="rounded-md p-2 text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700 dark:text-neutral-400 dark:hover:bg-neutral-800 dark:hover:text-neutral-200">
          <PanelRightOpen className="h-5 w-5" />
        </button>
      </div>
    </header>
  );
}
