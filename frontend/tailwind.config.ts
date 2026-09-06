import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  // Follow the OS/browser preference rather than an in-app toggle —
  // "dark mode is a nice touch but not required for v1" per spec.
  darkMode: "media",
  theme: {
    extend: {},
  },
  plugins: [],
};

export default config;
