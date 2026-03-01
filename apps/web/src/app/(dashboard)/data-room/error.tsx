"use client";
import { SectionError } from "@/components/section-error";
export default function DataRoomError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <SectionError error={error} reset={reset} section="data room" backPath="/data-room" />;
}
