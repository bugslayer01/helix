import type { CheckRow } from "../lib/api";

export function EvidenceShieldPanel({
  checks,
  overall,
  summary,
}: {
  checks: CheckRow[];
  overall: "accepted" | "flagged" | "rejected" | null;
  summary: string | null;
}) {
  const passed = checks.filter((c) => c.passed).length;

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="label mb-1">Evidence Shield</div>
          <div className="display text-lg">
            {passed}/{checks.length} checks passed
          </div>
        </div>
        <span className={`pill ${overall === "accepted" ? "pill-approved" : overall === "rejected" ? "pill-denied" : "border-warn/40 bg-warn/10 text-warn"}`}>
          {overall ?? "pending"}
        </span>
      </div>
      {summary && <div className="text-[13px] text-ink-muted mb-3">{summary}</div>}
      <ul className="space-y-2">
        {checks.map((c) => (
          <li key={c.name} className={`grid grid-cols-[20px_1fr] gap-3 text-[13px] ${c.passed ? "" : c.severity === "high" ? "text-bad" : "text-warn"}`}>
            <span className="pt-[3px]">
              {c.passed ? (
                <span className="inline-block h-2.5 w-2.5 rounded-full bg-good" />
              ) : c.severity === "high" ? (
                <span className="inline-block h-2.5 w-2.5 rounded-full bg-bad" />
              ) : (
                <span className="inline-block h-2.5 w-2.5 rounded-full bg-warn" />
              )}
            </span>
            <div>
              <div className="font-medium">{labelFor(c.name)}</div>
              <div className="text-ink-muted text-[12.5px]">{c.detail}</div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function labelFor(name: string): string {
  const map: Record<string, string> = {
    doc_type_matches_claim: "Document type matches the claim",
    freshness: "Document is fresh enough",
    bounds: "Value within sane bounds",
    cross_doc_consistency: "Consistent with other uploaded docs",
    issuer_present: "Issuer / letterhead detected",
    format_sanity: "Format hygiene",
    plausibility_vs_baseline: "Plausible vs prior baseline",
    pdf_metadata_check: "PDF metadata forensics",
    text_vs_render: "Text layer matches rendered OCR",
    replay: "Replay / reuse check",
  };
  return map[name] || name;
}
