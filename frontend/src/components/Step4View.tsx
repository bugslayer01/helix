import { useEffect, useRef } from "react";
import gsap from "gsap";
import { useStore } from "../store";
import type { ContestResult, ReviewResult } from "../types";

export function Step4View() {
  const contestResult = useStore((s) => s.contestResult);
  const reviewResult = useStore((s) => s.reviewResult);

  if (reviewResult) return <HumanReviewConfirmation result={reviewResult} />;
  if (contestResult) return <DeltaOutcomeView contest={contestResult} />;
  return null;
}

function DeltaOutcomeView({ contest }: { contest: ContestResult }) {
  const ev = useStore((s) => s.evaluation);
  const goto = useStore((s) => s.goto);
  const signOut = useStore((s) => s.signOut);

  const ref = useRef<HTMLDivElement | null>(null);
  const confRef = useRef<HTMLSpanElement | null>(null);
  const chipRef = useRef<HTMLSpanElement | null>(null);

  const before = contest.before;
  const after = contest.after ?? contest.before;
  const scale = 60;

  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.fromTo(
        "[data-fade]",
        { opacity: 0, y: 14 },
        { opacity: 1, y: 0, duration: 0.55, ease: "power2.out", stagger: 0.06 },
      );

      if (!contest.delta) return;
      const tl = gsap.timeline({ delay: 0.25 });

      contest.delta.feature_deltas.forEach((delta, i) => {
        const bar = ref.current?.querySelector<HTMLDivElement>(
          `[data-bar-key="${cssSafe(delta.feature)}"]`,
        );
        const val = ref.current?.querySelector<HTMLDivElement>(
          `[data-val-key="${cssSafe(delta.feature)}"]`,
        );
        if (!bar || !val) return;

        const newAbs = Math.abs(delta.new_contribution);
        const newIsNeg = delta.new_contribution < 0;
        const newWidth = Math.min(Math.max(newAbs * scale, 2), 48);
        const newLeft = newIsNeg ? 50 - newWidth : 50;
        const color =
          Math.abs(delta.new_contribution) < 1e-6
            ? "#6B6359"
            : newIsNeg
              ? "#B5412B"
              : "#4D6B4A";

        tl.to(
          bar,
          {
            left: `${newLeft}%`,
            width: `${newWidth}%`,
            backgroundColor: color,
            duration: 1.0,
            ease: "power3.inOut",
          },
          i * 0.06,
        );

        const proxy = { v: delta.old_contribution };
        tl.to(
          proxy,
          {
            v: delta.new_contribution,
            duration: 1.0,
            ease: "power3.inOut",
            onUpdate: () => {
              const v = proxy.v;
              const abs = Math.abs(v).toFixed(2);
              val.textContent = `${v >= 0 ? "+" : "−"}${abs}`;
              val.style.color = v >= 0 ? "#4D6B4A" : "#B5412B";
            },
          },
          i * 0.06,
        );
      });

      if (chipRef.current && before.decision !== after.decision) {
        tl.to(
          chipRef.current,
          {
            keyframes: [
              { rotationY: 90, duration: 0.18, ease: "power2.in" },
              { rotationY: 0, duration: 0.22, ease: "power2.out" },
            ],
            onStart: () => {
              setTimeout(() => {
                if (!chipRef.current || !ev) return;
                if (after.decision === "approved") {
                  chipRef.current.classList.remove("chip-denied");
                  chipRef.current.classList.add("chip-approved");
                  chipRef.current.textContent = ev.verbs.approved_label;
                } else {
                  chipRef.current.classList.remove("chip-approved");
                  chipRef.current.classList.add("chip-denied");
                  chipRef.current.textContent = ev.verbs.denied_label;
                }
              }, 180);
            },
          },
          0.55,
        );
      }

      if (confRef.current) {
        const proxy = { v: before.confidence * 100 };
        tl.to(
          proxy,
          {
            v: after.confidence * 100,
            duration: 0.65,
            ease: "power3.out",
            onUpdate: () => {
              if (confRef.current) confRef.current.textContent = String(Math.round(proxy.v));
            },
          },
          0.8,
        );
      }

      tl.to(
        "[data-summary]",
        { opacity: 1, y: 0, duration: 0.4, ease: "power2.out" },
        1.3,
      );
    }, ref);
    return () => ctx.revert();
  }, [contest, ev, before.decision, after.decision, before.confidence, after.confidence]);

  if (!ev) return null;
  const verbs = ev.verbs;
  const flipped = before.decision !== after.decision;
  const initialChipClass = before.decision === "approved" ? "chip-approved" : "chip-denied";
  const initialChipText = before.decision === "approved" ? verbs.approved_label : verbs.denied_label;
  const updated = contest.delta?.feature_deltas.filter((d) => Math.abs(d.contribution_delta) > 0.001).length ?? 0;
  const confDeltaPp = Math.round((contest.delta?.confidence_change ?? 0) * 100);

  return (
    <section ref={ref}>
      <div className="mb-2 text-xs uppercase tracking-[0.2em] text-ink-muted" data-fade>
        Step 4 of 4
      </div>
      <h1 className="display mb-6 text-6xl leading-[1.02]" data-fade>
        {flipped ? verbs.outcome_title_flipped : verbs.outcome_title_same}
      </h1>
      <p className="mb-10 max-w-2xl text-lg leading-relaxed text-ink-muted" data-fade>
        {flipped
          ? `With the corrected figures, the model's verdict flipped. Here's how each factor moved.`
          : `Even with your updates, the factors didn't move the decision across the threshold. Here's what did shift.`}
      </p>

      <div className="mb-12 flex items-center gap-6 border-y hairline py-6" data-fade>
        <span
          ref={chipRef}
          className={`${initialChipClass} rounded px-3 py-1 text-xs font-semibold uppercase tracking-wider`}
          style={{ transformStyle: "preserve-3d" }}
        >
          {initialChipText}
        </span>
        <div className="flex items-baseline gap-2">
          <span className="display text-4xl tabular-nums">
            <span ref={confRef}>{Math.round(before.confidence * 100)}</span>
            <span className="text-2xl">%</span>
          </span>
          <span className="text-sm text-ink-muted">confidence</span>
        </div>
        <div className="mono ml-auto text-xs text-ink-muted">
          {confDeltaPp >= 0 ? "+" : ""}{confDeltaPp}pp · {contest.audit_hash.slice(0, 14)}…
        </div>
      </div>

      <div className="mb-12">
        <div className="mb-5 flex items-center justify-between" data-fade>
          <h2 className="display text-2xl">How factors moved</h2>
          <div className="text-xs text-ink-muted">Before → After</div>
        </div>

        <div className="relative" data-fade>
          <div className="axis absolute top-0 bottom-0 left-1/2" />
          <div className="space-y-3 py-4">
            {contest.delta?.feature_deltas.map((d) => {
              const oldAbs = Math.abs(d.old_contribution);
              const initW = Math.min(Math.max(oldAbs * scale, 2), 48);
              const initL = d.old_contribution < 0 ? 50 - initW : 50;
              const initC = d.old_contribution < 0 ? "#B5412B" : "#4D6B4A";
              const isProtected = ev.shap_values.find((s) => s.feature === d.feature)?.protected;
              return (
                <div
                  key={d.feature}
                  className="grid grid-cols-[200px_1fr_80px] items-center gap-4"
                >
                  <div className="flex items-center gap-2 text-sm">
                    <span className="truncate">{d.displayName}</span>
                    {isProtected && <span className="lock-dot" aria-hidden />}
                  </div>
                  <div className="relative flex h-8 items-center">
                    <div
                      data-bar-key={cssSafe(d.feature)}
                      className="absolute h-3.5 rounded-sm"
                      style={{
                        left: `${initL}%`,
                        width: `${initW}%`,
                        backgroundColor: initC,
                      }}
                    />
                  </div>
                  <div
                    data-val-key={cssSafe(d.feature)}
                    className="mono text-right text-sm tabular-nums"
                    style={{
                      color: d.old_contribution >= 0 ? "#4D6B4A" : "#B5412B",
                    }}
                  >
                    {d.old_contribution >= 0 ? "+" : "−"}
                    {oldAbs.toFixed(2)}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div
          className="mt-6 text-sm text-ink-muted"
          data-summary
          style={{ opacity: 0, transform: "translateY(6px)" }}
        >
          {updated} field{updated === 1 ? "" : "s"} updated · decision{" "}
          {flipped ? "changed" : "unchanged"} from{" "}
          <span className="font-medium text-ink">
            {before.decision === "approved" ? verbs.approved_label : verbs.denied_label}
          </span>{" "}
          to{" "}
          <span className={`font-medium ${after.decision === "approved" ? "text-good" : "text-bad"}`}>
            {after.decision === "approved" ? verbs.approved_label : verbs.denied_label}
          </span>{" "}
          · confidence{" "}
          <span className={`font-medium ${confDeltaPp >= 0 ? "text-good" : "text-bad"}`}>
            {confDeltaPp >= 0 ? "+" : ""}{confDeltaPp}pp
          </span>
          .
        </div>
      </div>

      <div
        className="flex items-center justify-between border-t hairline pt-6"
        data-fade
      >
        <button onClick={signOut} className="btn-ghost">
          ↺ Sign out
        </button>
        <div className="flex items-center gap-2">
          <button onClick={() => goto(3)} className="btn-ghost">
            ← Revise
          </button>
          <button className="btn-primary">Download audit PDF</button>
        </div>
      </div>
    </section>
  );
}

function HumanReviewConfirmation({ result }: { result: ReviewResult }) {
  const ev = useStore((s) => s.evaluation);
  const signOut = useStore((s) => s.signOut);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.fromTo(
        "[data-fade]",
        { opacity: 0, y: 14 },
        { opacity: 1, y: 0, duration: 0.55, ease: "power2.out", stagger: 0.08 },
      );
    }, ref);
    return () => ctx.revert();
  }, []);

  if (!ev) return null;

  return (
    <section ref={ref} className="max-w-2xl">
      <div className="mb-2 text-xs uppercase tracking-[0.2em] text-ink-muted" data-fade>
        Step 4 of 4
      </div>
      <h1 className="display mb-6 text-6xl leading-[1.02]" data-fade>
        {ev.verbs.outcome_review_title}
      </h1>
      <p className="mb-10 max-w-2xl text-lg leading-relaxed text-ink-muted" data-fade>
        The model was <em>not</em> re-run. Your statement and the original decision have
        been queued for a person to review.
      </p>

      <div className="mb-10 grid grid-cols-3 gap-4 border-y hairline py-8" data-fade>
        <div>
          <div className="mb-1 text-[10px] uppercase tracking-widest text-ink-muted">
            Queue position
          </div>
          <div className="display text-4xl tabular-nums">#{result.queue_position}</div>
        </div>
        <div>
          <div className="mb-1 text-[10px] uppercase tracking-widest text-ink-muted">
            Expected response
          </div>
          <div className="display text-4xl">{result.estimated_review_window}</div>
        </div>
        <div>
          <div className="mb-1 text-[10px] uppercase tracking-widest text-ink-muted">
            Audit hash
          </div>
          <div className="mono pt-3 text-sm text-ink">{result.audit_hash.slice(0, 14)}…</div>
        </div>
      </div>

      <div
        className="mb-10 rounded-xl border border-good/20 bg-good/5 px-5 py-4 text-[13px] leading-relaxed"
        data-fade
      >
        <div className="mb-2 flex items-center gap-2 text-[10px] uppercase tracking-[0.15em] text-good">
          <span className="h-1.5 w-1.5 rounded-full bg-good" />
          Statutory route
        </div>
        Under {ev.legal_citations.slice(0, 2).join(" and ")}, you have the right to
        request human intervention in an automated decision. Your reviewer will see your
        statement exactly as written.
      </div>

      <div className="flex items-center justify-between border-t hairline pt-6" data-fade>
        <button onClick={signOut} className="btn-ghost">
          ↺ Sign out
        </button>
        <button className="btn-primary">Download audit PDF</button>
      </div>
    </section>
  );
}

function cssSafe(key: string): string {
  return key.replace(/[^A-Za-z0-9_-]/g, "_");
}
