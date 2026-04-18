import { useEffect, useId, useRef, useState } from "react";
import { useStore } from "../../store";

export type HighlightSeverity = "critical" | "warning" | "suggestion";

interface Props {
  id: string;
  severity: HighlightSeverity;
  tooltip: string;
  title?: string;
  flaggedFeature?: string;
  children: React.ReactNode;
}

const SEVERITY_COLOR: Record<HighlightSeverity, string> = {
  critical: "#B5412B",
  warning: "#9A6B1F",
  suggestion: "#B5412B",
};

const SEVERITY_LABEL: Record<HighlightSeverity, string> = {
  critical: "Critical",
  warning: "Warning",
  suggestion: "Suggestion",
};

const SEVERITY_PILL: Record<HighlightSeverity, string> = {
  critical: "border-bad/40 bg-bad/10 text-bad",
  warning: "border-warn/40 bg-warn/10 text-warn",
  suggestion: "border-accent/40 bg-accent/10 text-accent",
};

function dispatchFocusFormKey(formKey: string) {
  window.dispatchEvent(
    new CustomEvent("hiring:focus-form-key", { detail: { formKey } }),
  );
}

export function HighlightSpan({
  id,
  severity,
  tooltip,
  title,
  flaggedFeature,
  children,
}: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement | null>(null);
  const popId = useId();
  const toggleFlag = useStore((s) => s.toggleFlag);
  const flagged = useStore((s) => s.flaggedFields);
  const isFlagged = flaggedFeature ? !!flagged[flaggedFeature] : false;

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!ref.current) return;
      if (e.target instanceof Node && ref.current.contains(e.target)) return;
      setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("mousedown", onDown);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  useEffect(() => {
    const onScrollTo = (e: Event) => {
      const ce = e as CustomEvent<{ id: string }>;
      if (ce.detail?.id !== id) return;
      const el = ref.current;
      if (!el) return;
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.focus();
      el.classList.add("is-pulsing");
      setTimeout(() => el.classList.remove("is-pulsing"), 900);
    };
    window.addEventListener("hiring:scroll-to-highlight", onScrollTo);
    return () =>
      window.removeEventListener("hiring:scroll-to-highlight", onScrollTo);
  }, [id]);

  const onKeyDown = (e: React.KeyboardEvent<HTMLSpanElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      setOpen((v) => !v);
    }
  };

  const onContest = () => {
    if (flaggedFeature && !isFlagged) {
      toggleFlag(flaggedFeature);
    }
    if (flaggedFeature) dispatchFocusFormKey(flaggedFeature);
    setOpen(false);
  };

  const color = SEVERITY_COLOR[severity];

  return (
    <span
      ref={ref}
      id={`hl-${id}`}
      role="button"
      tabIndex={0}
      aria-describedby={open ? popId : undefined}
      aria-expanded={open}
      onClick={(e) => {
        e.stopPropagation();
        setOpen((v) => !v);
      }}
      onKeyDown={onKeyDown}
      onFocus={() => setOpen(true)}
      onMouseEnter={() => setOpen(true)}
      className={`relative cursor-pointer rounded-sm px-0.5 transition-colors outline-none focus-visible:shadow-focus ${
        isFlagged ? "bg-accent/10" : "hover:bg-cream-soft"
      }`}
      style={{
        textDecoration: "underline",
        textDecorationStyle: "wavy",
        textDecorationColor: color,
        textDecorationThickness: "2px",
        textUnderlineOffset: "3px",
      }}
      data-hl={id}
      data-hl-severity={severity}
    >
      {children}
      {open && (
        <span
          id={popId}
          role="dialog"
          aria-live="polite"
          onClick={(e) => e.stopPropagation()}
          className="absolute top-full left-0 z-30 mt-2 block w-max max-w-sm rounded-lg border hairline bg-surface p-4 text-left shadow-lg"
          style={{ minWidth: 280 }}
        >
          <span className="mb-2 flex items-center gap-2">
            <span
              className={`pill ${SEVERITY_PILL[severity]}`}
              style={{ textTransform: "uppercase" }}
            >
              {SEVERITY_LABEL[severity]}
            </span>
            {isFlagged && (
              <span className="pill pill-ok">Contested</span>
            )}
          </span>
          {title && (
            <span className="mb-1 block text-sm font-medium text-ink">
              {title}
            </span>
          )}
          <span className="mb-3 block text-[13px] leading-relaxed text-ink-muted">
            {tooltip}
          </span>
          <span className="flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="btn-ghost"
            >
              Dismiss
            </button>
            <button
              type="button"
              onClick={onContest}
              className="btn-primary"
              style={{ padding: "6px 12px", fontSize: 12 }}
            >
              {flaggedFeature
                ? isFlagged
                  ? "Open in form →"
                  : "Contest this"
                : "Flag to recruiter"}
            </button>
          </span>
        </span>
      )}
    </span>
  );
}
