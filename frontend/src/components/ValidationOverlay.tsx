import { useEffect, useRef } from "react";
import gsap from "gsap";
import { useStore } from "../store";

export function ValidationOverlay() {
  const flow = useStore((s) => s.contestFlow);
  const ev = useStore((s) => s.evaluation);
  const resetContestFlow = useStore((s) => s.resetContestFlow);
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!rootRef.current) return;
    if (flow.phase === "idle" || flow.phase === "applied") return;
    const ctx = gsap.context(() => {
      gsap.fromTo(
        "[data-validation-row]",
        { opacity: 0, y: 8 },
        { opacity: 1, y: 0, duration: 0.4, ease: "power2.out", stagger: 0.08 },
      );
    }, rootRef);
    return () => ctx.revert();
  }, [flow.phase, flow.proposals.length]);

  if (flow.phase === "idle" || flow.phase === "applied") return null;
  if (!ev) return null;

  const schemaByFeature = new Map(
    ev.feature_schema.map((s) => [s.feature, s]),
  );

  const phaseCopy = {
    proposing: {
      title: "Submitting for validation…",
      sub: "Preparing your evidence package.",
    },
    validating: {
      title: "Extracting values from your documents",
      sub: "Each document is verified and the updated value is derived from it. You never type the number — we read it from the source.",
    },
    applying: {
      title: "Applying the extracted values",
      sub: "All documents verified. Running the model on the updated feature vector.",
    },
    rejected: {
      title: "Evidence was rejected",
      sub: "No corrections were applied. Review the notes below and resubmit with fresh proof.",
    },
    error: {
      title: "Something went wrong",
      sub: flow.message ?? "The validator couldn't reach a verdict. Try again shortly.",
    },
  }[flow.phase as Exclude<typeof flow.phase, "idle" | "applied">];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="validation-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/50 backdrop-blur-sm px-4"
      ref={rootRef}
    >
      <div className="w-full max-w-xl rounded-2xl border hairline bg-surface shadow-2xl">
        <header className="border-b hairline px-6 py-5">
          <div className="mb-2 flex items-center gap-2 text-[11px] uppercase tracking-[0.2em] text-ink-muted">
            <span className="relative flex h-2 w-2">
              <span
                className={`absolute inline-flex h-full w-full rounded-full opacity-60 ${flow.phase === "rejected" || flow.phase === "error" ? "bg-bad" : "bg-good"} animate-ping`}
              />
              <span
                className={`relative inline-flex h-2 w-2 rounded-full ${flow.phase === "rejected" || flow.phase === "error" ? "bg-bad" : "bg-good"}`}
              />
            </span>
            Evidence validation
          </div>
          <h2 id="validation-title" className="display text-2xl">
            {phaseCopy.title}
          </h2>
          <p className="mt-2 text-sm text-ink-muted">{phaseCopy.sub}</p>
        </header>

        <ul className="divide-y divide-line px-6 py-4" role="list">
          {flow.proposals.map((p) => {
            const schema = schemaByFeature.get(p.feature);
            const label = schema?.display_name ?? p.feature;
            const isValidated = p.status === "validated";
            const isRejected = p.status === "rejected";
            const isWorking = p.status === "validating";
            return (
              <li
                key={p.feature}
                data-validation-row
                className="flex items-center gap-4 py-3"
              >
                <ValidationIcon state={p.status} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium truncate">{label}</span>
                    {isValidated && (
                      <span className="pill pill-ok">Validated</span>
                    )}
                    {isRejected && (
                      <span className="pill pill-concern">Rejected</span>
                    )}
                    {isWorking && (
                      <span className="pill pill-warn">Checking</span>
                    )}
                  </div>
                  <div className="text-xs text-ink-muted mt-0.5">
                    {isRejected && p.validation_note
                      ? p.validation_note
                      : isValidated && p.resolved_value !== null
                        ? `Resolved value · ${p.resolved_value}`
                        : "Verifying document chain…"}
                  </div>
                </div>
              </li>
            );
          })}
        </ul>

        {(flow.phase === "rejected" || flow.phase === "error") && (
          <footer className="border-t hairline px-6 py-4 flex justify-end">
            <button onClick={resetContestFlow} className="btn-primary">
              Close and retry
            </button>
          </footer>
        )}
      </div>
    </div>
  );
}

function ValidationIcon({ state }: { state: "validating" | "validated" | "rejected" }) {
  if (state === "validated") {
    return (
      <span
        aria-hidden
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-good/15 text-good"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M2 7.5L5.5 11L12 3.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
    );
  }
  if (state === "rejected") {
    return (
      <span
        aria-hidden
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-bad/15 text-bad"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M3 3L11 11M11 3L3 11" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
      </span>
    );
  }
  return (
    <span
      aria-hidden
      className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border hairline"
    >
      <span className="h-3 w-3 rounded-full border-2 border-ink-muted border-t-transparent animate-spin" />
    </span>
  );
}
