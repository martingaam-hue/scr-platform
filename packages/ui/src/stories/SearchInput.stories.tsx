import type { Meta, StoryObj } from "@storybook/react";
import { SearchInput } from "../components/search-input";

const meta: Meta<typeof SearchInput> = {
  title: "Components/SearchInput",
  component: SearchInput,
};
export default meta;

export const Default: StoryObj<typeof SearchInput> = {
  args: { placeholder: "Search projects..." },
};

export const WithValue: StoryObj<typeof SearchInput> = {
  args: { value: "solar energy", placeholder: "Search..." },
};
