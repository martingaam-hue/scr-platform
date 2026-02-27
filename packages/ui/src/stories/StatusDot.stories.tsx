import type { Meta, StoryObj } from "@storybook/react";
import { StatusDot } from "../components/status-dot";

const meta: Meta<typeof StatusDot> = {
  title: "Components/StatusDot",
  component: StatusDot,
  argTypes: {
    status: {
      control: "select",
      options: ["success", "warning", "error", "info", "neutral"],
    },
    pulse: { control: "boolean" },
  },
};
export default meta;
type Story = StoryObj<typeof StatusDot>;

export const Success: Story = { args: { status: "success", label: "Online" } };
export const Warning: Story = { args: { status: "warning", label: "Pending" } };
export const Error: Story = { args: { status: "error", label: "Offline" } };
export const Pulsing: Story = { args: { status: "success", label: "Live", pulse: true } };

export const AllStatuses: Story = {
  render: () => (
    <div className="flex flex-col gap-3">
      <StatusDot status="success" label="Active" />
      <StatusDot status="warning" label="Under Review" />
      <StatusDot status="error" label="Suspended" />
      <StatusDot status="info" label="Processing" />
      <StatusDot status="neutral" label="Inactive" />
    </div>
  ),
};
