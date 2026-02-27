import type { Meta, StoryObj } from "@storybook/react";
import { Download, Plus, ArrowRight } from "lucide-react";
import { Button } from "../components/button";

const meta: Meta<typeof Button> = {
  title: "Components/Button",
  component: Button,
  argTypes: {
    variant: {
      control: "select",
      options: ["default", "secondary", "outline", "ghost", "destructive", "link"],
    },
    size: { control: "select", options: ["sm", "md", "lg", "icon"] },
    loading: { control: "boolean" },
    disabled: { control: "boolean" },
  },
};
export default meta;
type Story = StoryObj<typeof Button>;

export const Primary: Story = { args: { children: "Primary Button" } };

export const Secondary: Story = {
  args: { variant: "secondary", children: "Secondary" },
};

export const Outline: Story = {
  args: { variant: "outline", children: "Outline" },
};

export const Ghost: Story = {
  args: { variant: "ghost", children: "Ghost" },
};

export const Destructive: Story = {
  args: { variant: "destructive", children: "Delete" },
};

export const Loading: Story = {
  args: { loading: true, children: "Saving..." },
};

export const WithIconLeft: Story = {
  args: {
    children: "Download",
    iconLeft: <Download className="h-4 w-4" />,
  },
};

export const WithIconRight: Story = {
  args: {
    children: "Next",
    iconRight: <ArrowRight className="h-4 w-4" />,
  },
};

export const Small: Story = {
  args: { size: "sm", children: "Small" },
};

export const Large: Story = {
  args: { size: "lg", children: "Large Button" },
};

export const IconOnly: Story = {
  args: {
    size: "icon",
    variant: "outline",
    children: <Plus className="h-4 w-4" />,
  },
};

export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-wrap gap-3">
      <Button>Primary</Button>
      <Button variant="secondary">Secondary</Button>
      <Button variant="outline">Outline</Button>
      <Button variant="ghost">Ghost</Button>
      <Button variant="destructive">Destructive</Button>
      <Button variant="link">Link</Button>
    </div>
  ),
};
