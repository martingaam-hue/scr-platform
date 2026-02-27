"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { useAuthenticatedApi, useSCRUser } from "@/lib/auth";
import { isOnboardingComplete } from "@/lib/onboarding";

export default function OnboardingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { user, isLoaded } = useSCRUser();

  // Inject Clerk token for API calls
  useAuthenticatedApi();

  // Already onboarded → redirect to dashboard
  if (isLoaded && user && isOnboardingComplete(user)) {
    router.replace("/dashboard");
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-secondary-50">
      {/* Top bar with logo */}
      <header className="flex items-center justify-center py-8">
        <div className="flex items-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-600 text-lg font-bold text-white">
            S
          </div>
          <span className="text-2xl font-bold tracking-tight text-neutral-900">
            SCR Platform
          </span>
        </div>
      </header>

      {/* Content */}
      <main className="mx-auto max-w-2xl px-6 pb-12">{children}</main>
    </div>
  );
}
