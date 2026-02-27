import type { Meta, StoryObj } from "@storybook/react";
import { FolderOpen } from "lucide-react";
import { EmptyState } from "../components/empty-state";
import { Button } from "../components/button";

const meta: Meta<typeof EmptyState> = {
  title: "Components/EmptyState",
  component: EmptyState,
};
export default meta;

export const Default: StoryObj<typeof EmptyState> = {
  args: {
    icon: <FolderOpen className="h-8 w-8" />,
    title: "No projects yet",
    description: "Create your first project to get started with impact tracking.",
    action: <Button>Create Project</Button>,
  },
};

export const NoAction: StoryObj<typeof EmptyState> = {
  args: {
    title: "No results found",
    description: "Try adjusting your search or filter criteria.",
  },
};
