import { useApp, type Domain } from "../store_app";
import { useStore } from "../store";
import { useHiring } from "../store_hiring";

export function DomainSwitcher() {
  const domain = useApp((s) => s.domain);
  const setDomain = useApp((s) => s.setDomain);
  const resetLoans = useStore((s) => s.back);
  const resetHiring = useHiring((s) => s.reset);

  const swap = (d: Domain) => {
    if (d === domain) return;
    setDomain(d);
    // Reset opposite-domain stage so applicant doesn't land mid-flow.
    resetLoans();
    resetHiring();
  };

  const isHiring = domain === "hiring";

  return (
    <div
      role="tablist"
      aria-label="Choose vertical"
      className="relative inline-flex items-center rounded-full border hairline bg-cream-soft p-0.5 text-[12px] font-medium select-none"
    >
      {/* sliding pill background */}
      <span
        aria-hidden
        className="absolute top-0.5 bottom-0.5 left-0.5 w-[calc(50%-2px)] rounded-full bg-brand transition-transform duration-200 ease-out"
        style={{ transform: isHiring ? "translateX(100%)" : "translateX(0)" }}
      />
      <button
        role="tab"
        aria-selected={!isHiring}
        onClick={() => swap("loans")}
        className={`relative z-10 px-4 py-1.5 rounded-full transition-colors duration-200 ${!isHiring ? "text-surface" : "text-ink-muted hover:text-ink"}`}
      >
        Loans
      </button>
      <button
        role="tab"
        aria-selected={isHiring}
        onClick={() => swap("hiring")}
        className={`relative z-10 px-4 py-1.5 rounded-full transition-colors duration-200 ${isHiring ? "text-surface" : "text-ink-muted hover:text-ink"}`}
      >
        Hiring
      </button>
    </div>
  );
}
