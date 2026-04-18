import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { useStore } from "../../store";
import type { FeatureSchemaEntry } from "../../types";
import type { Highlight } from "./highlights";

type SchemaWithPolicy = FeatureSchemaEntry & {
  correction_policy?: "user_editable" | "evidence_driven" | "locked";
};

interface Props {
  highlights: Highlight[];
}

function prettyEvidence(raw: string): string {
  return raw.replace(/_/g, " ").replace(/^(.)/, (c) => c.toUpperCase());
}

export function ContestFormPane({ highlights }: Props) {
  const ev = useStore((s) => s.evaluation);
  const flagged = useStore((s) => s.flaggedFields);
  const toggleFlag = useStore((s) => s.toggleFlag);
  const setCorrection = useStore((s) => s.setCorrection);
  const setEvidenceType = useStore((s) => s.setEvidenceType);
  const runContest = useStore((s) => s.runContest);
  const loading = useStore((s) => s.loading);
  const goto = useStore((s) => s.goto);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const rowRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const [uploaded, setUploaded] = useState<Record<string, string>>({});

  useEffect(() => {
    const onFocus = (e: Event) => {
      const ce = e as CustomEvent<{ formKey: string }>;
      const key = ce.detail?.formKey;
      if (!key) return;
      const row = rowRefs.current[key];
      if (!row) return;
      row.scrollIntoView({ behavior: "smooth", block: "center" });
      const reduce = window.matchMedia(
        "(prefers-reduced-motion: reduce)",
      ).matches;
      if (!reduce) {
        gsap.fromTo(
          row,
          { backgroundColor: "#F4EFE6" },
          {
            backgroundColor: "#FFFFFF",
            duration: 0.9,
            ease: "power2.out",
          },
        );
      }
    };
    window.addEventListener("hiring:focus-form-key", onFocus);
    return () => window.removeEventListener("hiring:focus-form-key", onFocus);
  }, []);

  if (!ev) return null;

  const schemaList = ev.feature_schema as SchemaWithPolicy[];
  const contestable = schemaList.filter((s) => s.contestable && !s.protected);
  const valuesByFeature = new Map(ev.shap_values.map((s) => [s.feature, s]));
  const flaggedCount = Object.keys(flagged).length;

  const handleToggle = (formKey: string) => {
    const wasFlagged = !!flagged[formKey];
    toggleFlag(formKey);
    if (!wasFlagged) {
      const match = highlights.find((h) => h.flaggedFeature === formKey);
      if (match) {
        window.dispatchEvent(
          new CustomEvent("hiring:scroll-to-highlight", {
            detail: { id: match.id },
          }),
        );
      }
    }
  };

  const fileInputs = useRef<Record<string, HTMLInputElement | null>>({});

  const openFilePicker = (formKey: string) => {
    fileInputs.current[formKey]?.click();
  };

  const onFilePicked = (formKey: string, file: File) => {
    setUploaded((p) => ({ ...p, [formKey]: file.name }));
    if (!flagged[formKey]) toggleFlag(formKey);
  };

  return (
    <div
      ref={containerRef}
      className="rounded-xl border hairline bg-surface p-[22px]"
    >
      <div className="mb-5 flex items-center justify-between">
        <div>
          <div className="mb-1 text-[10px] uppercase tracking-widest text-accent">
            Path 01 · Correction · Resume-linked
          </div>
          <h2 className="display text-2xl">{ev.verbs.correction_title}</h2>
        </div>
      </div>

      <div className="space-y-3">
        {contestable.map((schema) => {
          const policy = schema.correction_policy ?? "user_editable";
          const isFlagged = !!flagged[schema.form_key];
          const state = flagged[schema.form_key] ?? {};
          const currentShap = valuesByFeature.get(schema.feature);
          const currentDisplay = currentShap?.valueDisplay ?? "—";
          const options =
            schema.evidence_types.length > 0
              ? schema.evidence_types
              : ["Supporting document"];
          const linkedHls = highlights.filter(
            (h) => h.flaggedFeature === schema.form_key,
          );

          return (
            <div
              key={schema.form_key}
              ref={(el) => {
                rowRefs.current[schema.form_key] = el;
              }}
              data-form-row={schema.form_key}
              className={`rounded-lg border px-4 py-3.5 transition-all ${
                policy === "locked"
                  ? "hairline bg-cream-soft"
                  : isFlagged
                    ? "border-ink bg-surface shadow-[0_1px_0_rgba(0,0,0,0.02)]"
                    : "hairline bg-cream"
              }`}
            >
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2 text-sm font-medium">
                    {schema.display_name}
                    {policy === "evidence_driven" && (
                      <span className="pill">Evidence-driven</span>
                    )}
                    {policy === "locked" && (
                      <span className="pill pill-locked">Locked</span>
                    )}
                  </div>
                  <div className="text-xs text-ink-muted">
                    Currently: {currentDisplay}
                    {linkedHls.length > 0 && (
                      <>
                        {" "}
                        ·{" "}
                        <button
                          type="button"
                          onClick={() =>
                            window.dispatchEvent(
                              new CustomEvent("hiring:scroll-to-highlight", {
                                detail: { id: linkedHls[0].id },
                              }),
                            )
                          }
                          className="underline decoration-accent/40 underline-offset-2 hover:text-accent"
                        >
                          {linkedHls.length} resume{" "}
                          {linkedHls.length === 1 ? "highlight" : "highlights"}
                        </button>
                      </>
                    )}
                  </div>
                </div>
                {policy !== "locked" && (
                  <label
                    className={`flex cursor-pointer items-center gap-2 text-xs ${
                      isFlagged
                        ? "font-medium text-accent"
                        : "text-ink-muted"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={isFlagged}
                      onChange={() => handleToggle(schema.form_key)}
                      className="cursor-pointer accent-accent"
                    />
                    Contest
                  </label>
                )}
              </div>

              {policy === "locked" && (
                <div className="text-[11px] text-ink-muted">
                  This field isn't contestable via corrections.
                </div>
              )}

              {policy === "user_editable" && isFlagged && (
                <>
                  <div className="grid grid-cols-[130px_1fr] items-center gap-x-4 gap-y-2 text-sm">
                    <div className="text-ink-muted">Correct value</div>
                    <div className="flex items-center gap-2">
                      <input
                        value={(state.corrected as string) ?? ""}
                        onChange={(e) =>
                          setCorrection(schema.form_key, e.target.value)
                        }
                        placeholder={schema.hint_placeholder || "—"}
                        className="mono w-32 rounded border hairline bg-cream px-2 py-1.5 text-[13px] focus:border-ink focus:shadow-focus focus:outline-none"
                      />
                      {schema.unit && (
                        <span className="text-sm">{schema.unit}</span>
                      )}
                    </div>
                    <div className="text-ink-muted">Evidence</div>
                    <select
                      value={state.evidenceType ?? options[0]}
                      onChange={(e) =>
                        setEvidenceType(schema.form_key, e.target.value)
                      }
                      className="rounded border hairline bg-surface px-2 py-1.5 text-[13px] focus:border-ink focus:outline-none"
                    >
                      {options.map((o) => (
                        <option key={o} value={o}>
                          {prettyEvidence(o)}
                        </option>
                      ))}
                    </select>
                  </div>
                  {schema.hint && (
                    <div className="mt-3 border-l-2 border-accent pl-3 text-[11px] text-ink-muted">
                      <span className="font-medium text-ink">Hint.</span>{" "}
                      {schema.hint}
                    </div>
                  )}
                </>
              )}

              {policy === "evidence_driven" && (
                <>
                  <div className="flex items-center justify-between rounded-md border hairline bg-cream px-3 py-2.5">
                    <div className="flex items-center gap-2 text-[12.5px]">
                      {uploaded[schema.form_key] ? (
                        <>
                          <span className="h-1.5 w-1.5 rounded-full bg-good" />
                          <span className="mono text-ink">
                            {uploaded[schema.form_key]}
                          </span>
                        </>
                      ) : (
                        <span className="text-ink-muted">
                          No evidence attached
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <select
                        value={state.evidenceType ?? options[0]}
                        onChange={(e) =>
                          setEvidenceType(schema.form_key, e.target.value)
                        }
                        className="rounded border hairline bg-surface px-2 py-1 text-[12px] focus:border-ink focus:outline-none"
                      >
                        {options.map((o) => (
                          <option key={o} value={o}>
                            {prettyEvidence(o)}
                          </option>
                        ))}
                      </select>
                      <input
                        ref={(el) => {
                          fileInputs.current[schema.form_key] = el;
                        }}
                        type="file"
                        className="sr-only"
                        aria-hidden
                        tabIndex={-1}
                        onChange={(e) => {
                          const f = e.target.files?.[0];
                          if (f) onFilePicked(schema.form_key, f);
                          e.target.value = "";
                        }}
                      />
                      <button
                        type="button"
                        onClick={() => openFilePicker(schema.form_key)}
                        className="rounded border hairline bg-surface px-3 py-1 text-[11px] uppercase tracking-wider text-ink-muted transition-colors hover:text-ink"
                        aria-label={`${uploaded[schema.form_key] ? "Replace" : "Attach"} evidence for ${schema.display_name}`}
                      >
                        {uploaded[schema.form_key] ? "Replace" : "Upload evidence"}
                      </button>
                    </div>
                  </div>
                  <div className="mt-2 text-[11px] text-ink-muted">
                    Score will re-compute after validation.
                  </div>
                  {schema.hint && (
                    <div className="mt-2 border-l-2 border-accent pl-3 text-[11px] text-ink-muted">
                      <span className="font-medium text-ink">Hint.</span>{" "}
                      {schema.hint}
                    </div>
                  )}
                </>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-7 flex items-center justify-between border-t hairline pt-5">
        <div className="flex items-center gap-2 text-xs text-ink-muted">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-good" />
          Sync'd with resume · {flaggedCount}{" "}
          {flaggedCount === 1 ? "field" : "fields"} contested
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
                <span className="spinner" />
                <span>Re-evaluating…</span>
              </>
            ) : (
              "Re-evaluate →"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
