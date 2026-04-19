import { useRef } from "react";
import { useStore, type LoanDocType, type DocUploadState } from "../store";

const SLOTS: { key: LoanDocType; label: string; accept: string; hint: string }[] = [
  { key: "payslip", label: "Payslip", accept: ".pdf,application/pdf", hint: "Latest month, PDF." },
  { key: "bank_statement", label: "Bank statement", accept: ".pdf,application/pdf", hint: "Last 3–6 months, PDF." },
  { key: "credit_report", label: "Credit report", accept: ".pdf,application/pdf", hint: "Bureau report, PDF." },
];

function DocRow({ slot }: { slot: (typeof SLOTS)[number] }) {
  const ref = useRef<HTMLInputElement | null>(null);
  const state = useStore((s) => s.uploadedDocs[slot.key]);
  const uploading = useStore((s) => s.uploadingDoc[slot.key]);
  const uploadLoanDoc = useStore((s) => s.uploadLoanDoc);

  const hasGood = state && !state.error;
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <label className="label">{slot.label}</label>
        <span className="text-[11px] text-ink-muted">{slot.hint}</span>
      </div>
      <input
        ref={ref}
        type="file"
        accept={slot.accept}
        className="sr-only"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) uploadLoanDoc(slot.key, f);
          e.target.value = "";
        }}
      />
      <button
        className="btn-ghost w-full py-3"
        disabled={uploading}
        onClick={() => ref.current?.click()}
      >
        {uploading ? (
          <><span className="spinner" /> Extracting…</>
        ) : hasGood ? (
          `Re-upload ${slot.label.toLowerCase()}`
        ) : (
          `Choose ${slot.label.toLowerCase()} PDF`
        )}
      </button>
      <DocStatus state={state} uploading={uploading} label={slot.label} />
    </div>
  );
}

function DocStatus({ state, uploading, label }: { state: DocUploadState | null; uploading: boolean; label: string }) {
  if (uploading) {
    return (
      <div className="mt-2 text-[12px] text-ink-muted flex items-center gap-2">
        <span className="spinner" /> Extracting…
      </div>
    );
  }
  if (!state) return null;
  if (state.error) {
    return <div className="mt-2 text-[12px] text-bad">✕ {state.error}</div>;
  }
  const conf = typeof state.confidence === "number" ? state.confidence.toFixed(2) : "—";
  return (
    <div className="mt-2 text-[12px] text-good">
      ✓ {label} — source: <span className="mono text-ink-muted">{state.source || "unknown"}</span>
      {" "}• conf: <span className="mono text-ink-muted">{conf}</span>
    </div>
  );
}

export function LoanDocsUploadView() {
  const appId = useStore((s) => s.intakeApplicationId);
  const docs = useStore((s) => s.uploadedDocs);
  const submitLoanApplication = useStore((s) => s.submitLoanApplication);
  const goto = useStore((s) => s.goto);
  const busy = useStore((s) => s.busy);
  const error = useStore((s) => s.error);

  const allGood = SLOTS.every((s) => docs[s.key] && !docs[s.key]?.error);

  return (
    <section className="mx-auto max-w-2xl px-6 py-14">
      <div className="label mb-3">
        New application{" "}
        {appId && <span className="mono text-ink-muted">· {appId}</span>}
      </div>
      <h1 className="display text-4xl mb-3">Attach the underwriting documents.</h1>
      <p className="text-ink-muted mb-6 max-w-xl">
        Each PDF is hashed, extracted on upload, and then scored together when
        you submit. Re-upload any slot to replace it.
      </p>
      <div className="card p-5 space-y-6">
        {SLOTS.map((slot) => (
          <DocRow key={slot.key} slot={slot} />
        ))}
        {error && (
          <div className="rounded-md border border-bad/40 bg-bad/5 px-3 py-2 text-sm text-bad">{error}</div>
        )}
        <div className="flex items-center justify-between pt-2 border-t hairline">
          <button className="btn-ghost" onClick={() => goto("picker")}>← Back to cases</button>
          <button
            className="btn-primary"
            disabled={!allGood || busy}
            onClick={() => submitLoanApplication()}
          >
            {busy ? <><span className="spinner" /> Scoring…</> : "Submit + score →"}
          </button>
        </div>
      </div>
    </section>
  );
}
