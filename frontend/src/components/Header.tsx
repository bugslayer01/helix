import { useStore } from "../store";
import { ThemeToggle } from "./ThemeToggle";
import { AccessibilityPanel } from "./AccessibilityPanel";

const STAGES: { id: string; label: string }[] = [
  { id: "handoff", label: "Verify" },
  { id: "understand", label: "Understand" },
  { id: "contest", label: "Contest" },
  { id: "outcome", label: "Outcome" },
];

export function Header() {
  const stage = useStore((s) => s.stage);
  const applicant = useStore((s) => s.applicantDisplay);
  const externalRef = useStore((s) => s.externalRef);
  const verdict = useStore((s) => s.decisionVerdict);

  const currentIdx = STAGES.findIndex((s) => s.id === (stage === "review" ? "contest" : stage));

  return (
    <header className="sticky top-0 z-40 border-b hairline bg-cream/92 backdrop-blur">
      <div className="mx-auto flex max-w-shell items-center justify-between gap-6 px-6 py-4 lg:gap-10 lg:px-8">
        <div className="flex items-center gap-3">
          <div aria-hidden className="flex h-8 w-8 items-center justify-center rounded-full bg-ink">
            <div className="h-2.5 w-2.5 rounded-full bg-cream" />
          </div>
          <div>
            <div className="display text-lg leading-none">Recourse</div>
            <div className="mt-1 text-[11px] uppercase leading-none tracking-[0.18em] text-ink-muted">
              Independent contestation portal
            </div>
          </div>
        </div>

        {applicant && (
          <nav aria-label="Contest progress" className="hidden md:flex items-center gap-3 text-[12px]">
            {STAGES.map((s, i) => {
              const active = i === currentIdx;
              const done = i < currentIdx;
              return (
                <div key={s.id} className={`flex items-center gap-2 ${active ? "text-ink" : done ? "text-ink-muted" : "text-ink-muted/60"}`}>
                  <span className={`h-5 w-5 grid place-items-center rounded-full text-[10px] mono ${active ? "bg-ink text-cream" : done ? "bg-good-soft text-good" : "bg-cream-soft"}`}>
                    {done ? "✓" : i + 1}
                  </span>
                  <span className="uppercase tracking-wider">{s.label}</span>
                </div>
              );
            })}
          </nav>
        )}

        <div className="flex items-center gap-3">
          {applicant && (
            <div className="hidden sm:block text-right">
              <div className="text-[13px] font-medium">{applicant}</div>
              <div className="mono text-[10.5px] text-ink-muted">
                {externalRef} · {verdict}
              </div>
            </div>
          )}
          <ThemeToggle />
          <AccessibilityPanel />
        </div>
      </div>
    </header>
  );
}
