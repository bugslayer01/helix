import { create } from "zustand";
import * as api from "./lib/api";
import type {
  CheckRow,
  ContestOpenResp,
  EvidenceRow,
  OutcomeDelta,
  ShapRow,
  UploadResp,
} from "./lib/api";
import type { Stage } from "./types";

interface State {
  stage: Stage;
  token: string | null;
  dob: string;
  error: string | null;
  busy: boolean;

  caseId: string | null;
  applicantDisplay: string;
  externalRef: string;
  decisionVerdict: "approved" | "denied";
  decisionProbBad: number;
  features: Record<string, number>;
  shap: ShapRow[];
  topReasons: string[];
  modelVersion: string;
  intakeDocs: Array<{ doc_type: string; original_name: string }>;

  evidence: EvidenceRow[];
  lastUpload: UploadResp | null;

  submitting: boolean;
  outcome: {
    outcome: "flipped" | "held";
    new_verdict: string;
    new_prob_bad: number;
    delta: OutcomeDelta[];
    new_shap: ShapRow[];
  } | null;
  webhookId: string | null;
  auditVerified: { ok: boolean; rows: number; head: string | null } | null;

  setDob(v: string): void;
  setToken(t: string | null): void;
  goto(stage: Stage): void;
  reset(): void;

  tryPreview(token: string): Promise<void>;
  openSession(): Promise<void>;
  loadCase(): Promise<void>;
  refreshEvidence(): Promise<void>;
  upload(feature: string, docType: string, file: File): Promise<UploadResp | null>;
  removeEvidence(id: string): Promise<void>;
  submit(): Promise<void>;
  verifyAudit(): Promise<void>;
  requestReview(reason: string, statement: string): Promise<boolean>;
}

function tokenFromUrl(): string | null {
  try {
    const p = new URLSearchParams(window.location.search);
    return p.get("t");
  } catch {
    return null;
  }
}

export const useStore = create<State>((set, get) => ({
  stage: "handoff",
  token: tokenFromUrl(),
  dob: "",
  error: null,
  busy: false,

  caseId: null,
  applicantDisplay: "",
  externalRef: "",
  decisionVerdict: "denied",
  decisionProbBad: 0,
  features: {},
  shap: [],
  topReasons: [],
  modelVersion: "",
  intakeDocs: [],

  evidence: [],
  lastUpload: null,

  submitting: false,
  outcome: null,
  webhookId: null,
  auditVerified: null,

  setDob(v) { set({ dob: v }); },
  setToken(t) { set({ token: t }); },
  goto(stage) { set({ stage }); },
  reset() {
    set({
      stage: "handoff", token: tokenFromUrl(), dob: "", error: null, busy: false,
      caseId: null, applicantDisplay: "", externalRef: "",
      decisionVerdict: "denied", decisionProbBad: 0,
      features: {}, shap: [], topReasons: [], modelVersion: "", intakeDocs: [],
      evidence: [], lastUpload: null,
      submitting: false, outcome: null, webhookId: null, auditVerified: null,
    });
  },

  async tryPreview(token) {
    set({ busy: true, error: null });
    try {
      const r = await api.previewHandoff(token);
      set({ token, busy: false, applicantDisplay: "", externalRef: r.case_id });
    } catch (e: any) {
      set({ error: e.message || "Could not verify contest link.", busy: false });
    }
  },

  async openSession() {
    const { token, dob } = get();
    if (!token || !dob) return;
    set({ busy: true, error: null });
    try {
      const r: ContestOpenResp = await api.openContest(token, dob);
      set({
        busy: false,
        caseId: r.case_id,
        applicantDisplay: r.snapshot.applicant.display_name,
        externalRef: r.case_id,
        decisionVerdict: (r.snapshot.decision.verdict as any) || "denied",
        decisionProbBad: r.snapshot.decision.prob_bad,
        features: r.snapshot.features,
        shap: r.snapshot.shap,
        topReasons: r.snapshot.top_reasons,
        modelVersion: r.snapshot.model_version,
        intakeDocs: r.snapshot.intake_docs || [],
        stage: "understand",
      });
    } catch (e: any) {
      set({ error: e.message, busy: false });
    }
  },

  async loadCase() {
    set({ busy: true, error: null });
    try {
      const r = await api.getCase();
      set({
        busy: false,
        caseId: r.case_id,
        externalRef: r.external_ref,
        applicantDisplay: r.applicant_display,
        decisionVerdict: (r.snapshot.decision.verdict as any) || "denied",
        decisionProbBad: r.snapshot.decision.prob_bad,
        features: r.snapshot.features,
        shap: r.snapshot.shap,
        modelVersion: r.snapshot.model_version,
      });
    } catch (e: any) {
      set({ error: e.message, busy: false });
    }
  },

  async refreshEvidence() {
    try {
      const r = await api.listEvidence();
      set({ evidence: r.evidence });
    } catch { /* silent */ }
  },

  async upload(feature, docType, file) {
    set({ busy: true, error: null });
    try {
      const r = await api.uploadEvidence(feature, docType, file);
      await get().refreshEvidence();
      set({ busy: false, lastUpload: r });
      return r;
    } catch (e: any) {
      set({ error: e.message, busy: false });
      return null;
    }
  },

  async removeEvidence(id) {
    try {
      await api.deleteEvidence(id);
      await get().refreshEvidence();
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  async submit() {
    set({ submitting: true, error: null });
    try {
      const r = await api.submitContest();
      set({
        submitting: false,
        outcome: {
          outcome: r.outcome,
          new_verdict: r.new_decision.verdict,
          new_prob_bad: r.new_decision.prob_bad,
          delta: r.delta,
          new_shap: r.new_shap,
        },
        webhookId: r.webhook_id,
        stage: "outcome",
      });
    } catch (e: any) {
      set({ submitting: false, error: e.message });
    }
  },

  async verifyAudit() {
    const id = get().caseId;
    if (!id) return;
    try {
      const r = await api.verifyAudit(id);
      set({ auditVerified: r });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  async requestReview(reason, statement) {
    set({ busy: true, error: null });
    try {
      await api.requestReview(reason, statement);
      set({ busy: false, stage: "outcome", outcome: null });
      return true;
    } catch (e: any) {
      set({ error: e.message, busy: false });
      return false;
    }
  },
}));

export type { CheckRow };
