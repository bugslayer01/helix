export type A11yToggle =
  | "reduce-motion"
  | "large-text"
  | "dyslexia-font"
  | "underline-links"
  | "increased-spacing"
  | "high-contrast";

export interface A11yPrefs {
  "reduce-motion": boolean;
  "large-text": boolean;
  "dyslexia-font": boolean;
  "underline-links": boolean;
  "increased-spacing": boolean;
  "high-contrast": boolean;
}

const STORAGE_KEY = "recourse-a11y";

const DEFAULT: A11yPrefs = {
  "reduce-motion": false,
  "large-text": false,
  "dyslexia-font": false,
  "underline-links": false,
  "increased-spacing": false,
  "high-contrast": false,
};

export function loadA11y(): A11yPrefs {
  if (typeof window === "undefined") return { ...DEFAULT };
  try {
    const stored = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? "{}");
    return { ...DEFAULT, ...stored };
  } catch {
    return { ...DEFAULT };
  }
}

export function saveA11y(prefs: A11yPrefs): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
}

export function applyA11y(prefs: A11yPrefs): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  (Object.keys(prefs) as A11yToggle[]).forEach((key) => {
    root.classList.toggle(key, prefs[key]);
  });
}
