"use client";
import { SectionError } from "@/components/section-error";
export default function PortfolioError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <SectionError error={error} reset={reset} section="portfolio" />;
}
