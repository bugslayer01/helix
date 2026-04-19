const BASE = "/api/v1";

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    let detail: any;
    try {
      detail = await res.json();
    } catch {
      detail = { detail: { error: { message: res.statusText } } };
    }
    const err = detail?.detail?.error || detail?.error;
    throw new Error(err?.message || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export interface HandoffPreview {
  case_id: string;
  applicant_id: string;
  issuer: string;
  decision: string;
  expires_at: number;
}

export interface SnapshotDecision {
  verdict: string;
  prob_bad: number;
  decided_at?: number;
}

export interface ShapRow {
  feature: string;
  display_name?: string;
  value?: number | string;
  value_display?: string;
  contribution: number;
  contestable?: boolean;
  protected?: boolean;
}

export interface Snapshot {
  features: Record<string, number>;
  decision: SnapshotDecision;
  shap: ShapRow[];
  model_version: string;
}

export interface ContestOpenResp {
  case_id: string;
  snapshot: {
    applicant: { display_name: string; dob_hash: string };
    decision: SnapshotDecision;
    features: Record<string, number>;
    shap: ShapRow[];
    top_reasons: string[];
    model_version: string;
    intake_docs: Array<{ doc_type: string; original_name: string }>;
  };
}

export interface CaseResp {
  case_id: string;
  status: string;
  applicant_display: string;
  external_ref: string;
  snapshot: Snapshot;
}

export interface CheckRow {
  name: string;
  passed: boolean;
  severity: "low" | "medium" | "high";
  detail: string;
  data?: any;
}

export interface EvidenceRow {
  id: string;
  target_feature: string;
  doc_type: string;
  extracted: Record<string, unknown>;
  extracted_value: number | null;
  uploaded_at: number;
  overall: "accepted" | "flagged" | "rejected" | null;
  summary: string | null;
  checks: CheckRow[];
}

export interface UploadResp {
  evidence_id: string;
  doc_type: string;
  extracted_value: number | null;
  extracted_fields: Record<string, unknown>;
  extraction_source: string;
  extraction_confidence: number;
  validation: {
    overall: "accepted" | "flagged" | "rejected";
    summary: string;
    checks: CheckRow[];
  };
  proposal_id: string | null;
}

export interface OutcomeDelta {
  feature: string;
  display_name: string;
  old: number;
  new: number;
  evidence_id: string;
  contribution_old: number;
  contribution_new: number;
}

export interface SubmitResp {
  case_id: string;
  outcome: "flipped" | "held";
  new_decision: { verdict: string; prob_bad: number };
  new_features: Record<string, number>;
  new_shap: ShapRow[];
  delta: OutcomeDelta[];
  webhook_id: string;
}

export async function previewHandoff(token: string): Promise<HandoffPreview> {
  return call("/contest/session/preview", { method: "POST", body: JSON.stringify({ token }) });
}

export async function logout(): Promise<void> {
  await call("/contest/logout", { method: "POST" });
}

export async function openContest(token: string, dob: string): Promise<ContestOpenResp> {
  return call("/contest/open", { method: "POST", body: JSON.stringify({ token, dob }) });
}

export async function getCase(): Promise<CaseResp> {
  return call("/contest/case");
}

export async function getSession(): Promise<{ session_id: string; case_id: string; status: string; applicant_display: string; external_ref: string }> {
  return call("/contest/session");
}

export async function uploadEvidence(
  targetFeature: string,
  docType: string,
  opts: { file?: File | null; rebuttalText?: string | null },
): Promise<UploadResp> {
  if (!opts.file && !opts.rebuttalText) {
    throw new Error("Provide a file or rebuttal text.");
  }
  const fd = new FormData();
  fd.append("target_feature", targetFeature);
  fd.append("doc_type", docType);
  if (opts.file) fd.append("file", opts.file);
  if (opts.rebuttalText) fd.append("rebuttal_text", opts.rebuttalText);
  const res = await fetch(`${BASE}/contest/evidence`, { method: "POST", body: fd, credentials: "include" });
  if (!res.ok) {
    let body: any;
    try { body = await res.json(); } catch { body = {}; }
    throw new Error(body?.detail?.error?.message || res.statusText);
  }
  return res.json();
}

export async function listEvidence(): Promise<{ evidence: EvidenceRow[]; proposals: Array<{ id: string; feature: string; original_value: number; proposed_value: number; evidence_id: string; status: string }> }> {
  return call("/contest/evidence");
}

export async function deleteEvidence(id: string): Promise<void> {
  await call(`/contest/evidence/${id}`, { method: "DELETE" });
}

export async function submitContest(): Promise<SubmitResp> {
  return call("/contest/submit", { method: "POST" });
}

export async function getOutcome(): Promise<any> {
  return call("/contest/outcome");
}

export async function requestReview(reason: string, statement: string): Promise<any> {
  return call("/contest/request-review", {
    method: "POST",
    body: JSON.stringify({ review_reason: reason, user_statement: statement }),
  });
}

export async function getAudit(caseId: string): Promise<{ case_id: string; entries: any[] }> {
  return call(`/audit/${caseId}`);
}

export async function verifyAudit(caseId: string): Promise<{ ok: boolean; rows: number; head: string | null; broken_at_row?: number }> {
  return call(`/audit/${caseId}/verify`);
}
