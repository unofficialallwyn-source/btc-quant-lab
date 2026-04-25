import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: "hsl(var(--card))",
        border: "hsl(var(--border))",
        muted: "hsl(var(--muted))",
        ring: "hsl(var(--ring))",
        primary: "hsl(var(--primary))",
        secondary: "hsl(var(--secondary))"
      },
      boxShadow: {
        soft: "0 10px 30px -12px rgba(15,23,42,.22)",
      }
    },
  },
  plugins: [],
};

export default config;
