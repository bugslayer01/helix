import { create } from "zustand";
import * as api from "./lib/api";

export type Stage = "intro" | "form" | "docs" | "submitting" | "decision";

interface UploadedDoc {
  id: string;
  doc_type: string;
  original_name: string;
  sha256: string;
  extracted: Record<string, unknown>;
  source: string;
  confidence: number;
}

interface State {
  stage: Stage;
  applicationId: string | null;
  applicantId: string | null;
  applicantName: string;
  dob: string;
  email: string;
  phone: string;
  amount: number;
  purpose: string;
  error: string | null;
  busy: boolean;
  uploads: UploadedDoc[];
  decision: any | null;
  contestUrl: string | null;

  setField: (k: "applicantName" | "dob" | "email" | "phone" | "purpose", v: string) => void;
  setAmount: (v: number) => void;
  goto: (stage: Stage) => void;
  reset: () => void;

  startApplication: () => Promise<void>;
  uploadDoc: (docType: string, file: File) => Promise<void>;
  submitForDecision: () => Promise<void>;
  requestContest: () => Promise<void>;
}

export const useStore = create<State>((set, get) => ({
  stage: "intro",
  applicationId: null,
  applicantId: null,
  applicantName: "",
  dob: "",
  email: "",
  phone: "",
  amount: 500000,
  purpose: "Home renovation",
  error: null,
  busy: false,
  uploads: [],
  decision: null,
  contestUrl: null,

  setField: (k, v) => set({ [k]: v } as any),
  setAmount: (v) => set({ amount: v }),
  goto: (stage) => set({ stage }),
  reset: () => set({
    stage: "intro", applicationId: null, applicantId: null,
    applicantName: "", dob: "", email: "", phone: "",
    amount: 500000, purpose: "Home renovation",
    error: null, busy: false, uploads: [], decision: null, contestUrl: null,
  }),

  async startApplication() {
    set({ busy: true, error: null });
    try {
      const s = get();
      const res = await api.startApplication({
        full_name: s.applicantName,
        dob: s.dob,
        email: s.email,
        phone: s.phone || undefined,
        amount: s.amount,
        purpose: s.purpose,
      });
      set({
        applicationId: res.application_id,
        applicantId: res.applicant_id,
        stage: "docs",
        busy: false,
      });
    } catch (e: any) {
      set({ error: e.message, busy: false });
    }
  },

  async uploadDoc(docType, file) {
    const { applicationId, uploads } = get();
    if (!applicationId) return;
    set({ busy: true, error: null });
    try {
      const res = await api.uploadDocument(applicationId, docType, file);
      set({
        uploads: [
          ...uploads,
          {
            id: res.document_id,
            doc_type: res.doc_type,
            original_name: file.name,
            sha256: res.sha256,
            extracted: res.extracted,
            source: res.source,
            confidence: res.confidence,
          },
        ],
        busy: false,
      });
    } catch (e: any) {
      set({ error: e.message, busy: false });
    }
  },

  async submitForDecision() {
    const { applicationId } = get();
    if (!applicationId) return;
    set({ busy: true, error: null, stage: "submitting" });
    try {
      const res = await api.submitApplication(applicationId);
      set({ decision: res.decision, stage: "decision", busy: false });
    } catch (e: any) {
      set({ error: e.message, busy: false, stage: "docs" });
    }
  },

  async requestContest() {
    const { applicationId } = get();
    if (!applicationId) return;
    set({ busy: true, error: null });
    try {
      const res = await api.requestContestLink(applicationId);
      set({ contestUrl: res.contest_url, busy: false });
    } catch (e: any) {
      set({ error: e.message, busy: false });
    }
  },
}));
