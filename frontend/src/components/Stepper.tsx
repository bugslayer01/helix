import { useEffect, useRef } from "react";
import gsap from "gsap";
import type { Step } from "../types";

const STEPS: { label: string; help: string }[] = [
  { label: "Understand", help: "Understand the decision" },
  { label: "Choose path", help: "Choose how to contest" },
  { label: "Provide", help: "Provide information or evidence" },
  { label: "Outcome", help: "See the outcome" },
];

export function Stepper({ currentStep }: { currentStep: Step }) {
  const ref = useRef<HTMLOListElement | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const dots = ref.current.querySelectorAll<HTMLSpanElement>(".step-dot.active");
    if (dots.length > 0) {
      gsap.fromTo(
        dots,
        { scale: 0.7, opacity: 0.4 },
        { scale: 1, opacity: 1, duration: 0.4, ease: "back.out(2)" },
      );
    }
  }, [currentStep]);

  if (currentStep === 0) return null;

  return (
    <ol
      ref={ref}
      className="hidden max-w-3xl flex-1 items-center justify-center gap-0 lg:flex"
      aria-label="Contest progress"
      role="list"
    >
      {STEPS.map((s, i) => {
        const idx = (i + 1) as Step;
        const isDone = idx < currentStep;
        const isActive = idx === currentStep;
        const dotClass = isDone
          ? "bg-ink text-cream"
          : isActive
            ? "bg-ink text-cream shadow-ring"
            : "border border-line text-ink-muted bg-transparent";
        const labelClass = isActive ? "text-ink font-medium" : "text-ink-muted";
        return (
          <li
            key={s.label}
            className="flex items-center"
            aria-current={isActive ? "step" : undefined}
          >
            <div className="flex items-center gap-2.5">
              <span
                aria-hidden
                className={`step-dot inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[12px] font-semibold transition-all duration-200 ${dotClass} ${isActive ? "active" : ""}`}
              >
                {isDone ? "✓" : idx}
              </span>
              <span
                className={`whitespace-nowrap text-xs transition-colors duration-200 ${labelClass}`}
              >
                {s.label}
              </span>
              <span className="sr-only">. {s.help}.</span>
            </div>
            {i < STEPS.length - 1 && (
              <span
                aria-hidden
                className={`mx-3 h-px min-w-[28px] transition-colors duration-300 ${isDone ? "bg-ink" : "bg-line"}`}
                style={{ width: 40 }}
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}
