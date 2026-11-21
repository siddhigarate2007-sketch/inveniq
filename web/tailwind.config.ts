import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        tbo: {
          50: "#f0f7ff",
          100: "#e0effe",
          200: "#bae0fd",
          300: "#7cc7fc",
          400: "#36abf7",
          500: "#0b8fe8",
          600: "#0170c6",
          700: "#0259a0",
          800: "#064b83",
          900: "#0b3f6d",
          950: "#072848",
        },
        navy: {
          800: "#0f172a",
          850: "#0b1222",
          900: "#060b17",
          950: "#03060c",
        },
      },
    },
  },
  plugins: [],
};
export default config;
