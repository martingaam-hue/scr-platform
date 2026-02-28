"use client";

import React from "react";
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
  Mic,
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
  items: NavItem[];
}

const investorNav: NavSection[] = [
  {
    items: [
      { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
      { label: "Portfolio", href: "/dashboard/portfolio", icon: Briefcase, tourId: "nav-portfolio" },
      { label: "Deals", href: "/dashboard/deals", icon: FolderKanban, tourId: "nav-deals" },
      { label: "Smart Screener", href: "/dashboard/screener", icon: ScanSearch, tourId: "nav-screener" },
      { label: "Data Room", href: "/dashboard/data-room", icon: FolderLock, tourId: "nav-data-room" },
      { label: "Risk", href: "/dashboard/risk", icon: ShieldAlert },
      { label: "Marketplace", href: "/dashboard/marketplace", icon: Store },
      { label: "Reports", href: "/dashboard/reports", icon: BarChart3 },
    ],
  },
  {
    title: "Analytics",
    items: [
      { label: "Deal Flow", href: "/analytics/deal-flow", icon: TrendingUp },
      { label: "LP Reports", href: "/reports/lp", icon: FileText },
      { label: "Comps DB", href: "/comps", icon: GitCompare },
      { label: "ESG Dashboard", href: "/esg", icon: Leaf },
      { label: "Impact", href: "/impact", icon: Target },
      { label: "FX Exposure", href: "/portfolio/fx", icon: Globe },
      { label: "Stress Test", href: "/portfolio/stress-test", icon: Activity },
    ],
  },
  {
    title: "Investor Tools",
    items: [
      { label: "Signal Score", href: "/investor-signal-score", icon: Sparkles },
      { label: "Board Advisor", href: "/board-advisor", icon: UserCheck },
      { label: "Investor Personas", href: "/investor-personas", icon: Users },
      { label: "Equity Calculator", href: "/equity-calculator", icon: Calculator },
      { label: "Value Quantifier", href: "/value-quantifier", icon: DollarSign },
      { label: "Capital Efficiency", href: "/capital-efficiency", icon: Coins },
    ],
  },
  {
    title: "Network",
    items: [
      { label: "Warm Intros", href: "/warm-intros", icon: Users },
      { label: "Deal Rooms", href: "/deal-rooms", icon: MessageSquare },
      { label: "Ecosystem", href: "/ecosystem", icon: Network },
    ],
  },
  {
    title: "Operations",
    items: [
      { label: "Compliance", href: "/compliance", icon: Shield },
      { label: "Watchlists", href: "/watchlists", icon: Bell },
      { label: "Connectors", href: "/connectors", icon: Plug },
    ],
  },
  {
    title: "AI",
    items: [{ label: "Ralph AI", href: "/dashboard/ralph", icon: Bot, tourId: "nav-ralph" }],
  },
  {
    title: "Account",
    items: [{ label: "Settings", href: "/settings", icon: Settings }],
  },
];

const allyNav: NavSection[] = [
  {
    items: [
      { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
      { label: "Projects", href: "/dashboard/projects", icon: FolderKanban, tourId: "nav-projects" },
      { label: "Business Plan", href: "/business-plan", icon: FileText },
      { label: "Data Room", href: "/dashboard/data-room", icon: FolderLock, tourId: "nav-data-room" },
      { label: "Funding", href: "/dashboard/funding", icon: Wallet, tourId: "nav-funding" },
      { label: "Documents", href: "/dashboard/documents", icon: FileCheck },
      { label: "Legal", href: "/dashboard/legal", icon: Scale },
      { label: "Reports", href: "/dashboard/reports", icon: BarChart3 },
    ],
  },
  {
    title: "Tools",
    items: [
      { label: "Deal Rooms", href: "/deal-rooms", icon: MessageSquare },
      { label: "Compliance", href: "/compliance", icon: Shield },
      { label: "Insurance", href: "/insurance", icon: Umbrella },
      { label: "Tax Credits", href: "/tax-credits", icon: CreditCard },
      { label: "Board Advisor", href: "/board-advisor", icon: UserCheck },
      { label: "Capital Efficiency", href: "/capital-efficiency", icon: Coins },
      { label: "Dev OS", href: "/development-os", icon: Monitor },
      { label: "Score & Badges", href: "/gamification", icon: Trophy },
      { label: "Voice Input", href: "/onboarding/voice", icon: Mic },
    ],
  },
  {
    title: "Impact",
    items: [
      { label: "ESG Dashboard", href: "/esg", icon: Leaf },
      { label: "Impact", href: "/impact", icon: Target },
      { label: "Ecosystem", href: "/ecosystem", icon: Network },
    ],
  },
  {
    title: "AI",
    items: [{ label: "Ralph AI", href: "/dashboard/ralph", icon: Bot, tourId: "nav-ralph" }],
  },
  {
    title: "Account",
    items: [{ label: "Settings", href: "/settings", icon: Settings }],
  },
];

const adminNav: NavSection[] = [
  {
    items: [
      { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
      { label: "Portfolio", href: "/dashboard/portfolio", icon: Briefcase },
      { label: "Projects", href: "/dashboard/projects", icon: FolderKanban },
      { label: "Data Room", href: "/dashboard/data-room", icon: FolderLock },
      { label: "Deals", href: "/dashboard/deals", icon: FolderKanban },
      { label: "Smart Screener", href: "/dashboard/screener", icon: ScanSearch },
      { label: "Risk", href: "/dashboard/risk", icon: ShieldAlert },
      { label: "Marketplace", href: "/dashboard/marketplace", icon: Store },
      { label: "Reports", href: "/dashboard/reports", icon: BarChart3 },
    ],
  },
  {
    title: "Analytics",
    items: [
      { label: "Deal Flow", href: "/analytics/deal-flow", icon: TrendingUp },
      { label: "LP Reports", href: "/reports/lp", icon: FileText },
      { label: "Comps DB", href: "/comps", icon: GitCompare },
      { label: "ESG Dashboard", href: "/esg", icon: Leaf },
      { label: "Impact", href: "/impact", icon: Target },
      { label: "FX Exposure", href: "/portfolio/fx", icon: Globe },
      { label: "Stress Test", href: "/portfolio/stress-test", icon: Activity },
    ],
  },
  {
    title: "Investor Tools",
    items: [
      { label: "Signal Score", href: "/investor-signal-score", icon: Sparkles },
      { label: "Board Advisor", href: "/board-advisor", icon: UserCheck },
      { label: "Investor Personas", href: "/investor-personas", icon: Users },
      { label: "Equity Calculator", href: "/equity-calculator", icon: Calculator },
      { label: "Value Quantifier", href: "/value-quantifier", icon: DollarSign },
      { label: "Capital Efficiency", href: "/capital-efficiency", icon: Coins },
      { label: "Tax Credits", href: "/tax-credits", icon: CreditCard },
    ],
  },
  {
    title: "Network",
    items: [
      { label: "Warm Intros", href: "/warm-intros", icon: Users },
      { label: "Deal Rooms", href: "/deal-rooms", icon: MessageSquare },
      { label: "Ecosystem", href: "/ecosystem", icon: Network },
    ],
  },
  {
    title: "Operations",
    items: [
      { label: "Compliance", href: "/compliance", icon: Shield },
      { label: "Watchlists", href: "/watchlists", icon: Bell },
      { label: "Connectors", href: "/connectors", icon: Plug },
      { label: "Score & Badges", href: "/gamification", icon: Trophy },
      { label: "Dev OS", href: "/development-os", icon: Monitor },
    ],
  },
  {
    title: "AI",
    items: [{ label: "Ralph AI", href: "/dashboard/ralph", icon: Bot }],
  },
  {
    title: "Admin",
    items: [
      { label: "Admin Panel", href: "/dashboard/admin", icon: ShieldCheck },
      { label: "Blockchain Audit", href: "/blockchain-audit", icon: Link2 },
      { label: "Settings", href: "/settings", icon: Settings },
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

// ── Sidebar component ───────────────────────────────────────────────────

export function Sidebar() {
  const pathname = usePathname();
  const { isOpen, toggle } = useSidebarStore();
  const { signOut } = useClerk();
  const { user } = useSCRUser();

  const navSections = getNavForRole(user?.org_type);

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
        {navSections.map((section, si) => (
          <div key={si} className={cn(si > 0 && "mt-6")}>
            {section.title && isOpen && (
              <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-white/40">
                {section.title}
              </p>
            )}
            {si > 0 && !isOpen && (
              <div className="mx-3 mb-3 border-t border-white/10" />
            )}
            <ul className="space-y-0.5">
              {section.items.map((item) => {
                const isActive =
                  item.href === "/dashboard"
                    ? pathname === "/dashboard"
                    : pathname.startsWith(item.href);
                const isProjectsLink =
                  item.href === "/dashboard/projects" && activeProjectId;
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
          </div>
        ))}
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
