"use client";

import { useParams } from "next/navigation";
import { SignalScoreDetail } from "@/components/signal-score/signal-score-detail";

export default function SignalScorePage() {
  const { id } = useParams<{ id: string }>();
  return (
    <SignalScoreDetail
      projectId={id}
      backHref={`/projects/${id}`}
    />
  );
}
