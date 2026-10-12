/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: ["class", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        page: "var(--page)",
        well: "var(--well)",
        raised: "var(--raised)",
        line: "var(--line)",
        ink: "var(--ink)",
        muted: "var(--muted)",
        talking: "var(--talking)",
        scenic: "var(--scenic)",
        agent: "var(--agent)",
        "agent-ink": "var(--agent-ink)",
        danger: "var(--danger)",
        paper: "var(--paper)",
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        sheet: "0 24px 64px rgba(0,0,0,0.45)",
      },
    },
  },
  plugins: [],
};
