import type { Config } from "tailwindcss";

const config: Partial<Config> = {
  theme: {
    extend: {
      colors: {
        // SCR brand — Primary (dark navy)
        primary: {
          50: "#E8EEF4",
          100: "#C5D4E3",
          200: "#9FB7D0",
          300: "#799ABD",
          400: "#5C84AE",
          500: "#2C5F8A", // primary-light
          600: "#1B3A5C", // main brand
          700: "#15304D",
          800: "#0D2137", // primary-dark
          900: "#071525",
          DEFAULT: "#1B3A5C",
        },
        // SCR brand — Secondary (gold)
        secondary: {
          50: "#FBF6E8",
          100: "#F3E8C4",
          200: "#EBD99D",
          300: "#E2CA76",
          400: "#D4B76A", // secondary-light
          500: "#C5A34E", // main brand gold
          600: "#B89345",
          700: "#A67F3B",
          800: "#946C31",
          900: "#754D20",
          DEFAULT: "#C5A34E",
        },
        // Semantic — Success (green)
        success: {
          50: "#E6F4E7",
          100: "#C1E4C3",
          200: "#98D39C",
          300: "#6EC175",
          400: "#4EB457",
          500: "#2E7D32",
          600: "#29712D",
          700: "#226226",
          800: "#1B5320",
          900: "#103814",
          DEFAULT: "#2E7D32",
        },
        // Semantic — Warning (orange)
        warning: {
          50: "#FFF3E0",
          100: "#FFE0B2",
          200: "#FFCC80",
          300: "#FFB74D",
          400: "#FFA726",
          500: "#F57C00",
          600: "#EF6C00",
          700: "#E65100",
          800: "#BF360C",
          900: "#8B2500",
          DEFAULT: "#F57C00",
        },
        // Semantic — Error (red)
        error: {
          50: "#FFEBEE",
          100: "#FFCDD2",
          200: "#EF9A9A",
          300: "#E57373",
          400: "#EF5350",
          500: "#C62828",
          600: "#B71C1C",
          700: "#9B1515",
          800: "#7F1010",
          900: "#5D0A0A",
          DEFAULT: "#C62828",
        },
        // Neutral palette
        neutral: {
          50: "#FAFAFA",
          100: "#F5F5F5",
          200: "#EEEEEE",
          300: "#E0E0E0",
          400: "#BDBDBD",
          500: "#9E9E9E",
          600: "#757575",
          700: "#616161",
          800: "#424242",
          900: "#212121",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        heading: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      borderRadius: {
        lg: "0.625rem",
        md: "0.5rem",
        sm: "0.375rem",
      },
      fontSize: {
        "2xs": ["0.625rem", { lineHeight: "0.875rem" }],
      },
    },
  },
};

export default config;
