import type { Meta, StoryObj } from "@storybook/react";
import { Avatar, AvatarGroup } from "../components/avatar";

const meta: Meta<typeof Avatar> = {
  title: "Components/Avatar",
  component: Avatar,
  argTypes: {
    size: { control: "select", options: ["sm", "md", "lg", "xl"] },
  },
};
export default meta;

export const WithImage: StoryObj<typeof Avatar> = {
  args: { src: "https://i.pravatar.cc/150?img=3", alt: "Jane Doe", size: "md" },
};

export const Fallback: StoryObj<typeof Avatar> = {
  args: { alt: "John Smith", size: "md" },
};

export const AllSizes: StoryObj = {
  render: () => (
    <div className="flex items-center gap-3">
      <Avatar alt="Small" size="sm" />
      <Avatar alt="Medium" size="md" />
      <Avatar alt="Large" size="lg" />
      <Avatar alt="XLarge" size="xl" />
    </div>
  ),
};

export const Group: StoryObj = {
  render: () => (
    <AvatarGroup
      avatars={[
        { src: "https://i.pravatar.cc/150?img=1", alt: "Alice" },
        { src: "https://i.pravatar.cc/150?img=2", alt: "Bob" },
        { src: "https://i.pravatar.cc/150?img=3", alt: "Carol" },
        { alt: "Dave" },
        { alt: "Eve" },
        { alt: "Frank" },
      ]}
      max={4}
    />
  ),
};
