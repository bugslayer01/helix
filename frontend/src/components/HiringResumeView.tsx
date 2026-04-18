import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ResumeDocument } from "./hiring/ResumeDocument";
import { HighlightRail } from "./hiring/HighlightRail";
import { ContestFormPane } from "./hiring/ContestFormPane";
import { HIRING_HIGHLIGHTS } from "./hiring/highlights";

export function HiringResumeView() {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const reduce = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (reduce) return;

    const ctx = gsap.context(() => {
      gsap.fromTo(
        "[data-resume] [data-section]",
        { opacity: 0, x: -14 },
        {
          opacity: 1,
          x: 0,
          duration: 0.55,
          ease: "power2.out",
          stagger: 0.08,
        },
      );
      gsap.fromTo(
        "[data-form-pane]",
        { opacity: 0, y: 18 },
        {
          opacity: 1,
          y: 0,
          duration: 0.55,
          ease: "power2.out",
          delay: 0.15,
        },
      );
      gsap.fromTo(
        "[data-hl]",
        { backgroundColor: "rgba(181,65,43,0.18)" },
        {
          backgroundColor: "rgba(181,65,43,0)",
          duration: 0.8,
          ease: "power2.out",
          stagger: 0.08,
          delay: 0.6,
        },
      );
    }, ref);
    return () => ctx.revert();
  }, []);

  return (
    <div
      ref={ref}
      className="grid gap-8 grid-cols-1 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]"
    >
      <style>{`
        [data-hl].is-pulsing {
          animation: hl-pulse 0.9s ease-out;
        }
        @keyframes hl-pulse {
          0% { background-color: rgba(181,65,43,0.25); box-shadow: 0 0 0 4px rgba(181,65,43,0.18); }
          100% { background-color: transparent; box-shadow: 0 0 0 0 rgba(181,65,43,0); }
        }
        @media (prefers-reduced-motion: reduce) {
          [data-hl].is-pulsing { animation: none; }
        }
      `}</style>

      <div className="min-w-0 space-y-6">
        <ResumeDocument highlights={HIRING_HIGHLIGHTS} />
        <HighlightRail highlights={HIRING_HIGHLIGHTS} />
      </div>

      <div className="min-w-0" data-form-pane>
        <ContestFormPane highlights={HIRING_HIGHLIGHTS} />
      </div>
    </div>
  );
}
