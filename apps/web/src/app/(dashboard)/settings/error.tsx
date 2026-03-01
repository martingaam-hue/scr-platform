"use client";
import { SectionError } from "@/components/section-error";
export default function SettingsError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <SectionError error={error} reset={reset} section="settings" backPath="/settings" />;
}
