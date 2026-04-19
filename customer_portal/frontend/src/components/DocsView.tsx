import { useRef } from "react";
import { useStore } from "../store";

const REQUIRED_DOCS: { id: string; label: string; description: string }[] = [
  {
    id: "payslip",
    label: "Latest payslip",
    description: "PDF or image from your current employer, under 90 days old.",
  },
  {
    id: "bank_statement",
    label: "Bank statement (6 months)",
    description: "Salary account, covering the last six months. PDF.",
  },
  {
    id: "credit_report",
    label: "Credit bureau report",
    description: "Experian, CIBIL, or Equifax. Issued within the last 30 days.",
  },
  {
    id: "id_document",
    label: "Government ID",
    description: "Aadhaar, PAN, or passport.",
  },
];

function DocRow({ doc }: { doc: (typeof REQUIRED_DOCS)[number] }) {
  const uploads = useStore((s) => s.uploads);
  const uploadDoc = useStore((s) => s.uploadDoc);
  const busy = useStore((s) => s.busy);
  const picked = uploads.find((u) => u.doc_type === doc.id);
  const ref = useRef<HTMLInputElement | null>(null);

  return (
    <div className="card p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="font-medium">{doc.label}</div>
          <div className="text-[13px] text-ink-muted">{doc.description}</div>
          {picked && (
            <div className="mt-3 flex items-center gap-2 text-[12.5px]">
              <span className="h-1.5 w-1.5 rounded-full bg-good" />
              <span className="mono text-ink">{picked.original_name}</span>
              <span className="pill ml-2">{picked.source}</span>
              <span className="pill">confidence {(picked.confidence * 100).toFixed(0)}%</span>
            </div>
          )}
          {picked && Object.keys(picked.extracted).length > 0 && (
            <details className="mt-2 text-[12.5px] text-ink-muted">
              <summary className="cursor-pointer text-ink hover:text-brand">Inspect extracted fields</summary>
              <pre className="mono mt-2 rounded bg-cream-soft p-2 text-[11.5px] whitespace-pre-wrap break-all">
                {JSON.stringify(picked.extracted, null, 2)}
              </pre>
            </details>
          )}
        </div>
        <div>
          <input
            ref={ref}
            type="file"
            className="sr-only"
            accept="application/pdf,image/png,image/jpeg"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) uploadDoc(doc.id, f);
              e.target.value = "";
            }}
          />
          <button
            className="btn-ghost"
            disabled={busy}
            onClick={() => ref.current?.click()}
          >
            {picked ? "Replace" : "Attach"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function DocsView() {
  const uploads = useStore((s) => s.uploads);
  const submit = useStore((s) => s.submitForDecision);
  const goto = useStore((s) => s.goto);
  const busy = useStore((s) => s.busy);
  const error = useStore((s) => s.error);

  const haveAll = REQUIRED_DOCS.filter((d) => d.id !== "id_document").every((d) =>
    uploads.some((u) => u.doc_type === d.id),
  );

  return (
    <section className="mx-auto max-w-2xl px-6 py-12">
      <div className="label mb-3">Step 2 of 3 · Documents</div>
      <h1 className="display text-4xl mb-4">Attach the documents we'll score on.</h1>
      <p className="text-ink-muted mb-8 text-base max-w-xl">
        Our underwriting model reads each document with a local OCR pipeline.
        You never type a financial number — the extractor pulls the values
        directly. You can inspect every extracted field before continuing.
      </p>

      <div className="space-y-3">
        {REQUIRED_DOCS.map((d) => (
          <DocRow key={d.id} doc={d} />
        ))}
      </div>

      {error && <div className="mt-5 rounded-md border border-bad/40 bg-bad/5 px-3 py-2 text-sm text-bad">{error}</div>}

      <div className="mt-8 flex items-center justify-between">
        <button className="btn-ghost" onClick={() => goto("form")}>← Back</button>
        <button className="btn-primary" disabled={!haveAll || busy} onClick={() => submit()}>
          {busy ? <><span className="spinner" /> Scoring…</> : "Submit for decision →"}
        </button>
      </div>
      {!haveAll && <div className="mt-3 text-[12px] text-ink-muted">Payslip, bank statement, and credit report are required. ID is optional for this demo.</div>}
    </section>
  );
}
