import { useEffect, useRef, useState } from "react";
import { applyA11y, loadA11y, saveA11y, type A11yPrefs, type A11yToggle } from "../lib/a11y";

interface ToggleSpec {
  key: A11yToggle;
  label: string;
  description: string;
}

const TOGGLES: ToggleSpec[] = [
  {
    key: "reduce-motion",
    label: "Reduce motion",
    description: "Stop page animations, transitions, and auto-scrolling.",
  },
  {
    key: "large-text",
    label: "Larger text",
    description: "Increase the base font size across the entire app.",
  },
  {
    key: "increased-spacing",
    label: "Increased spacing",
    description: "More letter- and line-spacing for easier reading.",
  },
  {
    key: "dyslexia-font",
    label: "Dyslexia-friendly font",
    description: "Switch to Atkinson Hyperlegible, designed for readability.",
  },
  {
    key: "underline-links",
    label: "Underline links & actions",
    description: "Add an underline to every clickable text link and ghost button.",
  },
  {
    key: "high-contrast",
    label: "High contrast",
    description: "Strengthen text, borders, and muted-text contrast.",
  },
];

export function AccessibilityPanel() {
  const [open, setOpen] = useState(false);
  const [prefs, setPrefs] = useState<A11yPrefs>(() => loadA11y());
  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);

  // Apply prefs on mount (in case the pre-paint script missed a key).
  useEffect(() => {
    applyA11y(prefs);
  }, [prefs]);

  // Click-outside and Escape to close.
  useEffect(() => {
    if (!open) return;
    const onDocClick = (e: MouseEvent) => {
      if (
        !panelRef.current?.contains(e.target as Node) &&
        !buttonRef.current?.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        buttonRef.current?.focus();
      }
    };
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const toggle = (key: A11yToggle) => {
    const next: A11yPrefs = { ...prefs, [key]: !prefs[key] };
    setPrefs(next);
    applyA11y(next);
    saveA11y(next);
  };

  const reset = () => {
    const cleared: A11yPrefs = {
      "reduce-motion": false,
      "large-text": false,
      "dyslexia-font": false,
      "underline-links": false,
      "increased-spacing": false,
      "high-contrast": false,
    };
    setPrefs(cleared);
    applyA11y(cleared);
    saveA11y(cleared);
  };

  const activeCount = (Object.values(prefs) as boolean[]).filter(Boolean).length;

  return (
    <div className="relative">
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label={`Accessibility options (${activeCount} active)`}
        title="Accessibility options"
        className="relative inline-flex h-9 w-9 items-center justify-center rounded-full border border-line bg-surface text-ink-muted transition-colors hover:text-ink focus-visible:outline-none"
      >
        <AccessibilityIcon />
        {activeCount > 0 && (
          <span
            aria-hidden
            className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-accent px-1 text-[9px] font-bold leading-none text-cream"
          >
            {activeCount}
          </span>
        )}
      </button>

      {open && (
        <div
          ref={panelRef}
          role="dialog"
          aria-label="Accessibility settings"
          className="absolute right-0 top-[calc(100%+8px)] z-50 w-[340px] rounded-xl border hairline bg-surface shadow-2xl"
        >
          <div className="border-b hairline px-5 pt-4 pb-3">
            <div className="text-[11px] uppercase tracking-[0.18em] text-ink-muted">
              Accessibility
            </div>
            <div className="mt-0.5 flex items-center justify-between">
              <div className="display text-lg leading-tight">Make Recourse fit you.</div>
              {activeCount > 0 && (
                <button
                  onClick={reset}
                  className="text-[12px] text-ink-muted underline hover:text-ink"
                >
                  Reset
                </button>
              )}
            </div>
            <p className="mt-1 text-[12px] text-ink-muted">
              Changes apply instantly and are remembered on this device.
            </p>
          </div>

          <ul role="list" className="py-2">
            {TOGGLES.map((spec) => (
              <li key={spec.key}>
                <Row
                  label={spec.label}
                  description={spec.description}
                  checked={prefs[spec.key]}
                  onToggle={() => toggle(spec.key)}
                />
              </li>
            ))}
          </ul>

          <div className="border-t hairline px-5 py-3 text-[11px] text-ink-muted">
            Your OS "reduce motion" preference is always respected.
          </div>
        </div>
      )}
    </div>
  );
}

function Row({
  label,
  description,
  checked,
  onToggle,
}: {
  label: string;
  description: string;
  checked: boolean;
  onToggle: () => void;
}) {
  const id = `a11y-${label.replace(/\s+/g, "-").toLowerCase()}`;
  return (
    <label
      htmlFor={id}
      className="flex cursor-pointer items-start gap-3 px-5 py-3 transition-colors hover:bg-cream-soft/60"
    >
      <div className="flex-1 min-w-0">
        <div className="text-[14px] font-medium leading-tight">{label}</div>
        <div className="mt-0.5 text-[12px] text-ink-muted">{description}</div>
      </div>
      <Switch id={id} checked={checked} onToggle={onToggle} label={label} />
    </label>
  );
}

function Switch({
  id,
  checked,
  onToggle,
  label,
}: {
  id: string;
  checked: boolean;
  onToggle: () => void;
  label: string;
}) {
  return (
    <button
      id={id}
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={onToggle}
      className={`relative mt-0.5 inline-flex h-6 w-11 shrink-0 items-center rounded-full border transition-colors ${checked ? "border-ink bg-ink" : "border-line bg-cream-soft"}`}
    >
      <span
        aria-hidden
        className={`inline-block h-4 w-4 transform rounded-full transition-transform ${checked ? "translate-x-6 bg-cream" : "translate-x-1 bg-ink-muted"}`}
      />
    </button>
  );
}

function AccessibilityIcon() {
  return (
    <svg
      width="17"
      height="17"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <circle cx="12" cy="4.5" r="1.5" fill="currentColor" stroke="none" />
      <path d="M7.5 8.5h9" />
      <path d="M12 8.5v5.5" />
      <path d="M9 14l3 0l3 0" />
      <path d="M9 14l-2 6M15 14l2 6" />
    </svg>
  );
}
