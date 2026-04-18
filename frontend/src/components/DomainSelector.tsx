import { useEffect } from "react";
import { useStore } from "../store";
import type { Domain } from "../types";

const DOMAIN_ORDER: Domain[] = [
  "loans",
  "hiring",
  "moderation",
  "admissions",
  "fraud",
];

const DOMAIN_BLURB: Record<Domain, string> = {
  loans: "Credit · SHAP on real XGBoost",
  hiring: "Employment screening",
  moderation: "Creator content removal",
  admissions: "University & scholarship",
  fraud: "Account freezes",
};

export function DomainSelector() {
  // All hooks must run unconditionally, BEFORE any early return, to honor
  // the Rules of Hooks.
  const domains = useStore((s) => s.domains);
  const fetchDomains = useStore((s) => s.fetchDomains);
  const setRef = useStore((s) => s.setRef);
  const setDob = useStore((s) => s.setDob);
  const applicantRef = useStore((s) => s.applicantRef);

  useEffect(() => {
    if (!domains) fetchDomains();
  }, [domains, fetchDomains]);

  if (!domains) return null;

  const handlePick = (domain: Domain) => {
    const cases = domains.cases_by_domain[domain];
    if (!cases || cases.length === 0) return;
    const first = cases[0];
    setRef(first.applicant_reference);
    const [y, m, d] = first.date_of_birth.split("-");
    setDob("year", y);
    setDob("month", m);
    setDob("day", d);
  };

  const activeDomain = inferDomainFromRef(applicantRef);

  return (
    <div className="mt-8 border-t hairline pt-6">
      <div className="mb-3 text-[10px] uppercase tracking-[0.2em] text-ink-muted">
        Demo · try a domain
      </div>
      <div className="flex flex-wrap gap-2">
        {DOMAIN_ORDER.map((d) => {
          const domainMeta = domains.domains.find((x) => x.id === d);
          if (!domainMeta) return null;
          const isActive = activeDomain === d;
          return (
            <button
              key={d}
              type="button"
              onClick={() => handlePick(d)}
              className={`rounded-full border px-3 py-1.5 text-xs transition-all ${
                isActive
                  ? "border-ink bg-ink text-cream"
                  : "hairline bg-surface text-ink-muted hover:border-ink hover:text-ink"
              }`}
              title={DOMAIN_BLURB[d]}
            >
              {domainMeta.display_name}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function inferDomainFromRef(ref: string): Domain | null {
  const prefix = ref.slice(0, 2).toUpperCase();
  const map: Record<string, Domain> = {
    RC: "loans",
    HR: "hiring",
    CM: "moderation",
    UA: "admissions",
    FR: "fraud",
  };
  return map[prefix] ?? null;
}
