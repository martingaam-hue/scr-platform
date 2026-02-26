import type { Config } from "tailwindcss";
import baseConfig from "@scr/config/tailwind/base";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  presets: [baseConfig as Config],
  plugins: [],
};

export default config;
