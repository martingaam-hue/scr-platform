"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@scr/ui";
import { Sidebar } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";
import {
  FeatureTour,
  INVESTOR_TOUR_STEPS,
  ALLY_TOUR_STEPS,
} from "@/components/feature-tour";
import dynamic from "next/dynamic";
import { useSidebarStore, useRalphStore } from "@/lib/store";

const RalphPanel = dynamic(
  () =>
    import("@/components/ralph-ai/ralph-panel").then((m) => ({
      default: m.RalphPanel,
    })),
  { ssr: false, loading: () => null }
);
import { CommandPalette } from "@/components/search/command-palette";
import { useAuthenticatedApi, useSCRUser } from "@/lib/auth";
import { isOnboardingComplete } from "@/lib/onboarding";
import { BrandingProvider } from "@/components/branding-provider";

export function DashboardLayoutClient({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isOpen } = useSidebarStore();
  const { isOpen: isRalphOpen } = useRalphStore();
  const router = useRouter();
  const { user, isLoaded, isSignedIn } = useSCRUser();
  const [tourDismissed, setTourDismissed] = useState(false);

  useAuthenticatedApi();

  // Wait for Clerk to finish loading before rendering any data-fetching
  // components. Without this guard, hooks (BrandingProvider, NotificationBell,
  // dashboard page hooks) fire before the auth token is available, causing
  // every API request to be sent without Authorization → 403.
  if (!isLoaded) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50 dark:bg-[hsl(220,56%,7%)]">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
      </div>
    );
  }

  // Redirect to sign-in only when Clerk explicitly says not authenticated.
  // Do NOT redirect on API errors (e.g. 401/403 from /auth/me) — that would
  // create a redirect loop between /sign-in and /dashboard.
  if (!isSignedIn) {
    router.replace("/sign-in");
    return null;
  }

  if (isLoaded && isSignedIn && user && !isOnboardingComplete(user)) {
    router.replace("/onboarding");
    return null;
  }

  const showTour =
    !tourDismissed &&
    isLoaded &&
    user &&
    isOnboardingComplete(user) &&
    user.preferences?.tour_completed !== true;

  const tourSteps =
    user?.org_type === "investor" ? INVESTOR_TOUR_STEPS : ALLY_TOUR_STEPS;

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-[hsl(220,56%,7%)]">
      <BrandingProvider>
        <></>
      </BrandingProvider>
      <Sidebar />
      <Topbar />
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
      {isRalphOpen && <RalphPanel />}
      <CommandPalette />
      {showTour && (
        <FeatureTour
          steps={tourSteps}
          onComplete={() => setTourDismissed(true)}
        />
      )}
    </div>
  );
}
