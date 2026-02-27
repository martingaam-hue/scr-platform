"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight } from "lucide-react";

const labelMap: Record<string, string> = {
  dashboard: "Dashboard",
  portfolio: "Portfolio",
  projects: "Projects",
  deals: "Deals",
  risk: "Risk",
  marketplace: "Marketplace",
  reports: "Reports",
  ralph: "Ralph AI",
  funding: "Funding",
  documents: "Documents",
  legal: "Legal",
  settings: "Settings",
  admin: "Admin",
};

export function Breadcrumbs() {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);

  if (segments.length <= 1) return null;

  const crumbs = segments.map((seg, i) => {
    const href = "/" + segments.slice(0, i + 1).join("/");
    const label = labelMap[seg] || seg.charAt(0).toUpperCase() + seg.slice(1);
    const isLast = i === segments.length - 1;
    return { href, label, isLast };
  });

  return (
    <nav className="flex items-center gap-1 text-sm">
      {crumbs.map((crumb, i) => (
        <React.Fragment key={crumb.href}>
          {i > 0 && (
            <ChevronRight className="h-3.5 w-3.5 text-neutral-300 dark:text-neutral-600" />
          )}
          {crumb.isLast ? (
            <span className="font-medium text-neutral-900 dark:text-neutral-100">
              {crumb.label}
            </span>
          ) : (
            <Link
              href={crumb.href}
              className="text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
            >
              {crumb.label}
            </Link>
          )}
        </React.Fragment>
      ))}
    </nav>
  );
}
