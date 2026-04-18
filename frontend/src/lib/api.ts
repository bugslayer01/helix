import type {
  ContestPath,
  ContestResult,
  DomainsCatalog,
  EvaluationResult,
  FeatureDelta,
  ReasonCategory,
  ReviewResult,
  ShapEntry,
} from "../types";

const USE_MOCK =
  typeof window !== "undefined" &&
  (new URLSearchParams(window.location.search).get("mock") === "1" ||
    import.meta.env.VITE_USE_MOCK === "1");

const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

/* ---- snake_case → camelCase for SHAP and deltas ---- */

interface RawShap {
  feature: string;
  display_name: string;
  value: number | string;
  value_display?: string;
  contribution: number;
  contestable: boolean;
  protected: boolean;
}

interface RawDelta {
  feature: string;
  display_name: string;
  old_value: number | string;
  new_value: number | string;
  old_value_display?: string;
  new_value_display?: string;
  old_contribution: number;
  new_contribution: number;
  contribution_delta: number;
}

function toShap(row: RawShap): ShapEntry {
  return {
    feature: row.feature,
    displayName: row.display_name,
    value: row.value,
    valueDisplay: row.value_display ?? String(row.value),
    contribution: row.contribution,
    contestable: row.contestable,
    protected: row.protected,
  };
}

function toDelta(row: RawDelta): FeatureDelta {
  return {
    feature: row.feature,
    displayName: row.display_name,
    old_value: row.old_value,
    new_value: row.new_value,
    old_value_display: row.old_value_display ?? String(row.old_value),
    new_value_display: row.new_value_display ?? String(row.new_value),
    old_contribution: row.old_contribution,
    new_contribution: row.new_contribution,
    contribution_delta: row.contribution_delta,
  };
}

function transformEvaluation(raw: unknown): EvaluationResult {
  const r = raw as Omit<EvaluationResult, "shap_values"> & {
    shap_values: RawShap[];
  };
  return { ...r, shap_values: r.shap_values.map(toShap) };
}

function transformContest(raw: unknown): ContestResult {
  const r = raw as {
    case_id: string;
    contest_path: ContestPath;
    before: { decision: "approved" | "denied"; confidence: number; shap_values: RawShap[] };
    after: { decision: "approved" | "denied"; confidence: number; shap_values: RawShap[] } | null;
    delta: {
      decision_flipped: boolean;
      confidence_change: number;
      feature_deltas: RawDelta[];
    } | null;
    anomaly_flags: string[];
    audit_entry_id: string;
    audit_hash: string;
  };
  return {
    case_id: r.case_id,
    contest_path: r.contest_path,
    before: {
      decision: r.before.decision,
      confidence: r.before.confidence,
      shap_values: r.before.shap_values.map(toShap),
    },
    after: r.after
      ? {
          decision: r.after.decision,
          confidence: r.after.confidence,
          shap_values: r.after.shap_values.map(toShap),
        }
      : null,
    delta: r.delta
      ? {
          decision_flipped: r.delta.decision_flipped,
          confidence_change: r.delta.confidence_change,
          feature_deltas: r.delta.feature_deltas.map(toDelta),
        }
      : null,
    anomaly_flags: r.anomaly_flags ?? [],
    audit_entry_id: r.audit_entry_id,
    audit_hash: r.audit_hash,
  };
}

/* ---- Mock builder (for ?mock=1) ---- */

async function mockEval(): Promise<EvaluationResult> {
  return fetchJson(`${BASE}/evaluate/lookup`, "POST", {
    application_reference: "RC-2024-A4F2-9E31",
    date_of_birth: "1990-03-12",
  }).then(transformEvaluation);
}

async function fetchJson(url: string, method: string, body?: unknown): Promise<unknown> {
  const res = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`${res.status} ${txt}`);
  }
  return res.json();
}

/* ---- Public API ---- */

export async function loginLookup(ref: string, dob: string): Promise<EvaluationResult> {
  if (USE_MOCK) return mockEval();
  const raw = await fetchJson(`${BASE}/evaluate/lookup`, "POST", {
    application_reference: ref,
    date_of_birth: dob,
  });
  return transformEvaluation(raw);
}

export async function submitContest(
  caseId: string,
  path: ContestPath,
  reasonCategory: ReasonCategory,
  updates: Record<string, number | string>,
): Promise<ContestResult> {
  const raw = await fetchJson(`${BASE}/contest`, "POST", {
    case_id: caseId,
    contest_path: path,
    reason_category: reasonCategory,
    updates,
  });
  return transformContest(raw);
}

export async function requestHumanReview(
  caseId: string,
  reviewReason: string,
  statement: string,
): Promise<ReviewResult> {
  const raw = (await fetchJson(`${BASE}/review`, "POST", {
    case_id: caseId,
    review_reason: reviewReason,
    user_statement: statement,
  })) as ReviewResult;
  return raw;
}

export async function listDomains(): Promise<DomainsCatalog> {
  const raw = (await fetchJson(`${BASE}/evaluate/domains`, "GET")) as DomainsCatalog;
  return raw;
}

/* ---- Propose / validate / apply (multi-stage contest flow) ---- */

export type ProposalStatus = "validating" | "validated" | "rejected";

export interface ProposalPayload {
  feature: string;
  form_key: string;
  policy: "user_editable" | "evidence_driven";
  proposed_value?: number | null;
  evidence_type: string;
  evidence_filename?: string;
  evidence_hash?: string;
}

export interface ProposalState {
  feature: string;
  form_key: string;
  status: ProposalStatus;
  resolved_value: number | null;
  validation_note: string | null;
}

export interface ContestStatus {
  contest_id: string;
  status: "validating" | "validated" | "partially_rejected" | "rejected" | "applied";
  proposals: ProposalState[];
}

export interface ProposeResponse {
  contest_id: string;
  status: "validating";
  proposals: { feature: string; status: ProposalStatus; estimated_validation_seconds: number }[];
  audit_entry_id: string;
  audit_hash: string;
}

export async function proposeContest(
  caseId: string,
  path: ContestPath,
  reasonCategory: ReasonCategory,
  proposals: ProposalPayload[],
  userContext?: string,
): Promise<ProposeResponse> {
  return (await fetchJson(`${BASE}/contest/propose`, "POST", {
    case_id: caseId,
    contest_path: path,
    reason_category: reasonCategory,
    user_context: userContext,
    proposals,
  })) as ProposeResponse;
}

export async function getContestStatus(contestId: string): Promise<ContestStatus> {
  return (await fetchJson(
    `${BASE}/contest/${contestId}/status`,
    "GET",
  )) as ContestStatus;
}

export async function applyContest(
  contestId: string,
  applyRejectedAsSkip = false,
): Promise<ContestResult & { contest_id?: string; applied_status?: string }> {
  const raw = await fetchJson(`${BASE}/contest/${contestId}/apply`, "POST", {
    apply_rejected_as_skip: applyRejectedAsSkip,
  });
  return transformContest(raw) as ContestResult & {
    contest_id?: string;
    applied_status?: string;
  };
}
