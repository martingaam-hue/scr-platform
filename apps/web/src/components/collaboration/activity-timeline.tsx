"use client";

import React from "react";
import {
  Plus,
  Pencil,
  Trash2,
  MessageSquare,
  Upload,
  CheckCircle,
  Activity,
} from "lucide-react";
import { Timeline, Button, EmptyState, type TimelineItem } from "@scr/ui";
import { useEntityActivity, timeAgo } from "@/lib/collaboration";

interface ActivityTimelineProps {
  entityType: string;
  entityId: string;
}

function actionIcon(action: string): React.ReactNode {
  switch (action) {
    case "created":
      return <Plus className="h-4 w-4" />;
    case "updated":
    case "edited":
      return <Pencil className="h-4 w-4" />;
    case "deleted":
      return <Trash2 className="h-4 w-4" />;
    case "comment_added":
      return <MessageSquare className="h-4 w-4" />;
    case "uploaded":
      return <Upload className="h-4 w-4" />;
    case "resolved":
    case "completed":
      return <CheckCircle className="h-4 w-4" />;
    default:
      return <Activity className="h-4 w-4" />;
  }
}

export function ActivityTimeline({
  entityType,
  entityId,
}: ActivityTimelineProps) {
  const { data, isLoading, isFetching } = useEntityActivity(
    entityType,
    entityId
  );

  if (isLoading) {
    return (
      <div className="py-8 text-center text-sm text-neutral-400">
        Loading activity...
      </div>
    );
  }

  if (!data?.items.length) {
    return (
      <EmptyState
        icon={<Activity className="h-8 w-8" />}
        title="No activity yet"
        description="Activity will appear here as changes are made"
      />
    );
  }

  const timelineItems: TimelineItem[] = data.items.map((item) => ({
    id: item.id,
    icon: actionIcon(item.action),
    title: item.description,
    description: item.user_name
      ? `by ${item.user_name}`
      : undefined,
    timestamp: timeAgo(item.created_at),
  }));

  return (
    <div className="space-y-4">
      <Timeline items={timelineItems} />
      {data.total_pages > 1 && (
        <div className="flex justify-center">
          <Button variant="ghost" size="sm" disabled={isFetching}>
            Load more
          </Button>
        </div>
      )}
    </div>
  );
}
