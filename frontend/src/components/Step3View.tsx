import { useEffect, useRef } from "react";
import gsap from "gsap";
import { useStore } from "../store";
import { ProfileCard } from "./ProfileCard";
import { CorrectionForm } from "./CorrectionForm";
import { NewEvidenceForm } from "./NewEvidenceForm";
import { HumanReviewForm } from "./HumanReviewForm";
import { HiringResumeView } from "./HiringResumeView";

export function Step3View() {
  const ev = useStore((s) => s.evaluation);
  const selectedPath = useStore((s) => s.selectedPath);
  const goto = useStore((s) => s.goto);
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
  }, [selectedPath]);

  if (!ev) return null;

  const path = selectedPath ?? "correction";
  const verbs = ev.verbs;
  const isHumanReview = path === "human_review";

  const heading =
    path === "correction"
      ? verbs.correction_title
      : path === "new_evidence"
        ? verbs.new_evidence_title
        : verbs.review_title;

  const sub =
    path === "correction"
      ? verbs.correction_sub
      : path === "new_evidence"
        ? verbs.new_evidence_sub
        : verbs.review_sub;

  return (
    <section ref={ref}>
      <div className="mb-2 text-xs uppercase tracking-[0.2em] text-ink-muted" data-fade>
        Step 3 of 4
      </div>
      <div className="mb-2 flex items-baseline justify-between" data-fade>
        <h1 className="display text-4xl leading-[1.05]">{heading}</h1>
        <button className="btn-ghost" onClick={() => goto(2)}>
          ← Change path
        </button>
      </div>
      <p className="mb-8 max-w-2xl text-base text-ink-muted" data-fade>
        {sub}
      </p>

      {path === "correction" && ev.domain === "hiring" ? (
        <div data-fade>
          <HiringResumeView />
        </div>
      ) : (
        <div
          data-fade
          className={`grid gap-6 ${isHumanReview ? "grid-cols-1 max-w-2xl" : "grid-cols-[300px_1fr]"}`}
        >
          {!isHumanReview && <ProfileCard />}
          <div>
            {path === "correction" && <CorrectionForm />}
            {path === "new_evidence" && <NewEvidenceForm />}
            {path === "human_review" && <HumanReviewForm />}
          </div>
        </div>
      )}
    </section>
  );
}
