import { useEffect, useRef } from "react";
import gsap from "gsap";
import { useStore } from "../store";
import type { ContestPath } from "../types";

export function Step2View() {
  const ev = useStore((s) => s.evaluation);
  const goto = useStore((s) => s.goto);
  const selectPath = useStore((s) => s.selectPath);
  const selectedPath = useStore((s) => s.selectedPath);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.fromTo(
        "[data-fade]",
        { opacity: 0, y: 14 },
        { opacity: 1, y: 0, duration: 0.55, ease: "power2.out", stagger: 0.08 },
      );
      gsap.fromTo(
        "[data-card]",
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0, duration: 0.6, ease: "power3.out", stagger: 0.1, delay: 0.2 },
      );
    }, ref);
    return () => ctx.revert();
  }, []);

  if (!ev) return null;

  const verbs = ev.verbs;

  const paths: Array<{
    id: ContestPath;
    num: string;
    title: string;
    body: string;
    aux?: string;
    legal?: boolean;
  }> = [
    {
      id: "correction",
      num: "Path 01",
      title: verbs.correction_button,
      body: verbs.correction_body,
      aux: "→ Re-evaluates",
    },
    {
      id: "new_evidence",
      num: "Path 02",
      title: "Submit new evidence",
      body: verbs.new_evidence_body,
      aux: "→ Re-evaluates",
    },
    {
      id: "human_review",
      num: "Path 03",
      title: "Request human reviewer",
      body: verbs.review_body,
      legal: true,
    },
  ];

  const handleSelect = (p: ContestPath, el: HTMLElement) => {
    selectPath(p);
    gsap.fromTo(
      el,
      { scale: 1 },
      {
        scale: 1.02,
        duration: 0.12,
        yoyo: true,
        repeat: 1,
        ease: "power2.out",
        onComplete: () => setTimeout(() => goto(3), 140),
      },
    );
  };

  return (
    <section ref={ref}>
      <div className="mb-2 text-xs uppercase tracking-[0.2em] text-ink-muted" data-fade>
        Step 2 of 4
      </div>
      <h1 className="display mb-5 text-5xl leading-[1.05]" data-fade>
        How would you like to contest?
      </h1>
      <p className="mb-10 max-w-2xl text-base leading-relaxed text-ink-muted" data-fade>
        Contestation isn't one shape. Choose the one that matches your situation — each
        triggers a different pipeline, and the third is your statutory right to a human
        reviewer.
      </p>

      <div className="mb-10 grid grid-cols-3 gap-5">
        {paths.map((p) => {
          const isSelected = selectedPath === p.id;
          return (
            <button
              key={p.id}
              data-card
              onClick={(e) => handleSelect(p.id, e.currentTarget)}
              className={`group cursor-pointer rounded-xl border hairline bg-surface p-6 text-left transition-all duration-200 hover:-translate-y-0.5 hover:border-ink ${isSelected ? "border-ink bg-cream-soft" : ""}`}
            >
              <div className="mb-3 text-[10px] uppercase tracking-widest text-accent">
                {p.num}
              </div>
              <h3 className="display mb-2 text-xl">{p.title}</h3>
              <p className="text-sm leading-relaxed text-ink-muted">{p.body}</p>
              {p.aux && <div className="mt-4 text-xs text-ink-muted">{p.aux}</div>}
              {p.legal && ev.legal_citations.length > 0 && (
                <div className="mt-3 text-[10px] uppercase tracking-[0.08em] text-ink-muted">
                  {ev.legal_citations.slice(0, 2).join(" · ")}
                </div>
              )}
            </button>
          );
        })}
      </div>

      <div className="flex items-center justify-between border-t hairline pt-6" data-fade>
        <button className="btn-ghost" onClick={() => goto(1)}>
          ← Back
        </button>
        <div className="text-xs text-ink-muted">Select a path to continue</div>
      </div>
    </section>
  );
}
