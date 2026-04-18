import { useRef, useState } from "react";
import { useStore } from "../store";
import type { FeatureSchemaEntry } from "../types";

export function CorrectionForm() {
  const ev = useStore((s) => s.evaluation);
  const flagged = useStore((s) => s.flaggedFields);
  const toggleFlag = useStore((s) => s.toggleFlag);
  const setEvidenceType = useStore((s) => s.setEvidenceType);
  const runContest = useStore((s) => s.runContest);
  const loading = useStore((s) => s.loading);
  const goto = useStore((s) => s.goto);
  const [uploads, setUploads] = useState<Record<string, string>>({});

  if (!ev) return null;

  const valuesByFeature = new Map(ev.shap_values.map((s) => [s.feature, s]));
  const contestable = ev.feature_schema.filter(
    (s) => s.contestable && !s.protected && s.correction_policy !== "locked",
  );
  const flaggedCount = Object.keys(flagged).length;

  return (
    <section
      className="rounded-xl border hairline bg-surface p-6 lg:p-7"
      aria-labelledby="correction-form-title"
    >
      <header className="mb-6 flex items-center justify-between">
        <div>
          <div className="mb-1 text-[11px] uppercase tracking-[0.18em] text-accent">
            Path 01 · Correction
          </div>
          <h2 id="correction-form-title" className="display text-2xl">
            {ev.verbs.correction_title}
          </h2>
          <p className="mt-2 max-w-xl text-sm text-ink-muted">
            Attach the source document for any factor the model got wrong. The
            validator extracts the correct value from it — you never type the
            number.
          </p>
        </div>
      </header>

      <ul className="space-y-3" role="list">
        {contestable.map((schema) => (
          <UploadRow
            key={schema.form_key}
            schema={schema}
            currentDisplay={valuesByFeature.get(schema.feature)?.valueDisplay ?? "—"}
            flagged={!!flagged[schema.form_key]}
            evidenceType={flagged[schema.form_key]?.evidenceType}
            filename={uploads[schema.form_key]}
            onToggle={() => toggleFlag(schema.form_key)}
            onEvidence={(v) => setEvidenceType(schema.form_key, v)}
            onFilePicked={(filename) => {
              setUploads((u) => ({ ...u, [schema.form_key]: filename }));
              if (!flagged[schema.form_key]) toggleFlag(schema.form_key);
              if (!flagged[schema.form_key]?.evidenceType) {
                setEvidenceType(
                  schema.form_key,
                  schema.evidence_types[0] ?? "supporting_document",
                );
              }
            }}
          />
        ))}
      </ul>

      <footer className="mt-7 flex items-center justify-between border-t hairline pt-5">
        <div className="text-xs text-ink-muted">
          {flaggedCount} {flaggedCount === 1 ? "document" : "documents"} attached
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => goto(2)}
            className="btn-ghost"
            aria-label="Cancel corrections and return to path selection"
          >
            Cancel
          </button>
          <button
            disabled={loading === "contest" || flaggedCount === 0}
            onClick={() => runContest()}
            className="btn-primary"
            aria-describedby="re-evaluate-hint"
          >
            {loading === "contest" ? (
              <>
                <span className="spinner" aria-hidden />
                <span>Validating evidence…</span>
              </>
            ) : (
              "Submit documents for validation →"
            )}
          </button>
        </div>
      </footer>
      <span id="re-evaluate-hint" className="sr-only">
        Submitting queues your documents for validation. The validator extracts
        values from each document and the model re-runs only after every
        proposal is verified.
      </span>
    </section>
  );
}

interface UploadRowProps {
  schema: FeatureSchemaEntry;
  currentDisplay: string;
  flagged: boolean;
  evidenceType: string | undefined;
  filename: string | undefined;
  onToggle: () => void;
  onEvidence: (v: string) => void;
  onFilePicked: (filename: string) => void;
}

function UploadRow({
  schema,
  currentDisplay,
  flagged,
  evidenceType,
  filename,
  onToggle,
  onEvidence,
  onFilePicked,
}: UploadRowProps) {
  const options = schema.evidence_types.length > 0
    ? schema.evidence_types
    : ["supporting_document"];
  const rowId = `cf-${schema.form_key}`;
  const inputRef = useRef<HTMLInputElement | null>(null);

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    onFilePicked(file.name);
    // clear so the same file can be reselected if needed
    e.target.value = "";
  };

  return (
    <li
      className={`rounded-lg border px-4 py-4 transition-all ${flagged ? "border-ink bg-surface shadow-sm" : "hairline bg-cream-soft/40"}`}
    >
      <div className="mb-3 flex items-center justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium">{schema.display_name}</div>
          <div className="text-xs text-ink-muted">
            On file: <span className="mono">{currentDisplay}</span>
            <span className="ml-2 pill pill-warn">We compute this from your document</span>
          </div>
        </div>
        <label
          htmlFor={rowId}
          className={`flex cursor-pointer items-center gap-2 text-xs ${flagged ? "font-medium text-accent" : "text-ink-muted"}`}
        >
          <input
            id={rowId}
            type="checkbox"
            checked={flagged}
            onChange={onToggle}
            className="cursor-pointer accent-accent"
            aria-label={`Flag ${schema.display_name} for correction`}
          />
          <span>Contest this factor</span>
        </label>
      </div>

      {flagged && (
        <div
          className="grid grid-cols-[minmax(110px,130px)_1fr] items-center gap-x-4 gap-y-3 text-sm"
          role="group"
          aria-label={`Document upload for ${schema.display_name}`}
        >
          <label htmlFor={`${rowId}-evidence`} className="text-ink-muted">
            Document type
          </label>
          <select
            id={`${rowId}-evidence`}
            value={evidenceType ?? options[0]}
            onChange={(e) => onEvidence(e.target.value)}
            className="rounded border hairline bg-surface px-2.5 py-2 text-sm focus:border-ink focus:outline-none"
            aria-label={`Evidence type for ${schema.display_name}`}
          >
            {options.map((o) => (
              <option key={o} value={o}>
                {prettyEvidence(o)}
              </option>
            ))}
          </select>

          <div className="text-ink-muted">File</div>
          <div className="flex items-center gap-3">
            <input
              ref={inputRef}
              type="file"
              onChange={handleFile}
              className="sr-only"
              aria-hidden
              tabIndex={-1}
            />
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="rounded border hairline bg-cream-soft/60 px-3 py-1.5 text-[11px] uppercase tracking-wider text-ink-muted transition-colors hover:text-ink"
              aria-label={`${filename ? "Replace" : "Attach"} document for ${schema.display_name}`}
            >
              {filename ? "Replace file" : "Attach document"}
            </button>
            {filename && (
              <span className="mono flex items-center gap-2 text-[12px] text-ink">
                <span className="h-2 w-2 rounded-full bg-good" aria-hidden />
                {truncateMiddle(filename, 36)}
              </span>
            )}
          </div>

          {schema.hint && (
            <div className="col-span-2 mt-1 border-l-2 border-accent pl-3 text-xs text-ink-muted">
              <span className="font-medium text-ink">Hint.</span> {schema.hint}
            </div>
          )}
        </div>
      )}
    </li>
  );
}

function prettyEvidence(raw: string): string {
  return raw.replace(/_/g, " ").replace(/^(.)/, (c) => c.toUpperCase());
}

function truncateMiddle(s: string, max: number): string {
  if (s.length <= max) return s;
  const keep = Math.floor((max - 1) / 2);
  return `${s.slice(0, keep)}…${s.slice(-keep)}`;
}
