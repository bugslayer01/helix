import { useStore } from "../store";
import { Stepper } from "./Stepper";
import { ThemeToggle } from "./ThemeToggle";
import { AccessibilityPanel } from "./AccessibilityPanel";

export function Header() {
  const step = useStore((s) => s.step);
  const ev = useStore((s) => s.evaluation);
  const contestResult = useStore((s) => s.contestResult);
  const reviewResult = useStore((s) => s.reviewResult);
  const signOut = useStore((s) => s.signOut);

  const verbs = ev?.verbs;
  const displayName = ev?.display_name ?? "";

  let chipClass = "chip-denied";
  let chipLabel = verbs ? verbs.denied_label : "Denied";
  let confPct = ev ? Math.round(ev.confidence * 100) : 27;

  if (ev && ev.decision === "approved") {
    chipClass = "chip-approved";
    chipLabel = verbs?.approved_label ?? "Approved";
  }

  if (step === 4 && contestResult?.after && verbs) {
    if (contestResult.after.decision === "approved") {
      chipClass = "chip-approved";
      chipLabel = verbs.approved_label;
    } else {
      chipClass = "chip-denied";
      chipLabel = verbs.denied_label;
    }
    confPct = Math.round(contestResult.after.confidence * 100);
  }

  if (step === 4 && reviewResult) {
    chipClass = "border border-warn/30 bg-warn/15 text-warn";
    chipLabel = "Queued for review";
  }

  return (
    <header
      className="sticky top-0 z-40 border-b hairline bg-cream/92 backdrop-blur"
      role="banner"
    >
      <div className="mx-auto flex max-w-shell items-center justify-between gap-6 px-6 py-4 lg:gap-10 lg:px-8">
        <div className="flex shrink-0 items-center gap-3">
          <div
            aria-hidden
            className="flex h-8 w-8 items-center justify-center rounded-full bg-ink"
          >
            <div className="h-2.5 w-2.5 rounded-full bg-cream" />
          </div>
          <div>
            <div className="display text-lg leading-none">Recourse</div>
            <div className="mt-1 text-[11px] uppercase leading-none tracking-[0.18em] text-ink-muted">
              {displayName && `${displayName} · `}Case #{ev?.case_id ?? "?"}
            </div>
          </div>
        </div>

        <Stepper currentStep={step} />

        <div className="flex shrink-0 items-center gap-3">
          <span
            role="status"
            aria-live="polite"
            className={`rounded px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider transition-colors duration-500 ${chipClass}`}
          >
            {reviewResult ? chipLabel : `${chipLabel} · ${confPct}%`}
          </span>
          <ThemeToggle />
          <AccessibilityPanel />
          <button
            onClick={signOut}
            className="btn-ghost text-xs"
            aria-label="Sign out and return to login"
          >
            Sign out
          </button>
        </div>
      </div>
    </header>
  );
}
