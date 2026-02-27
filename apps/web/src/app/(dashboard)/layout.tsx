"use client";

import React from "react";
import { cn } from "@scr/ui";
import { Sidebar } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";
import { useSidebarStore } from "@/lib/store";
import { useAuthenticatedApi } from "@/lib/auth";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isOpen } = useSidebarStore();

  // Register Clerk token provider for API calls
  useAuthenticatedApi();

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-[hsl(220,56%,7%)]">
      <Sidebar />
      <Topbar />

      {/* Main content */}
      <main
        className={cn(
          "pt-[var(--topbar-height)] transition-all duration-300",
          isOpen
            ? "ml-[var(--sidebar-width)]"
            : "ml-[var(--sidebar-collapsed-width)]"
        )}
      >
        <div className="p-6">{children}</div>
      </main>
    </div>
  );
}
