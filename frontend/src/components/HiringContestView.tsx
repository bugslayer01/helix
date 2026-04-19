import { useEffect, useRef, useState } from "react";
import { useStore } from "../store";
import { EvidenceShieldPanel } from "./EvidenceShieldPanel";

const DOC_TYPES: { id: string; label: string }[] = [
  { id: "certificate", label: "Certification / course completion" },
  { id: "course_completion", label: "Course transcript" },
  { id: "recommendation_letter", label: "Recommendation letter" },
  { id: "linkedin_export", label: "LinkedIn export" },
  { id: "resume", label: "Updated resume" },
];

interface ReasonRow {
  feature: string;
  display_name?: string;
  value?: string | number;
  value_display?: string;
  contribution: number;
  evidence_quote?: string;
  jd_requirement?: string;
  protected?: boolean;
}

function ReasonCard({ reason }: { reason: ReasonRow }) {
  const upload = useStore((s) => s.upload);
  const removeEvidence = useStore((s) => s.removeEvidence);
  const evidence = useStore((s) => s.evidence);
  const busy = useStore((s) => s.busy);

  const [text, setText] = useState("");
  const [docType, setDocType] = useState(DOC_TYPES[0].id);
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const submitted = evidence.filter((e) => e.target_feature === reason.feature);

  const submit = async () => {
    if (!text.trim() && !file) return;
    const r = await upload(reason.feature, docType, { file, rebuttalText: text.trim() || null });
    if (r) {
      setText("");
      setFile(null);
    }
  };

  const negative = reason.contribution < 0;

  return (
    <div className={`card p-5 ${negative ? "border-bad/30" : "border-good/30"}`}>
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`pill ${negative ? "pill-denied" : "pill-approved"}`}>
              {negative ? "Counts against you" : "Counts for you"}
            </span>
            <span className="mono text-[12px] text-ink-muted">
              {reason.contribution >= 0 ? "+" : ""}{reason.contribution.toFixed(2)}
            </span>
          </div>
          <div className="display text-lg">{reason.display_name || reason.feature}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-[1fr_1fr] gap-3 text-[13px] mb-4">
        <div className="rounded border hairline bg-cream-soft/40 p-3">
          <div className="label mb-1">JD requires</div>
          <div className="text-ink">{reason.jd_requirement || "—"}</div>
        </div>
        <div className="rounded border hairline bg-cream-soft/40 p-3">
          <div className="label mb-1">Resume says</div>
          <div className="text-ink mono text-[12.5px]">{reason.value_display || reason.value || "—"}</div>
        </div>
      </div>

      {submitted.length === 0 ? (
        <div className="rounded-lg border hairline bg-cream-soft/30 p-4 space-y-4">
          <div>
            <label className="flex items-center justify-between mb-2">
              <span className="label">Your rebuttal</span>
              <span className="text-[11px] text-ink-muted">{text.length} chars</span>
            </label>
            <textarea
              rows={5}
              className="block w-full rounded-md border hairline bg-surface px-3 py-2.5 text-[14px] leading-relaxed text-ink placeholder:text-ink-muted/60 focus:border-brand focus:outline-none focus:shadow-focus resize-y min-h-[120px]"
              placeholder={negative
                ? "Explain why this judgment is wrong, or what context the resume omitted. Be specific — cite roles, dates, projects, or numbers."
                : "Optional: add nuance or evidence supporting this strength."}
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
          </div>

          <div>
            <label className="label mb-2 block">Supporting document (optional)</label>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_auto]">
              <select
                className="input text-[13px] py-2"
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
              >
                {DOC_TYPES.map((d) => <option key={d.id} value={d.id}>{d.label}</option>)}
              </select>
              <input
                ref={inputRef}
                type="file"
                className="sr-only"
                accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
                onChange={(e) => { setFile(e.target.files?.[0] || null); e.target.value = ""; }}
              />
              <button
                type="button"
                className={`inline-flex items-center justify-center gap-2 rounded-md border hairline px-4 py-2 text-[13px] transition-colors ${file ? "border-brand bg-brand-soft/40 text-brand" : "bg-surface text-ink-muted hover:text-brand hover:border-brand"}`}
                disabled={busy}
                onClick={() => inputRef.current?.click()}
              >
                {file ? <><span>📎</span><span className="mono truncate max-w-[180px]">{file.name}</span></> : <><span>📎</span><span>Attach file</span></>}
              </button>
            </div>
            {file && (
              <button
                type="button"
                className="mt-1 text-[11px] text-ink-muted hover:text-bad"
                onClick={() => setFile(null)}
              >
                ✕ Remove attachment
              </button>
            )}
          </div>

          <div className="flex items-center justify-between pt-2 border-t hairline">
            <div className="text-[11px] text-ink-muted">
              {text.trim() || file ? "Ready to submit." : "Provide text, a file, or both."}
            </div>
            <button
              className="btn-primary"
              disabled={busy || (!text.trim() && !file)}
              onClick={submit}
            >
              {busy ? <><span className="spinner" /> Submitting…</> : "Submit rebuttal →"}
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {submitted.map((ev) => (
            <div key={ev.id}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2 text-[12.5px]">
                  <span className="pill">{ev.doc_type}</span>
                  {(ev.extracted as any)?.rebuttal_text && (
                    <span className="text-ink-muted italic">"{String((ev.extracted as any).rebuttal_text).slice(0, 80)}{String((ev.extracted as any).rebuttal_text).length > 80 ? "…" : ""}"</span>
                  )}
                </div>
                <button className="btn-ghost text-xs" onClick={() => removeEvidence(ev.id)}>Remove</button>
              </div>
              <EvidenceShieldPanel checks={ev.checks} overall={ev.overall} summary={ev.summary} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function HiringContestView() {
  const goto = useStore((s) => s.goto);
  const submit = useStore((s) => s.submit);
  const refresh = useStore((s) => s.refreshEvidence);
  const evidence = useStore((s) => s.evidence);
  const submitting = useStore((s) => s.submitting);
  const error = useStore((s) => s.error);
  const shap = useStore((s) => s.shap);

  useEffect(() => { refresh(); }, []);

  const negativeReasons = (shap as ReasonRow[]).filter((r) => r.contribution < 0).sort((a, b) => a.contribution - b.contribution);
  const positiveReasons = (shap as ReasonRow[]).filter((r) => r.contribution >= 0);
  const accepted = evidence.filter((e) => e.overall === "accepted").length;

  return (
    <section className="mx-auto max-w-3xl px-6 py-12">
      <div className="label mb-3">Step 2 of 4 · Counter the recruiter's model</div>
      <h1 className="display text-4xl mb-2">Address each reason that counted against you.</h1>
      <p className="text-ink-muted text-base max-w-2xl mb-3">
        For every reason below, write a short rebuttal in your own words AND
        optionally attach a supporting document (a certificate, transcript,
        recommendation letter, or updated resume). The model re-judges with
        your rebuttals + evidence in context.
      </p>
      <div className="rounded-md border border-warn/40 bg-warn/5 px-3 py-2 text-[12.5px] text-warn mb-8">
        ⚠ You get one re-evaluation cycle. Submit all your rebuttals before clicking "Re-evaluate".
      </div>

      <div className="space-y-4 mb-8">
        {negativeReasons.length === 0 && (
          <div className="card p-5 text-sm text-ink-muted">No negative factors found in this decision.</div>
        )}
        {negativeReasons.map((r) => <ReasonCard key={r.feature} reason={r} />)}
      </div>

      {positiveReasons.length > 0 && (
        <details className="mb-8">
          <summary className="cursor-pointer text-[13px] text-ink-muted hover:text-ink mb-2">
            {positiveReasons.length} positive reasons (already in your favor) — usually no need to counter
          </summary>
          <div className="mt-3 space-y-3">
            {positiveReasons.map((r) => <ReasonCard key={r.feature} reason={r} />)}
          </div>
        </details>
      )}

      {error && <div className="rounded-md border border-accent/40 bg-accent/5 px-3 py-2 text-sm text-accent mb-4">{error}</div>}

      <div className="flex items-center justify-between border-t hairline pt-6">
        <button className="btn-ghost" onClick={() => goto("understand")}>← Back</button>
        <div className="flex items-center gap-3">
          <div className="text-[12px] text-ink-muted">{accepted} of {evidence.length} rebuttal(s) accepted</div>
          <button
            className="btn-primary"
            disabled={accepted === 0 || submitting}
            onClick={() => submit()}
          >
            {submitting ? <><span className="spinner" /> Re-judging with LLM…</> : "Re-evaluate now →"}
          </button>
        </div>
      </div>
    </section>
  );
}
