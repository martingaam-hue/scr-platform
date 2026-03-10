"use client";

import React from "react";
import { Moon, Sun, Sparkles } from "lucide-react";
import { useTheme } from "next-themes";
import { cn } from "@scr/ui";
import { SearchInput } from "@scr/ui";
import { useSidebarStore, useGlobalFilterStore, useRalphStore, useSearchStore } from "@/lib/store";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { NotificationBell } from "@/components/collaboration/notification-bell";

export function Topbar() {
  const { isOpen: sidebarOpen } = useSidebarStore();
  const { search, setSearch } = useGlobalFilterStore();
  const { theme, setTheme } = useTheme();
  const { toggle: toggleRalph, isOpen: ralphOpen } = useRalphStore();
  const { open: openSearch } = useSearchStore();

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

      {/* Search — clicking opens the command palette */}
      <div className="hidden w-72 md:block">
        <SearchInput
          value={search}
          onValueChange={setSearch}
          placeholder="Search anything..."
          shortcutHint={"\u2318K"}
          onFocus={openSearch}
          readOnly
        />
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1">
        {/* Notifications */}
        <NotificationBell />

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
        <button
          onClick={toggleRalph}
          className={cn(
            "ml-1 inline-flex items-center gap-1.5 rounded-lg bg-[#1B2A4A] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#243660]",
            ralphOpen && "bg-[#243660]",
          )}
        >
          <Sparkles className="h-4 w-4" />
          Ask Ralph
        </button>
      </div>
    </header>
  );
}
