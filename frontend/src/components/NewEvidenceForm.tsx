import { useRef, useState } from "react";
import { useStore } from "../store";
import type { FeatureSchemaEntry } from "../types";

export function NewEvidenceForm() {
  const ev = useStore((s) => s.evaluation);
  const flagged = useStore((s) => s.flaggedFields);
  const toggleFlag = useStore((s) => s.toggleFlag);
  const setEvidenceType = useStore((s) => s.setEvidenceType);
  const runContest = useStore((s) => s.runContest);
  const loading = useStore((s) => s.loading);
  const goto = useStore((s) => s.goto);
  const [fileNames, setFileNames] = useState<Record<string, string>>({});

  if (!ev) return null;

  const contestable = ev.feature_schema.filter(
    (s) => s.contestable && !s.protected && s.correction_policy !== "locked",
  );
  const valuesByFeature = new Map(ev.shap_values.map((s) => [s.feature, s]));
  const flaggedCount = Object.keys(flagged).length;

  const onFilePicked = (schema: FeatureSchemaEntry, name: string) => {
    setFileNames((p) => ({ ...p, [schema.form_key]: name }));
    if (!flagged[schema.form_key]) toggleFlag(schema.form_key);
    if (!flagged[schema.form_key]?.evidenceType) {
      setEvidenceType(
        schema.form_key,
        schema.evidence_types[0] ?? "supporting_document",
      );
    }
  };

  return (
    <section
      className="rounded-xl border hairline bg-surface p-6 lg:p-7"
      aria-labelledby="new-evidence-title"
    >
      <header className="mb-5 flex items-center justify-between">
        <div>
          <div className="mb-1 text-[11px] uppercase tracking-[0.18em] text-accent">
            Path 02 · New evidence
          </div>
          <h2 id="new-evidence-title" className="display text-2xl">
            {ev.verbs.new_evidence_title}
          </h2>
          <p className="mt-2 max-w-xl text-sm text-ink-muted">
            {ev.verbs.new_evidence_sub} The validator reads your documents and
            derives the updated value before the model re-runs.
          </p>
        </div>
      </header>

      <ul className="space-y-3" role="list">
        {contestable.map((schema) => (
          <EvidenceRow
            key={schema.form_key}
            schema={schema}
            current={valuesByFeature.get(schema.feature)?.valueDisplay ?? "—"}
            fileName={fileNames[schema.form_key]}
            flagged={!!flagged[schema.form_key]}
            evidenceType={flagged[schema.form_key]?.evidenceType}
            onFilePicked={(name) => onFilePicked(schema, name)}
            onEvidence={(v) => setEvidenceType(schema.form_key, v)}
          />
        ))}
      </ul>

      <footer className="mt-7 flex items-center justify-between border-t hairline pt-5">
        <div className="text-xs text-ink-muted">
          {flaggedCount} {flaggedCount === 1 ? "document" : "documents"} attached
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => goto(2)} className="btn-ghost">
            Cancel
          </button>
          <button
            disabled={loading === "contest" || flaggedCount === 0}
            onClick={() => runContest()}
            className="btn-primary"
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
    </section>
  );
}

interface EvidenceRowProps {
  schema: FeatureSchemaEntry;
  current: string;
  fileName: string | undefined;
  flagged: boolean;
  evidenceType: string | undefined;
  onFilePicked: (name: string) => void;
  onEvidence: (v: string) => void;
}

function EvidenceRow({
  schema,
  current,
  fileName,
  flagged,
  evidenceType,
  onFilePicked,
  onEvidence,
}: EvidenceRowProps) {
  const options = schema.evidence_types.length > 0
    ? schema.evidence_types
    : ["supporting_document"];
  const inputRef = useRef<HTMLInputElement | null>(null);

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    onFilePicked(file.name);
    e.target.value = "";
  };

  return (
    <li
      className={`rounded-lg border px-4 py-4 transition-all ${flagged ? "border-ink bg-surface shadow-sm" : "hairline bg-cream-soft/40"}`}
    >
      <div className="mb-3 flex items-center justify-between gap-4">
        <div>
          <div className="text-sm font-medium">{schema.display_name}</div>
          <div className="text-xs text-ink-muted">
            On file: <span className="mono">{current}</span>
          </div>
        </div>
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
          aria-label={`${fileName ? "Replace" : "Upload"} evidence for ${schema.display_name}`}
        >
          {fileName ? "Replace file" : "Upload document"}
        </button>
      </div>

      {flagged && (
        <div className="grid grid-cols-[minmax(110px,130px)_1fr] items-center gap-x-4 gap-y-3 text-sm">
          <div className="text-ink-muted">Document</div>
          <div className="mono flex items-center gap-2 text-[13px]">
            <span className="h-2 w-2 rounded-full bg-good" aria-hidden />
            {fileName ?? "—"}
          </div>

          <label htmlFor={`ne-${schema.form_key}-evidence`} className="text-ink-muted">
            Evidence type
          </label>
          <select
            id={`ne-${schema.form_key}-evidence`}
            value={evidenceType ?? options[0]}
            onChange={(e) => onEvidence(e.target.value)}
            className="rounded border hairline bg-surface px-2.5 py-2 text-sm focus:border-ink focus:outline-none"
          >
            {options.map((o) => (
              <option key={o} value={o}>
                {o.replace(/_/g, " ").replace(/^(.)/, (c) => c.toUpperCase())}
              </option>
            ))}
          </select>

          {schema.hint && (
            <div className="col-span-2 mt-1 border-l-2 border-accent pl-3 text-[12px] text-ink-muted">
              <span className="font-medium text-ink">Hint.</span> {schema.hint}
            </div>
          )}
        </div>
      )}
    </li>
  );
}
