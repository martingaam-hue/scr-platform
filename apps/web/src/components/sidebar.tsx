"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Briefcase,
  FolderKanban,
  BarChart3,
  ShieldAlert,
  Store,
  FileText,
  Bot,
  Wallet,
  FileCheck,
  Scale,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ShieldCheck,
  FolderLock,
  ScanSearch,
  TrendingUp,
  GitCompare,
  Users,
  Globe,
  Calendar,
  Leaf,
  Shield,
  Activity,
  Plug,
  MessageSquare,
  Bell,
  Trophy,
  Calculator,
  DollarSign,
  Target,
  Monitor,
  Link2,
  CreditCard,
  Coins,
  UserCheck,
  Sparkles,
  Zap,
  Network,
  Umbrella,
  Layers,
  Lightbulb,
  PieChart,
  Rss,
  Construction,
  TrendingDown,
  BarChart2,
} from "lucide-react";
import { useClerk } from "@clerk/nextjs";
import { cn } from "@scr/ui";
import { Avatar } from "@scr/ui";
import { useSidebarStore } from "@/lib/store";
import { useSCRUser } from "@/lib/auth";

// ── Navigation config ───────────────────────────────────────────────────

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number;
  roles?: string[];
  tourId?: string;
}

interface NavSection {
  title?: string;
  collapsible?: boolean;
  items: NavItem[];
}

// ── Investor nav ────────────────────────────────────────────────────────

const investorNav: NavSection[] = [
  {
    items: [
      { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    ],
  },
  {
    title: "Portfolio",
    collapsible: true,
    items: [
      { label: "Overview", href: "/portfolio", icon: Briefcase, tourId: "nav-portfolio" },
      { label: "Monitoring", href: "/monitoring", icon: Monitor },
      { label: "FX Exposure", href: "/fx", icon: Globe },
      { label: "Market Intelligence", href: "/market-data", icon: BarChart2 },
      { label: "Stress Testing", href: "/stress-test", icon: Activity },
      { label: "ESG Dashboard", href: "/esg", icon: Leaf },
      { label: "LP Reports", href: "/lp-reports", icon: FileText },
      { label: "Capital Efficiency", href: "/capital-efficiency", icon: Coins },
      { label: "J-Curve Pacing", href: "/pacing", icon: TrendingDown },
      { label: "Financial Models", href: "/financial-templates", icon: Calculator },
      { label: "Benchmarks & Metrics", href: "/metrics", icon: TrendingUp },
    ],
  },
  {
    title: "Deal Pipeline",
    collapsible: true,
    items: [
      { label: "Deals", href: "/deals", icon: FolderKanban, tourId: "nav-deals" },
      { label: "Smart Screener", href: "/screener", icon: ScanSearch, tourId: "nav-screener" },
      { label: "Deal Rooms", href: "/deal-rooms", icon: MessageSquare },
      { label: "Comparable Transactions", href: "/comps", icon: GitCompare },
    ],
  },
  {
    items: [
      { label: "Matching", href: "/matching", icon: Zap },
      { label: "Data Room", href: "/data-room", icon: FolderLock, tourId: "nav-data-room" },
    ],
  },
  {
    title: "Risk & Compliance",
    collapsible: true,
    items: [
      { label: "Risk Dashboard", href: "/risk", icon: ShieldAlert },
      { label: "Compliance Calendar", href: "/compliance", icon: Calendar },
      { label: "Blockchain Audit", href: "/blockchain-audit", icon: Link2 },
    ],
  },
  {
    items: [
      { label: "Marketplace", href: "/marketplace", icon: Store },
      { label: "Watchlists", href: "/watchlists", icon: Bell },
      { label: "Reports", href: "/reports", icon: BarChart3 },
      { label: "Impact", href: "/impact", icon: Target },
      { label: "Notifications", href: "/notifications", icon: Bell },
    ],
  },
  {
    title: "Investor Tools",
    collapsible: true,
    items: [
      { label: "Signal Score", href: "/investor-signal-score", icon: Sparkles },
      { label: "Risk Profile", href: "/risk-profile", icon: ShieldCheck },
      { label: "Board Advisor", href: "/board-advisor", icon: UserCheck },
      { label: "Equity Calculator", href: "/equity-calculator", icon: Calculator },
      { label: "Value Quantifier", href: "/value-quantifier", icon: DollarSign },
      { label: "Deal Flow Analytics", href: "/analytics/deal-flow", icon: TrendingUp },
      { label: "Portfolio Analytics", href: "/analytics/portfolio", icon: BarChart3 },
      { label: "Score Performance", href: "/score-performance", icon: BarChart2 },
    ],
  },
  {
    title: "AI",
    items: [{ label: "Ralph AI", href: "/dashboard", icon: Bot, tourId: "nav-ralph" }],
  },
  {
    title: "Settings",
    collapsible: true,
    items: [
      { label: "Settings", href: "/settings", icon: Settings },
      { label: "Connectors", href: "/connectors", icon: Plug },
      { label: "Sync History", href: "/connectors/sync-history", icon: Plug },
      { label: "Investor Personas", href: "/investor-personas", icon: Users },
      { label: "Ecosystem", href: "/ecosystem", icon: Network },
      { label: "Activity Digest", href: "/digest", icon: Rss },
    ],
  },
];

// ── Ally nav ─────────────────────────────────────────────────────────────

const allyNav: NavSection[] = [
  {
    items: [
      { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
      { label: "Projects", href: "/projects", icon: FolderKanban, tourId: "nav-projects" },
    ],
  },
  {
    title: "Deal Pipeline",
    collapsible: true,
    items: [
      { label: "Deals", href: "/deals", icon: FolderKanban },
      { label: "Investor Matching", href: "/matching", icon: Zap },
      { label: "Warm Introductions", href: "/warm-intros", icon: Users },
    ],
  },
  {
    items: [
      { label: "Data Room", href: "/data-room", icon: FolderLock, tourId: "nav-data-room" },
      { label: "Funding", href: "/funding", icon: Wallet, tourId: "nav-funding" },
      { label: "Reports", href: "/reports", icon: BarChart3 },
    ],
  },
  {
    title: "Tools",
    collapsible: true,
    items: [
      { label: "Business Plan", href: "/business-plan", icon: FileText },
      { label: "Legal", href: "/legal", icon: Scale },
      { label: "Valuation", href: "/valuations", icon: PieChart },
      { label: "Tax Credits", href: "/tax-credits", icon: CreditCard },
      { label: "Insurance", href: "/insurance", icon: Umbrella },
      { label: "Board Advisor", href: "/board-advisor", icon: UserCheck },
      { label: "Capital Efficiency", href: "/capital-efficiency", icon: Coins },
      { label: "Value Quantifier", href: "/value-quantifier", icon: DollarSign },
      { label: "Tokenization", href: "/tokenization", icon: Layers },
      { label: "Dev OS", href: "/development-os", icon: Monitor },
      { label: "Activity Feed", href: "/collaboration", icon: Activity },
      { label: "Q&A Workflow", href: "/qa", icon: MessageSquare },
      { label: "Engagement Analytics", href: "/engagement", icon: Activity },
      { label: "AI Citations", href: "/citations", icon: FileText },
    ],
  },
  {
    title: "Impact & Compliance",
    collapsible: true,
    items: [
      { label: "ESG Dashboard", href: "/esg", icon: Leaf },
      { label: "Impact", href: "/impact", icon: Target },
      { label: "Compliance", href: "/compliance", icon: Shield },
      { label: "Ecosystem", href: "/ecosystem", icon: Network },
    ],
  },
  {
    items: [
      { label: "Notifications", href: "/notifications", icon: Bell },
    ],
  },
  {
    title: "AI",
    items: [{ label: "Ralph AI", href: "/dashboard", icon: Bot, tourId: "nav-ralph" }],
  },
  {
    title: "Settings",
    collapsible: true,
    items: [
      { label: "Settings", href: "/settings", icon: Settings },
      { label: "Gamification", href: "/gamification", icon: Trophy },
      { label: "Activity Digest", href: "/digest", icon: Rss },
    ],
  },
];

// ── Admin nav ────────────────────────────────────────────────────────────

const adminNav: NavSection[] = [
  {
    items: [
      { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
      { label: "Projects", href: "/projects", icon: FolderKanban },
    ],
  },
  {
    title: "Portfolio",
    collapsible: true,
    items: [
      { label: "Overview", href: "/portfolio", icon: Briefcase },
      { label: "Monitoring", href: "/monitoring", icon: Monitor },
      { label: "FX Exposure", href: "/fx", icon: Globe },
      { label: "Market Intelligence", href: "/market-data", icon: BarChart2 },
      { label: "Stress Testing", href: "/stress-test", icon: Activity },
      { label: "ESG Dashboard", href: "/esg", icon: Leaf },
      { label: "LP Reports", href: "/lp-reports", icon: FileText },
      { label: "Capital Efficiency", href: "/capital-efficiency", icon: Coins },
      { label: "J-Curve Pacing", href: "/pacing", icon: TrendingDown },
      { label: "Financial Models", href: "/financial-templates", icon: Calculator },
      { label: "Benchmarks & Metrics", href: "/metrics", icon: TrendingUp },
    ],
  },
  {
    title: "Deal Pipeline",
    collapsible: true,
    items: [
      { label: "Deals", href: "/deals", icon: FolderKanban },
      { label: "Smart Screener", href: "/screener", icon: ScanSearch },
      { label: "Deal Rooms", href: "/deal-rooms", icon: MessageSquare },
      { label: "Comparable Transactions", href: "/comps", icon: GitCompare },
    ],
  },
  {
    items: [
      { label: "Matching", href: "/matching", icon: Zap },
      { label: "Data Room", href: "/data-room", icon: FolderLock },
    ],
  },
  {
    title: "Risk & Compliance",
    collapsible: true,
    items: [
      { label: "Risk Dashboard", href: "/risk", icon: ShieldAlert },
      { label: "Compliance Calendar", href: "/compliance", icon: Calendar },
    ],
  },
  {
    items: [
      { label: "Marketplace", href: "/marketplace", icon: Store },
      { label: "Watchlists", href: "/watchlists", icon: Bell },
      { label: "Reports", href: "/reports", icon: BarChart3 },
      { label: "Notifications", href: "/notifications", icon: Bell },
    ],
  },
  {
    title: "Investor Tools",
    collapsible: true,
    items: [
      { label: "Signal Score", href: "/investor-signal-score", icon: Sparkles },
      { label: "Risk Profile", href: "/risk-profile", icon: ShieldCheck },
      { label: "Board Advisor", href: "/board-advisor", icon: UserCheck },
      { label: "Equity Calculator", href: "/equity-calculator", icon: Calculator },
      { label: "Value Quantifier", href: "/value-quantifier", icon: DollarSign },
      { label: "Impact", href: "/impact", icon: Target },
      { label: "Deal Flow Analytics", href: "/analytics/deal-flow", icon: TrendingUp },
      { label: "Portfolio Analytics", href: "/analytics/portfolio", icon: BarChart3 },
      { label: "Score Performance", href: "/score-performance", icon: BarChart2 },
    ],
  },
  {
    title: "AI",
    items: [{ label: "Ralph AI", href: "/dashboard", icon: Bot }],
  },
  {
    title: "Admin",
    collapsible: true,
    items: [
      { label: "Admin Panel", href: "/admin", icon: ShieldCheck },
      { label: "Prompt Templates", href: "/admin/prompts", icon: FileText },
      { label: "System Health", href: "/admin/health", icon: Activity },
      { label: "AI Cost Management", href: "/admin/ai-costs", icon: DollarSign },
      { label: "Feature Flags", href: "/admin/feature-flags", icon: Construction },
      { label: "Blockchain Audit", href: "/blockchain-audit", icon: Link2 },
      { label: "Gamification", href: "/gamification", icon: Trophy },
    ],
  },
  {
    title: "Settings",
    collapsible: true,
    items: [
      { label: "Settings", href: "/settings", icon: Settings },
      { label: "Connectors", href: "/connectors", icon: Plug },
      { label: "Sync History", href: "/connectors/sync-history", icon: Plug },
      { label: "Investor Personas", href: "/investor-personas", icon: Users },
      { label: "Ecosystem", href: "/ecosystem", icon: Network },
      { label: "Activity Digest", href: "/digest", icon: Rss },
    ],
  },
];

function getNavForRole(orgType?: string): NavSection[] {
  switch (orgType) {
    case "investor":
      return investorNav;
    case "ally":
      return allyNav;
    case "admin":
      return adminNav;
    default:
      return allyNav;
  }
}

// ── Project sub-nav ─────────────────────────────────────────────────────

const PROJECT_SUB_ITEMS = [
  { label: "Signal Score", segment: "signal-score", icon: Sparkles },
  { label: "Due Diligence", segment: "due-diligence", icon: ScanSearch },
  { label: "Expert Insights", segment: "expert-insights", icon: Lightbulb },
  { label: "Matching", segment: "matching", icon: Zap },
  { label: "Meeting Prep", segment: "meeting-prep", icon: Calendar },
  { label: "Certification", segment: "certification", icon: FileCheck },
  { label: "Carbon", segment: "carbon", icon: Leaf },
  { label: "Insurance", segment: "insurance", icon: Umbrella },
] as const;

function ProjectSubNav({
  projectId,
  pathname,
  isOpen,
}: {
  projectId: string;
  pathname: string;
  isOpen: boolean;
}) {
  return (
    <div className="mt-1 ml-3 border-l border-white/20 pl-3">
      {isOpen && (
        <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-white/30">
          Project
        </p>
      )}
      <ul className="space-y-0.5">
        {PROJECT_SUB_ITEMS.map(({ label, segment, icon: Icon }) => {
          const href = `/projects/${projectId}/${segment}`;
          const isActive = pathname.startsWith(href);
          return (
            <li key={segment}>
              <Link
                href={href}
                title={!isOpen ? label : undefined}
                className={`flex items-center gap-2 rounded-md px-2 py-1.5 text-xs font-medium transition-colors ${
                  isActive
                    ? "bg-white/15 text-white"
                    : "text-white/60 hover:bg-white/10 hover:text-white"
                } ${!isOpen ? "justify-center" : ""}`}
              >
                <Icon className="h-3.5 w-3.5 shrink-0" />
                {isOpen && <span>{label}</span>}
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

// ── Collapsible section ──────────────────────────────────────────────────

function CollapsibleSectionHeader({
  title,
  isCollapsed,
  onToggle,
  isOpen: sidebarOpen,
}: {
  title: string;
  isCollapsed: boolean;
  onToggle: () => void;
  isOpen: boolean;
}) {
  if (!sidebarOpen) {
    return <div className="mx-3 mb-3 border-t border-white/10" />;
  }
  return (
    <button
      onClick={onToggle}
      className="mb-1 flex w-full items-center justify-between px-3 text-[10px] font-semibold uppercase tracking-widest text-white/40 hover:text-white/60 transition-colors"
    >
      <span>{title}</span>
      <ChevronDown
        className={cn(
          "h-3 w-3 transition-transform",
          isCollapsed && "-rotate-90"
        )}
      />
    </button>
  );
}

// ── Sidebar component ───────────────────────────────────────────────────

export function Sidebar() {
  const pathname = usePathname();
  const { isOpen, toggle } = useSidebarStore();
  const { signOut } = useClerk();
  const { user } = useSCRUser();

  const navSections = getNavForRole(user?.org_type);

  // Track which collapsible sections are collapsed (by title)
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set());

  const toggleSection = (title: string) => {
    setCollapsedSections((prev) => {
      const next = new Set(prev);
      if (next.has(title)) {
        next.delete(title);
      } else {
        next.add(title);
      }
      return next;
    });
  };

  // Extract project ID for context-aware sub-nav
  const projectMatch = pathname.match(/\/projects\/([^/]+)/);
  const activeProjectId = projectMatch ? projectMatch[1] : null;

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-30 flex h-screen flex-col border-r border-neutral-200 bg-primary-600 text-white transition-all duration-300 dark:border-neutral-800 dark:bg-primary-800",
        isOpen ? "w-[var(--sidebar-width)]" : "w-[var(--sidebar-collapsed-width)]"
      )}
    >
      {/* Logo */}
      <div className="flex h-[var(--topbar-height)] items-center justify-between px-4">
        {isOpen && (
          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-secondary-500 text-sm font-bold text-white">
              S
            </div>
            <span className="text-lg font-bold tracking-tight">SCR</span>
          </Link>
        )}
        <button
          onClick={toggle}
          className={cn(
            "rounded-md p-1.5 text-white/70 hover:bg-white/10 hover:text-white",
            !isOpen && "mx-auto"
          )}
        >
          {isOpen ? (
            <ChevronLeft className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-4">
        {navSections.map((section, si) => {
          const sectionKey = section.title ?? `section-${si}`;
          const isCollapsed = !!(section.title && collapsedSections.has(section.title));
          const showItems = !section.collapsible || !isCollapsed || !isOpen;

          return (
            <div key={sectionKey} className={cn(si > 0 && "mt-4")}>
              {/* Section header */}
              {section.title && section.collapsible ? (
                <CollapsibleSectionHeader
                  title={section.title}
                  isCollapsed={isCollapsed}
                  onToggle={() => toggleSection(section.title!)}
                  isOpen={isOpen}
                />
              ) : section.title && isOpen ? (
                <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-white/40">
                  {section.title}
                </p>
              ) : si > 0 && !isOpen && !section.title ? (
                <div className="mx-3 mb-3 border-t border-white/10" />
              ) : null}

              {/* Section items */}
              {showItems && (
                <ul className="space-y-0.5">
                  {section.items.map((item) => {
                    const isActive =
                      item.href === "/dashboard"
                        ? pathname === "/dashboard"
                        : pathname.startsWith(item.href);
                    const isProjectsLink =
                      (item.href === "/projects" || item.href === "/dashboard/projects") &&
                      activeProjectId;
                    return (
                      <React.Fragment key={item.href}>
                        <li>
                          <Link
                            href={item.href}
                            title={!isOpen ? item.label : undefined}
                            data-tour={item.tourId}
                            className={cn(
                              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                              isActive
                                ? "bg-white/15 text-white"
                                : "text-white/70 hover:bg-white/10 hover:text-white",
                              !isOpen && "justify-center px-2"
                            )}
                          >
                            <item.icon className="h-5 w-5 shrink-0" />
                            {isOpen && <span>{item.label}</span>}
                            {isOpen && item.badge !== undefined && item.badge > 0 && (
                              <span className="ml-auto inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-secondary-500 px-1.5 text-[10px] font-bold text-white">
                                {item.badge}
                              </span>
                            )}
                          </Link>
                        </li>
                        {isProjectsLink && (
                          <li>
                            <ProjectSubNav
                              projectId={activeProjectId}
                              pathname={pathname}
                              isOpen={isOpen}
                            />
                          </li>
                        )}
                      </React.Fragment>
                    );
                  })}
                </ul>
              )}
            </div>
          );
        })}
      </nav>

      {/* User section */}
      <div className="border-t border-white/10 p-3">
        <div
          className={cn(
            "flex items-center gap-3",
            !isOpen && "justify-center"
          )}
        >
          <Avatar
            src={user?.avatar_url}
            alt={user?.full_name}
            size="sm"
            className="ring-2 ring-white/20"
          />
          {isOpen && (
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-white">
                {user?.full_name ?? "Loading..."}
              </p>
              <p className="truncate text-xs text-white/50">
                {user?.org_name}
              </p>
            </div>
          )}
          {isOpen && (
            <div className="flex items-center gap-1">
              <Link
                href="/dashboard/settings"
                className="rounded-md p-1.5 text-white/50 hover:bg-white/10 hover:text-white"
              >
                <Settings className="h-4 w-4" />
              </Link>
              <button
                onClick={() => signOut()}
                className="rounded-md p-1.5 text-white/50 hover:bg-white/10 hover:text-white"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
