/** @type {import('tailwindcss').Config} */

function token(name) {
  return `rgb(var(${name}) / <alpha-value>)`;
}

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        cream: {
          DEFAULT: token("--c-bg-rgb"),
          soft: token("--c-bg-soft-rgb"),
        },
        surface: token("--c-surface-rgb"),
        ink: {
          DEFAULT: token("--c-ink-rgb"),
          muted: token("--c-ink-muted-rgb"),
        },
        line: token("--c-line-rgb"),
        accent: {
          DEFAULT: token("--c-accent-rgb"),
          soft: token("--c-accent-soft-rgb"),
        },
        good: {
          DEFAULT: token("--c-good-rgb"),
          soft: token("--c-good-soft-rgb"),
        },
        bad: {
          DEFAULT: token("--c-bad-rgb"),
          soft: token("--c-bad-soft-rgb"),
        },
        warn: token("--c-warn-rgb"),
        brand: {
          DEFAULT: token("--c-brand-rgb"),
          soft: token("--c-brand-soft-rgb"),
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Fraunces", "Georgia", "serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      fontSize: {
        xs: ["0.8125rem", { lineHeight: "1.45" }],
        sm: ["0.9375rem", { lineHeight: "1.55" }],
        base: ["1.0625rem", { lineHeight: "1.65" }],
        lg: ["1.1875rem", { lineHeight: "1.6" }],
        xl: ["1.375rem", { lineHeight: "1.5" }],
        "2xl": ["1.75rem", { lineHeight: "1.35" }],
        "3xl": ["2.125rem", { lineHeight: "1.2" }],
        "4xl": ["2.75rem", { lineHeight: "1.1" }],
        "5xl": ["3.375rem", { lineHeight: "1.05" }],
      },
      boxShadow: {
        focus: "0 0 0 3px rgb(var(--c-focus-ring-rgb) / 0.35)",
        card: "0 1px 2px rgb(0 0 0 / 0.04)",
      },
      maxWidth: {
        shell: "1280px",
      },
    },
  },
  plugins: [],
};
