import type { Meta, StoryObj } from "@storybook/react";
import { Badge, ScoreBadge } from "../components/badge";

const meta: Meta<typeof Badge> = {
  title: "Components/Badge",
  component: Badge,
  argTypes: {
    variant: {
      control: "select",
      options: ["success", "warning", "error", "info", "neutral", "gold"],
    },
  },
};
export default meta;
type Story = StoryObj<typeof Badge>;

export const Success: Story = { args: { variant: "success", children: "Active" } };
export const Warning: Story = { args: { variant: "warning", children: "Pending" } };
export const Error: Story = { args: { variant: "error", children: "Overdue" } };
export const Info: Story = { args: { variant: "info", children: "In Review" } };
export const Neutral: Story = { args: { variant: "neutral", children: "Draft" } };
export const Gold: Story = { args: { variant: "gold", children: "Premium" } };

export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-wrap gap-2">
      <Badge variant="success">Active</Badge>
      <Badge variant="warning">Pending</Badge>
      <Badge variant="error">Overdue</Badge>
      <Badge variant="info">In Review</Badge>
      <Badge variant="neutral">Draft</Badge>
      <Badge variant="gold">Premium</Badge>
    </div>
  ),
};

export const ScoreExamples: StoryObj = {
  render: () => (
    <div className="flex flex-wrap gap-3">
      <ScoreBadge score={15} />
      <ScoreBadge score={35} />
      <ScoreBadge score={55} />
      <ScoreBadge score={72} />
      <ScoreBadge score={88} />
      <ScoreBadge score={100} />
    </div>
  ),
};
