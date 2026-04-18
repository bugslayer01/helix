import { create } from "zustand";
import type {
  AuditEntry,
  ContestPath,
  ContestResult,
  DomainsCatalog,
  EvaluationResult,
  ReasonCategory,
  ReviewResult,
  Step,
} from "./types";
import {
  applyContest,
  getContestStatus,
  listDomains,
  loginLookup,
  proposeContest,
  requestHumanReview,
  type ProposalPayload,
  type ProposalState,
} from "./lib/api";

type FlaggedFields = Record<
  string,
  { corrected?: string | number; evidenceType?: string }
>;

export type ContestPhase =
  | "idle"
  | "proposing"
  | "validating"
  | "applying"
  | "applied"
  | "rejected"
  | "error";

export interface ContestFlow {
  phase: ContestPhase;
  contestId: string | null;
  proposals: ProposalState[];
  message: string | null;
}

interface RecourseState {
  step: Step;
  applicantRef: string;
  dob: { day: string; month: string; year: string };

  loading: "idle" | "login" | "contest" | "review";
  error: string | null;

  evaluation: EvaluationResult | null;
  contestResult: ContestResult | null;
  reviewResult: ReviewResult | null;

  selectedPath: ContestPath | null;
  reasonCategory: ReasonCategory | null;
  flaggedFields: FlaggedFields;
  humanReviewText: string;
  humanReviewReason: string;

  auditEntries: AuditEntry[];
  domains: DomainsCatalog | null;

  contestFlow: ContestFlow;

  login: () => Promise<void>;
  loginWith: (ref: string, dob: string) => Promise<void>;
  signOut: () => void;
  goto: (step: Step) => void;
  setRef: (ref: string) => void;
  setDob: (segment: "day" | "month" | "year", value: string) => void;

  selectPath: (p: ContestPath) => void;
  setReasonCategory: (c: ReasonCategory | null) => void;
  toggleFlag: (key: string) => void;
  setCorrection: (key: string, value: string | number) => void;
  setEvidenceType: (key: string, type: string) => void;
  setHumanReviewText: (t: string) => void;
  setHumanReviewReason: (r: string) => void;
  runContest: () => Promise<void>;
  runHumanReview: () => Promise<void>;
  resetContestFlow: () => void;

  fetchDomains: () => Promise<void>;
}

const INITIAL_CONTEST_FLOW: ContestFlow = {
  phase: "idle",
  contestId: null,
  proposals: [],
  message: null,
};

const POLL_INTERVAL_MS = 500;
const POLL_TIMEOUT_MS = 30_000;

async function pollUntilResolved(
  contestId: string,
  onSnapshot: (s: Awaited<ReturnType<typeof getContestStatus>>) => void,
) {
  const start = performance.now();
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const snap = await getContestStatus(contestId);
    onSnapshot(snap);
    if (
      snap.status === "validated" ||
      snap.status === "rejected" ||
      snap.status === "partially_rejected" ||
      snap.status === "applied"
    ) {
      return snap;
    }
    if (performance.now() - start > POLL_TIMEOUT_MS) {
      throw new Error("Evidence validation timed out");
    }
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
  }
}

function timestampedAudit(
  id: string,
  title: string,
  subtitle: string,
  hash: string,
  kind: AuditEntry["kind"] = "info",
): AuditEntry {
  const d = new Date();
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const stamp = `${months[d.getMonth()]} ${String(d.getDate()).padStart(2, "0")} · ${String(
    d.getHours(),
  ).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  return { id, case_id: "", timestamp: stamp, title, subtitle, hash, kind };
}

function initialAudit(ev: EvaluationResult): AuditEntry[] {
  return [
    {
      id: "ae-open",
      case_id: ev.case_id,
      timestamp: "Apr 08 · 09:02",
      title: "Case opened",
      subtitle: `${ev.domain} · applicant submitted features`,
      hash: "0x" + ev.model_version_hash.replace(/[^0-9a-f]/gi, "").slice(0, 12),
      kind: "info",
    },
    {
      id: "ae-eval",
      case_id: ev.case_id,
      timestamp: "Apr 08 · 09:02",
      title: `Evaluated · ${ev.decision === "approved" ? ev.verbs.approved_label : ev.verbs.denied_label}`,
      subtitle: `confidence ${ev.confidence.toFixed(2)} · notice emailed`,
      hash:
        "0x" +
        (ev.model_version_hash + ev.case_id)
          .replace(/[^0-9a-f]/gi, "")
          .slice(-12),
      kind: "info",
    },
    timestampedAudit("ae-signin", "Signed in", "reference + DOB verified", "0x4d1f8a10b220"),
  ];
}

function computeInitialFlags(ev: EvaluationResult): FlaggedFields {
  // Pre-flag the top 2 negative-contribution contestable features so the demo
  // lands on "here's what you should correct" without clicks.
  const contestableNegative = ev.shap_values
    .filter((s) => s.contestable && !s.protected)
    .filter((s) => s.contribution < 0)
    .sort((a, b) => a.contribution - b.contribution)
    .slice(0, 2);
  const schemaByFeature = new Map(ev.feature_schema.map((s) => [s.feature, s]));
  const suggestionsByFeature = new Map(
    ev.suggested_evidence.map((s) => [s.feature, s]),
  );
  const out: FlaggedFields = {};
  for (const entry of contestableNegative) {
    const schema = schemaByFeature.get(entry.feature);
    if (!schema) continue;
    const suggestion = suggestionsByFeature.get(entry.feature);
    const target = suggestion?.target_value_hint;
    out[schema.form_key] = {
      corrected: target !== undefined ? String(target) : "",
      evidenceType: schema.evidence_types[0] ?? "",
    };
  }
  return out;
}

export const useStore = create<RecourseState>((set, get) => ({
  step: 0,
  applicantRef: "RC-2024-A4F2-9E31",
  dob: { day: "12", month: "03", year: "1990" },

  loading: "idle",
  error: null,

  evaluation: null,
  contestResult: null,
  reviewResult: null,

  selectedPath: null,
  reasonCategory: null,
  flaggedFields: {},
  humanReviewText: "",
  humanReviewReason: "",

  auditEntries: [],
  domains: null,

  contestFlow: INITIAL_CONTEST_FLOW,

  login: async () => {
    const state = get();
    const dobIso = `${state.dob.year}-${state.dob.month.padStart(2, "0")}-${state.dob.day.padStart(2, "0")}`;
    await get().loginWith(state.applicantRef, dobIso);
  },

  loginWith: async (ref, dob) => {
    set({ loading: "login", error: null });
    try {
      const evaluation = await loginLookup(ref, dob);
      set({
        evaluation,
        step: 1,
        loading: "idle",
        auditEntries: initialAudit(evaluation),
        flaggedFields: computeInitialFlags(evaluation),
        contestResult: null,
        reviewResult: null,
        selectedPath: null,
        reasonCategory: null,
        humanReviewText: "",
        humanReviewReason: "",
      });
    } catch (e: unknown) {
      set({
        loading: "idle",
        error: e instanceof Error ? e.message : "Unable to look up case",
      });
    }
  },

  signOut: () => {
    set({
      step: 0,
      evaluation: null,
      contestResult: null,
      reviewResult: null,
      selectedPath: null,
      reasonCategory: null,
      humanReviewText: "",
      humanReviewReason: "",
      auditEntries: [],
      flaggedFields: {},
      loading: "idle",
      error: null,
    });
  },

  goto: (step) => set({ step }),

  setRef: (applicantRef) => set({ applicantRef }),
  setDob: (segment, value) =>
    set((s) => ({ dob: { ...s.dob, [segment]: value } })),

  selectPath: (selectedPath) => set({ selectedPath }),
  setReasonCategory: (reasonCategory) => set({ reasonCategory }),
  toggleFlag: (key) =>
    set((s) => {
      const next = { ...s.flaggedFields };
      if (next[key]) delete next[key];
      else next[key] = {};
      return { flaggedFields: next };
    }),
  setCorrection: (key, corrected) =>
    set((s) => ({
      flaggedFields: {
        ...s.flaggedFields,
        [key]: { ...(s.flaggedFields[key] ?? {}), corrected },
      },
    })),
  setEvidenceType: (key, evidenceType) =>
    set((s) => ({
      flaggedFields: {
        ...s.flaggedFields,
        [key]: { ...(s.flaggedFields[key] ?? {}), evidenceType },
      },
    })),
  setHumanReviewText: (humanReviewText) => set({ humanReviewText }),
  setHumanReviewReason: (humanReviewReason) => set({ humanReviewReason }),

  resetContestFlow: () => set({ contestFlow: INITIAL_CONTEST_FLOW }),

  runContest: async () => {
    const state = get();
    if (!state.evaluation || !state.selectedPath) return;
    if (state.selectedPath === "human_review") return;

    const schemaByForm = new Map(
      state.evaluation.feature_schema.map((s) => [s.form_key, s]),
    );
    const proposals: ProposalPayload[] = [];
    const invalid: string[] = [];

    for (const [formKey, entry] of Object.entries(state.flaggedFields)) {
      const schema = schemaByForm.get(formKey);
      if (!schema) continue;
      if (schema.correction_policy === "locked") continue;

      const policy =
        schema.correction_policy === "evidence_driven"
          ? "evidence_driven"
          : "user_editable";

      const evidenceType = entry.evidenceType ?? schema.evidence_types[0];
      if (!evidenceType) {
        invalid.push(`${schema.display_name} is missing an evidence type`);
        continue;
      }

      if (policy === "user_editable") {
        const raw = entry.corrected;
        if (raw === undefined || raw === "" || raw === null) {
          invalid.push(`${schema.display_name} is missing a proposed value`);
          continue;
        }
        const num = Number(raw);
        if (!Number.isFinite(num)) {
          invalid.push(`${schema.display_name} proposed value is not a number`);
          continue;
        }
        let clamped = num;
        if (schema.min !== undefined && schema.min !== null && clamped < schema.min) clamped = schema.min;
        if (schema.max !== undefined && schema.max !== null && clamped > schema.max) clamped = schema.max;

        // Backend expects ratios in 0..1 for DebtRatio + RevolvingUtilization;
        // users type 0..100 here, server will divide by 100 if > 1.
        proposals.push({
          feature: schema.feature,
          form_key: formKey,
          policy,
          proposed_value: clamped,
          evidence_type: evidenceType,
        });
      } else {
        proposals.push({
          feature: schema.feature,
          form_key: formKey,
          policy,
          evidence_type: evidenceType,
        });
      }
    }

    if (proposals.length === 0) {
      set({
        error: invalid.length > 0 ? invalid.join(", ") : "Flag at least one field to contest",
      });
      return;
    }

    set({
      error: null,
      loading: "contest",
      contestFlow: {
        phase: "proposing",
        contestId: null,
        proposals: proposals.map((p) => ({
          feature: p.feature,
          form_key: p.form_key,
          status: "validating",
          resolved_value: null,
          validation_note: null,
        })),
        message: invalid.length > 0 ? invalid.join(" · ") : null,
      },
    });

    try {
      const propose = await proposeContest(
        state.evaluation.case_id,
        state.selectedPath,
        state.reasonCategory ?? "other",
        proposals,
      );

      set((s) => ({
        contestFlow: {
          phase: "validating",
          contestId: propose.contest_id,
          proposals: s.contestFlow.proposals,
          message: null,
        },
        auditEntries: [
          ...s.auditEntries,
          timestampedAudit(
            "ae-evidence-" + Date.now(),
            "Evidence submitted for validation",
            `${proposals.length} proposal${proposals.length === 1 ? "" : "s"} queued`,
            propose.audit_hash,
            "info",
          ),
        ],
      }));

      // Poll status until terminal.
      const done = await pollUntilResolved(propose.contest_id, (snapshot) => {
        set({
          contestFlow: {
            phase: "validating",
            contestId: snapshot.contest_id,
            proposals: snapshot.proposals,
            message: null,
          },
        });
      });

      if (done.status === "rejected") {
        set({
          loading: "idle",
          contestFlow: {
            phase: "rejected",
            contestId: done.contest_id,
            proposals: done.proposals,
            message: "All proposed changes were rejected by the validator.",
          },
          error: "Evidence rejected. See validation notes per field.",
        });
        return;
      }

      // validated OR partially_rejected → apply the validated subset.
      set({
        contestFlow: {
          phase: "applying",
          contestId: done.contest_id,
          proposals: done.proposals,
          message: null,
        },
      });

      const applyRejectedAsSkip = done.status === "partially_rejected";
      const result = await applyContest(done.contest_id, applyRejectedAsSkip);

      const flipped = result.after?.decision !== result.before.decision;
      const finalDecision = result.after?.decision ?? result.before.decision;
      const entry = timestampedAudit(
        "ae-contest-" + Date.now(),
        `Re-evaluated · ${finalDecision === "approved" ? state.evaluation.verbs.approved_label : state.evaluation.verbs.denied_label}`,
        `${state.reasonCategory ?? "other"} · confidence ${result.before.confidence.toFixed(2)} → ${result.after?.confidence?.toFixed(2) ?? "—"}`,
        result.audit_hash,
        flipped ? "success" : "info",
      );

      set((s) => ({
        contestResult: result,
        loading: "idle",
        step: 4,
        auditEntries: [...s.auditEntries, entry],
        contestFlow: {
          phase: "applied",
          contestId: done.contest_id,
          proposals: done.proposals,
          message: null,
        },
      }));
    } catch (e: unknown) {
      set({
        loading: "idle",
        error: e instanceof Error ? e.message : "Contest submission failed",
        contestFlow: { ...get().contestFlow, phase: "error", message: null },
      });
    }
  },

  runHumanReview: async () => {
    const state = get();
    if (!state.evaluation) return;
    set({ loading: "review", error: null });
    try {
      const result = await requestHumanReview(
        state.evaluation.case_id,
        state.humanReviewReason || "other",
        state.humanReviewText,
      );
      const entry = timestampedAudit(
        "ae-review-" + Date.now(),
        "Queued for human review",
        `reason: ${state.humanReviewReason || "other"} · no model re-run`,
        result.audit_hash,
        "success",
      );
      set((s) => ({
        reviewResult: result,
        loading: "idle",
        step: 4,
        auditEntries: [...s.auditEntries, entry],
      }));
    } catch (e: unknown) {
      set({
        loading: "idle",
        error: e instanceof Error ? e.message : "Review request failed",
      });
    }
  },

  fetchDomains: async () => {
    try {
      const d = await listDomains();
      set({ domains: d });
    } catch {
      /* ignore */
    }
  },
}));
