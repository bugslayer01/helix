/** @type {import('tailwindcss').Config} */

// Each colour is exposed as an `rgb(var(...) / <alpha-value>)` token so
// Tailwind's `/opacity` syntax (e.g. `bg-accent/10`, `border-good/40`)
// keeps working — while the underlying values still switch via CSS-var
// theme tokens in index.css. Keep --c-*-rgb triples in sync with index.css.
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
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Fraunces", "Georgia", "serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      fontSize: {
        xs: ["0.8125rem", { lineHeight: "1.45" }],   // 13px
        sm: ["0.9375rem", { lineHeight: "1.55" }],   // 15px
        base: ["1.0625rem", { lineHeight: "1.65" }], // 17px
        lg: ["1.1875rem", { lineHeight: "1.6" }],    // 19px
        xl: ["1.375rem", { lineHeight: "1.5" }],     // 22px
        "2xl": ["1.75rem", { lineHeight: "1.35" }],  // 28px
        "3xl": ["2.125rem", { lineHeight: "1.2" }],  // 34px
        "4xl": ["2.75rem", { lineHeight: "1.1" }],   // 44px
        "5xl": ["3.375rem", { lineHeight: "1.05" }], // 54px
        "6xl": ["4rem", { lineHeight: "1.02" }],     // 64px
      },
      boxShadow: {
        focus: "0 0 0 3px rgb(var(--c-focus-ring-rgb) / 0.35)",
        ring: "0 0 0 5px rgb(var(--c-focus-ring-rgb) / 0.2)",
        card: "0 1px 2px rgb(0 0 0 / 0.04)",
        "card-dark": "0 1px 2px rgb(0 0 0 / 0.5)",
      },
      maxWidth: {
        shell: "1400px",
      },
    },
  },
  plugins: [],
};
