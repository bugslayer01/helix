import { useEffect, useRef } from "react";
import gsap from "gsap";
import { useStore } from "../store";

export function Step1View() {
  const ev = useStore((s) => s.evaluation);
  const goto = useStore((s) => s.goto);
  const ref = useRef<HTMLDivElement | null>(null);
  const confRef = useRef<HTMLSpanElement | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.fromTo(
        "[data-fade]",
        { opacity: 0, y: 14 },
        { opacity: 1, y: 0, duration: 0.55, ease: "power2.out", stagger: 0.08 },
      );
      gsap.fromTo(
        "[data-bar]",
        { scaleX: 0, transformOrigin: "50% 50%" },
        { scaleX: 1, duration: 0.7, ease: "power3.out", stagger: 0.1, delay: 0.4 },
      );

      // Count-up on the confidence number.
      if (confRef.current && ev) {
        const target = Math.round(ev.confidence * 100);
        const proxy = { v: 0 };
        gsap.to(proxy, {
          v: target,
          duration: 0.9,
          delay: 0.2,
          ease: "power3.out",
          onUpdate: () => {
            if (confRef.current) confRef.current.textContent = String(Math.round(proxy.v));
          },
        });
      }
    }, ref);
    return () => ctx.revert();
  }, [ev?.case_id, ev?.confidence, ev]);

  if (!ev) return null;

  const scale = 60;
  const verbs = ev.verbs;
  const deniedChipLabel = verbs.denied_label;
  const approvedChipLabel = verbs.approved_label;
  const isDenied = ev.decision === "denied";

  return (
    <section ref={ref} className="max-w-3xl">
      <div className="mb-2 text-xs uppercase tracking-[0.2em] text-ink-muted" data-fade>
        Step 1 of 4
      </div>
      <h1 className="display mb-6 text-6xl leading-[1.02]" data-fade>
        {isDenied ? verbs.hero_question : `Here's why this was ${approvedChipLabel.toLowerCase()}.`}
      </h1>
      <p className="mb-12 max-w-2xl text-lg leading-relaxed text-ink-muted" data-fade>
        {ev.plain_language_reason}
      </p>

      <div className="mb-12 flex items-center gap-6 border-y hairline py-5" data-fade>
        <span
          className={`${isDenied ? "chip-denied" : "chip-approved"} rounded px-3 py-1 text-xs font-semibold uppercase tracking-wider`}
        >
          {isDenied ? deniedChipLabel : approvedChipLabel}
        </span>
        <div className="flex items-baseline gap-2">
          <span className="display text-3xl tabular-nums">
            <span ref={confRef}>{Math.round(ev.confidence * 100)}</span>
            <span className="text-xl">%</span>
          </span>
          <span className="text-sm text-ink-muted">confidence</span>
        </div>
        <div className="mono ml-auto text-xs text-ink-muted">
          model@{ev.model_version_hash.replace("sha256:", "").slice(0, 12)}…
        </div>
      </div>

      <div className="mb-16">
        <div className="mb-5 flex items-center justify-between" data-fade>
          <h2 className="display text-2xl">Contributing factors</h2>
          <div className="text-xs text-ink-muted">Attribution · per feature</div>
        </div>

        <div className="relative" data-fade>
          <div className="axis absolute top-0 bottom-0 left-1/2" />
          <div className="space-y-3 py-4">
            {ev.shap_values.map((row) => {
              const abs = Math.abs(row.contribution);
              const width = Math.min(Math.max(abs * scale, 2), 48);
              const isNegative = row.contribution < 0;
              const barClass = isNegative ? "bg-bad" : "bg-good";
              const valueClass = row.protected
                ? "text-ink-muted"
                : isNegative
                  ? "text-bad"
                  : "text-good";
              return (
                <div
                  key={row.feature}
                  className="grid grid-cols-[200px_1fr_80px] items-center gap-4"
                >
                  <div className="flex items-center gap-2 text-sm">
                    <span className="truncate">{row.displayName}</span>
                    {row.protected && <span className="lock-dot" aria-hidden />}
                  </div>
                  <div className="relative flex h-8 items-center">
                    <div
                      data-bar
                      className={`absolute h-3.5 rounded-sm ${barClass}`}
                      style={{
                        left: isNegative ? `${50 - width}%` : "50%",
                        width: `${width}%`,
                      }}
                    />
                  </div>
                  <div className={`mono text-right text-sm tabular-nums ${valueClass}`}>
                    {row.contribution >= 0 ? "+" : "−"}
                    {abs.toFixed(2)}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-3 flex justify-between text-[10px] uppercase tracking-wider text-ink-muted">
            <span>← pushes toward {deniedChipLabel.toLowerCase()}</span>
            <span>pushes toward {approvedChipLabel.toLowerCase()} →</span>
          </div>
        </div>
      </div>

      <div
        className="flex items-center justify-between border-t hairline pt-6"
        data-fade
      >
        <div className="text-sm text-ink-muted">
          When you're ready, choose how to respond.
        </div>
        <button className="btn-primary" onClick={() => goto(2)}>
          Continue →
        </button>
      </div>
    </section>
  );
}
