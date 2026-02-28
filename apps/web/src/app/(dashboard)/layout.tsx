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
import { useSidebarStore } from "@/lib/store";
import { RalphPanel } from "@/components/ralph-ai/ralph-panel";
import { useAuthenticatedApi, useSCRUser } from "@/lib/auth";
import { isOnboardingComplete } from "@/lib/onboarding";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isOpen } = useSidebarStore();
  const router = useRouter();
  const { user, isLoaded } = useSCRUser();
  const [tourDismissed, setTourDismissed] = useState(false);

  // Register Clerk token provider for API calls
  useAuthenticatedApi();

  // Redirect to onboarding if not completed
  if (isLoaded && user && !isOnboardingComplete(user)) {
    router.replace("/onboarding");
    return null;
  }

  // Show feature tour if onboarding is done but tour hasn't been completed
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

      {/* Ralph AI panel */}
      <RalphPanel />

      {/* Feature tour overlay */}
      {showTour && (
        <FeatureTour
          steps={tourSteps}
          onComplete={() => setTourDismissed(true)}
        />
      )}
    </div>
  );
}
