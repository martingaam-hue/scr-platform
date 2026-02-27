import type { Meta, StoryObj } from "@storybook/react";
import { FileText, Users, CheckCircle, AlertTriangle } from "lucide-react";
import { Timeline } from "../components/timeline";

const meta: Meta<typeof Timeline> = {
  title: "Components/Timeline",
  component: Timeline,
};
export default meta;

export const Default: StoryObj<typeof Timeline> = {
  args: {
    items: [
      {
        id: "1",
        icon: <CheckCircle className="h-4 w-4 text-success-500" />,
        title: "Due diligence completed",
        description: "All required documents verified by legal team.",
        timestamp: "2 hours ago",
      },
      {
        id: "2",
        icon: <FileText className="h-4 w-4" />,
        title: "Financial model uploaded",
        description: "Q4 projections added by analyst.",
        timestamp: "Yesterday",
      },
      {
        id: "3",
        icon: <Users className="h-4 w-4" />,
        title: "Team meeting scheduled",
        timestamp: "3 days ago",
      },
      {
        id: "4",
        icon: <AlertTriangle className="h-4 w-4 text-warning-500" />,
        title: "Risk flag raised",
        description: "Currency exposure exceeds threshold.",
        timestamp: "1 week ago",
      },
    ],
  },
};
