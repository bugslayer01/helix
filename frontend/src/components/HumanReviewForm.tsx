import { useStore } from "../store";

const MAX = 2000;

// Strip angle brackets and null bytes defensively — the statement is relayed
// verbatim to a human reviewer, so we don't want hidden markup or control chars.
function sanitize(raw: string): string {
  return raw.replace(/[<>\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "");
}

export function HumanReviewForm() {
  const ev = useStore((s) => s.evaluation);
  const text = useStore((s) => s.humanReviewText);
  const setText = useStore((s) => s.setHumanReviewText);
  const reason = useStore((s) => s.humanReviewReason);
  const setReason = useStore((s) => s.setHumanReviewReason);
  const runHumanReview = useStore((s) => s.runHumanReview);
  const loading = useStore((s) => s.loading);
  const goto = useStore((s) => s.goto);

  if (!ev) return null;

  const reasons = ev.path_reasons.review;
  const citations = ev.legal_citations;
  const canSubmit = reason.length > 0 && text.trim().length > 10;

  return (
    <div className="rounded-xl border hairline bg-surface p-[22px]">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <div className="mb-1 text-[10px] uppercase tracking-widest text-accent">
            Path 03 · Human review
          </div>
          <h2 className="display text-2xl">{ev.verbs.review_title}</h2>
        </div>
      </div>

      <div className="mb-5 rounded-lg border border-warn/30 bg-warn/5 px-4 py-3 text-[13px] leading-relaxed text-ink">
        <div className="mb-1 flex items-center gap-2 text-[10px] uppercase tracking-wider text-warn">
          <span className="h-1.5 w-1.5 rounded-full bg-warn" />
          No automatic re-evaluation
        </div>
        {ev.verbs.review_sub} This is your right under{" "}
        {citations.slice(0, 2).join(" and ")}.
      </div>

      <div className="mb-5">
        <label
          htmlFor="hr-reason"
          className="mb-2 block text-[10px] uppercase tracking-[0.2em] text-ink-muted"
        >
          What's your concern? <span className="text-accent">*</span>
        </label>
        <select
          id="hr-reason"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          className="w-full rounded-md border hairline bg-surface px-3 py-2.5 text-sm focus:border-ink focus:shadow-focus focus:outline-none"
        >
          <option value="">— Select a reason —</option>
          {reasons.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </select>
      </div>

      <div className="mb-5">
        <label
          htmlFor="hr-text"
          className="mb-2 block text-[10px] uppercase tracking-[0.2em] text-ink-muted"
        >
          Your statement for the reviewer
        </label>
        <textarea
          id="hr-text"
          value={text}
          onChange={(e) => setText(sanitize(e.target.value).slice(0, MAX))}
          placeholder="Describe what you think went wrong. A human will read this — not the model."
          rows={7}
          aria-describedby="hr-text-counter"
          maxLength={MAX}
          className="w-full resize-y rounded-md border hairline bg-surface px-3 py-2.5 text-sm leading-relaxed focus:border-ink focus:shadow-focus focus:outline-none"
        />
        <div className="mt-1 flex items-center justify-between text-[11px] text-ink-muted">
          <span>Your words go to a person. They are not interpreted by any model.</span>
          <span id="hr-text-counter" className="mono tabular-nums" aria-live="polite">
            {text.length} / {MAX}
          </span>
        </div>
      </div>

      <div className="flex items-center justify-between border-t hairline pt-5">
        <div className="text-xs text-ink-muted">
          Submitting queues this case. A reviewer will email you.
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => goto(2)} className="btn-ghost">
            Cancel
          </button>
          <button
            disabled={!canSubmit || loading === "review"}
            onClick={() => runHumanReview()}
            className="btn-primary"
          >
            {loading === "review" ? (
              <>
                <span className="spinner" />
                <span>Submitting…</span>
              </>
            ) : (
              "Submit to reviewer →"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
