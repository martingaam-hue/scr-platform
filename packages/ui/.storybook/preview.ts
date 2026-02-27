import type { Preview } from "@storybook/react";
import "../src/globals.css";

const preview: Preview = {
  parameters: {
    controls: { matchers: { color: /(background|color)$/i, date: /Date$/i } },
    backgrounds: {
      default: "light",
      values: [
        { name: "light", value: "#FAFAFA" },
        { name: "dark", value: "#0A0F1A" },
      ],
    },
  },
};

export default preview;
