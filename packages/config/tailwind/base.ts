import type { Config } from "tailwindcss";

const config: Partial<Config> = {
  theme: {
    extend: {
      colors: {
        // SCR brand colors
        primary: {
          50: "#E8EEF4",
          100: "#C5D4E3",
          200: "#9FB7D0",
          300: "#799ABD",
          400: "#5C84AE",
          500: "#3F6E9F",
          600: "#365E8A",
          700: "#2B4D71",
          800: "#1B3A5C", // Main brand navy
          900: "#0D2540",
          DEFAULT: "#1B3A5C",
        },
        secondary: {
          50: "#FBF6E8",
          100: "#F3E8C4",
          200: "#EBD99D",
          300: "#E2CA76",
          400: "#DCBF58",
          500: "#C5A34E", // Main brand gold
          600: "#B89345",
          700: "#A67F3B",
          800: "#946C31",
          900: "#754D20",
          DEFAULT: "#C5A34E",
        },
        accent: {
          50: "#E6F4E7",
          100: "#C1E4C3",
          200: "#98D39C",
          300: "#6EC175",
          400: "#4EB457",
          500: "#2E7D32", // Main ESG green
          600: "#29712D",
          700: "#226226",
          800: "#1B5320",
          900: "#103814",
          DEFAULT: "#2E7D32",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        heading: ["Inter", "system-ui", "sans-serif"],
      },
      borderRadius: {
        lg: "0.625rem",
        md: "0.5rem",
        sm: "0.375rem",
      },
    },
  },
};

export default config;
