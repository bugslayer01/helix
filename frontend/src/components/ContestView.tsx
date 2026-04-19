import { useEffect, useRef, useState } from "react";
import { useStore } from "../store";
import { EvidenceShieldPanel } from "./EvidenceShieldPanel";

type FeatureSpec = {
  key: string;
  label: string;
  description: string;
  accepted_docs: { id: string; label: string }[];
};

const CONTESTABLE_FEATURES: FeatureSpec[] = [
  {
    key: "MonthlyIncome",
    label: "Monthly income",
    description: "Upload a recent payslip or bank statement. The extractor pulls net monthly income directly.",
    accepted_docs: [
      { id: "payslip", label: "Payslip" },
      { id: "bank_statement", label: "Bank statement (salary credits)" },
    ],
  },
  {
    key: "DebtRatio",
    label: "Debt-to-income ratio",
    description: "Upload a loan payoff letter or a bank statement showing debt service lines to update your obligations.",
    accepted_docs: [
      { id: "loan_payoff_letter", label: "Loan payoff letter" },
      { id: "bank_statement", label: "Bank statement" },
    ],
  },
  {
    key: "RevolvingUtilizationOfUnsecuredLines",
    label: "Credit card utilization",
    description: "Upload a fresh credit report or card statement. We pull the revolving utilization number.",
    accepted_docs: [
      { id: "credit_report", label: "Credit report" },
      { id: "card_statement", label: "Card statement" },
    ],
  },
];

function UploadRow({ spec }: { spec: FeatureSpec }) {
  const evidence = useStore((s) => s.evidence);
  const upload = useStore((s) => s.upload);
  const removeEvidence = useStore((s) => s.removeEvidence);
  const busy = useStore((s) => s.busy);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [docType, setDocType] = useState(spec.accepted_docs[0].id);

  const forThis = evidence.filter((e) => e.target_feature === spec.key);

  return (
    <div className="card p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="label mb-1">{spec.label}</div>
          <h3 className="display text-lg mb-1">Change this factor</h3>
          <p className="text-[13px] text-ink-muted">{spec.description}</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            className="input text-sm w-44"
            value={docType}
            onChange={(e) => setDocType(e.target.value)}
          >
            {spec.accepted_docs.map((d) => (
              <option key={d.id} value={d.id}>{d.label}</option>
            ))}
          </select>
          <input
            ref={inputRef}
            type="file"
            className="sr-only"
            accept="application/pdf,image/png,image/jpeg"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) upload(spec.key, docType, f);
              e.target.value = "";
            }}
          />
          <button className="btn-primary" disabled={busy} onClick={() => inputRef.current?.click()}>Upload</button>
        </div>
      </div>

      {forThis.length > 0 && (
        <div className="mt-4 space-y-4">
          {forThis.map((ev) => (
            <div key={ev.id} className="border-t hairline pt-4">
              <div className="flex items-start justify-between mb-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 text-[13px]">
                    <span className="pill">{ev.doc_type}</span>
                    {ev.extracted_value !== null && (
                      <span className="mono text-ink">extracted: {ev.extracted_value}</span>
                    )}
                  </div>
                  {Object.keys(ev.extracted).length > 0 && (
                    <details className="mt-2 text-[12px]">
                      <summary className="cursor-pointer text-ink-muted hover:text-ink">Inspect extracted fields</summary>
                      <pre className="mono mt-2 rounded bg-cream-soft p-2 text-[11px] whitespace-pre-wrap break-all">
                        {JSON.stringify(ev.extracted, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
                <button className="btn-ghost text-xs" onClick={() => removeEvidence(ev.id)}>Remove</button>
              </div>
              <EvidenceShieldPanel
                checks={ev.checks}
                overall={ev.overall}
                summary={ev.summary}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function ContestView() {
  const goto = useStore((s) => s.goto);
  const submit = useStore((s) => s.submit);
  const refresh = useStore((s) => s.refreshEvidence);
  const evidence = useStore((s) => s.evidence);
  const submitting = useStore((s) => s.submitting);
  const error = useStore((s) => s.error);

  const accepted = evidence.filter((e) => e.overall === "accepted").length;

  useEffect(() => { refresh(); }, []);

  return (
    <section className="mx-auto max-w-4xl px-6 py-12">
      <div className="label mb-3">Step 2 of 4 · Contest</div>
      <h1 className="display text-4xl mb-2">Attach evidence for each factor you want to change.</h1>
      <p className="text-ink-muted text-base max-w-2xl mb-8">
        Upload a real document. Our pipeline runs 10 forensic checks — document type,
        freshness, bounds, cross-doc consistency, issuer attribution, format hygiene,
        plausibility vs your baseline, PDF metadata, text-vs-render tamper detection,
        and replay — before turning the extracted value into a proposal for
        re-evaluation.
      </p>

      <div className="space-y-4">
        {CONTESTABLE_FEATURES.map((f) => <UploadRow key={f.key} spec={f} />)}
      </div>

      {error && <div className="mt-5 rounded-md border border-accent/40 bg-accent/5 px-3 py-2 text-sm text-accent">{error}</div>}

      <div className="mt-8 flex items-center justify-between border-t hairline pt-6">
        <button className="btn-ghost" onClick={() => goto("understand")}>← Back</button>
        <div className="flex items-center gap-3">
          <div className="text-[12px] text-ink-muted">{accepted} of {evidence.length} accepted</div>
          <button
            className="btn-primary"
            disabled={accepted === 0 || submitting}
            onClick={() => submit()}
          >
            {submitting ? <><span className="spinner" /> Re-evaluating…</> : "Re-evaluate now →"}
          </button>
        </div>
      </div>
    </section>
  );
}
