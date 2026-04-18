import { useStore } from "../../store";
import type { Highlight } from "./highlights";

interface Props {
  highlights: Highlight[];
}

const DOT: Record<Highlight["severity"], string> = {
  critical: "bg-bad",
  warning: "bg-warn",
  suggestion: "bg-accent",
};

const LABEL: Record<Highlight["severity"], string> = {
  critical: "Critical",
  warning: "Warning",
  suggestion: "Suggestion",
};

function scrollToHighlight(id: string) {
  window.dispatchEvent(
    new CustomEvent("hiring:scroll-to-highlight", { detail: { id } }),
  );
}

export function HighlightRail({ highlights }: Props) {
  const flagged = useStore((s) => s.flaggedFields);
  const total = highlights.length;
  const contested = highlights.filter(
    (h) => h.flaggedFeature && flagged[h.flaggedFeature],
  ).length;

  return (
    <div className="rounded-xl border hairline bg-surface p-5">
      <div className="mb-4 flex items-baseline justify-between">
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-ink-muted">
            ATS highlights
          </div>
          <div className="display mt-1 text-lg">
            {total} {total === 1 ? "issue" : "issues"} ·{" "}
            <span className="text-accent">{contested} contested</span>
          </div>
        </div>
      </div>
      <ul className="space-y-2">
        {highlights.map((h) => {
          const isContested = h.flaggedFeature && !!flagged[h.flaggedFeature];
          return (
            <li
              key={h.id}
              role="button"
              tabIndex={0}
              onClick={() => scrollToHighlight(h.id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  scrollToHighlight(h.id);
                }
              }}
              className="group cursor-pointer rounded-lg border hairline bg-cream px-3 py-2.5 transition-colors hover:border-ink focus:outline-none focus-visible:shadow-focus"
            >
              <div className="flex items-start gap-2.5">
                <span
                  className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${DOT[h.severity]}`}
                  aria-hidden
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-[13px] font-medium text-ink">
                      {h.title}
                    </div>
                    <span className="pill shrink-0 text-[9px]">
                      {LABEL[h.severity]}
                    </span>
                  </div>
                  <div className="mt-1 truncate text-[11.5px] italic text-ink-muted">
                    “{h.quote}”
                  </div>
                  {isContested && (
                    <div className="mt-1.5 text-[10px] uppercase tracking-widest text-accent">
                      · contested
                    </div>
                  )}
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
