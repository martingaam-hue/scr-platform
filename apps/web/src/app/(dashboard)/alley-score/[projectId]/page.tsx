"use client";

import { useParams } from "next/navigation";
import { SignalScoreDetail } from "@/components/signal-score/signal-score-detail";

export default function ProjectScoreDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  return (
    <SignalScoreDetail
      projectId={projectId}
      backHref="/alley-score"
      backLabel="Back to Signal Score"
    />
  );
}
