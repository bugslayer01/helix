import { create } from "zustand";
import * as api from "./lib/api";

export type Stage = "picker" | "intake_form" | "intake_docs" | "decision";

interface CaseSummary {
  id: string;
  full_name: string;
  amount: number;
  status: string;
  verdict: string | null;
  prob_bad: number | null;
  decided_at: number | null;
}

export interface DocUploadState {
  document_id: string;
  sha256: string;
  extracted: any;
  source?: string;
  confidence?: number;
  error?: string;
}

export type LoanDocType = "payslip" | "bank_statement" | "credit_report";

interface ApplicantForm {
  full_name: string;
  dob: string;
  email: string;
  phone: string;
  amount: number;
  purpose: string;
}

interface UploadedDocs {
  payslip: DocUploadState | null;
  bank_statement: DocUploadState | null;
  credit_report: DocUploadState | null;
}

interface State {
  stage: Stage;
  applicationId: string | null;
  cases: CaseSummary[];
  detail: any | null;
  decision: any | null;
  contestUrl: string | null;
  mailStatus: { ok: boolean; mailinator_inbox?: string; error?: string; skipped?: boolean } | null;
  error: string | null;
  busy: boolean;

  // Intake flow state
  applicantForm: ApplicantForm;
  uploadedDocs: UploadedDocs;
  intakeApplicationId: string | null;
  // per-slot busy guard so one slot upload doesn't block another
  uploadingDoc: Record<LoanDocType, boolean>;

  goto: (stage: Stage) => void;
  loadCases: () => Promise<void>;
  pickCase: (id: string) => Promise<void>;
  requestContest: () => Promise<void>;
  back: () => void;

  setApplicantField: <K extends keyof ApplicantForm>(key: K, value: ApplicantForm[K]) => void;
  startNewApplication: () => void;
  createApplication: () => Promise<void>;
  uploadLoanDoc: (docType: LoanDocType, file: File) => Promise<void>;
  submitLoanApplication: () => Promise<void>;
}

const BLANK_FORM: ApplicantForm = {
  full_name: "",
  dob: "",
  email: "",
  phone: "",
  amount: 500000,
  purpose: "",
};

const BLANK_DOCS: UploadedDocs = { payslip: null, bank_statement: null, credit_report: null };

export const useStore = create<State>((set, get) => ({
  stage: "picker",
  applicationId: null,
  cases: [],
  detail: null,
  decision: null,
  contestUrl: null,
  mailStatus: null,
  error: null,
  busy: false,

  applicantForm: { ...BLANK_FORM },
  uploadedDocs: { ...BLANK_DOCS },
  intakeApplicationId: null,
  uploadingDoc: { payslip: false, bank_statement: false, credit_report: false },

  goto(stage) { set({ stage }); },

  async loadCases() {
    set({ busy: true, error: null });
    try {
      const r = await api.listOperatorCases();
      set({ cases: r.cases as CaseSummary[], busy: false });
    } catch (e: any) {
      set({ error: e.message, busy: false });
    }
  },

  async pickCase(id) {
    set({ busy: true, error: null, applicationId: id, contestUrl: null, mailStatus: null });
    try {
      const detail = await api.getOperatorCase(id);
      const decision = (detail.decisions || []).slice(-1)[0] || null;
      set({
        busy: false,
        detail,
        decision,
        stage: "decision",
      });
    } catch (e: any) {
      set({ error: e.message, busy: false });
    }
  },

  async requestContest() {
    const { applicationId, busy, contestUrl } = get();
    if (!applicationId || busy || contestUrl) return;
    set({ busy: true, error: null });
    try {
      const r = await api.requestContestLink(applicationId);
      set({ contestUrl: r.contest_url, mailStatus: (r as any).email || null, busy: false });
    } catch (e: any) {
      set({ error: e.message, busy: false });
    }
  },

  back() {
    set({
      stage: "picker",
      applicationId: null,
      detail: null,
      decision: null,
      contestUrl: null,
      mailStatus: null,
      intakeApplicationId: null,
      applicantForm: { ...BLANK_FORM },
      uploadedDocs: { ...BLANK_DOCS },
      error: null,
    });
  },

  setApplicantField(key, value) {
    set({ applicantForm: { ...get().applicantForm, [key]: value } });
  },

  startNewApplication() {
    set({
      stage: "intake_form",
      applicantForm: { ...BLANK_FORM },
      uploadedDocs: { ...BLANK_DOCS },
      intakeApplicationId: null,
      error: null,
    });
  },

  async createApplication() {
    const { applicantForm, busy, intakeApplicationId } = get();
    if (busy || intakeApplicationId) return;
    set({ busy: true, error: null });
    try {
      const r = await api.startApplication({
        full_name: applicantForm.full_name.trim(),
        dob: applicantForm.dob,
        email: applicantForm.email.trim(),
        phone: applicantForm.phone.trim() || undefined,
        amount: applicantForm.amount,
        purpose: applicantForm.purpose.trim() || undefined,
      });
      set({
        intakeApplicationId: r.application_id,
        stage: "intake_docs",
        busy: false,
      });
    } catch (e: any) {
      set({ error: e.message, busy: false });
    }
  },

  async uploadLoanDoc(docType, file) {
    const { intakeApplicationId, uploadingDoc } = get();
    if (!intakeApplicationId) return;
    if (uploadingDoc[docType]) return;
    set({
      uploadingDoc: { ...uploadingDoc, [docType]: true },
      error: null,
    });
    try {
      const r = await api.uploadIntakeDoc(intakeApplicationId, docType, file);
      set({
        uploadedDocs: {
          ...get().uploadedDocs,
          [docType]: {
            document_id: r.document_id,
            sha256: r.sha256,
            extracted: r.extracted,
            source: r.source,
            confidence: r.confidence,
          },
        },
        uploadingDoc: { ...get().uploadingDoc, [docType]: false },
      });
    } catch (e: any) {
      set({
        uploadedDocs: {
          ...get().uploadedDocs,
          [docType]: {
            document_id: "",
            sha256: "",
            extracted: {},
            error: e.message,
          },
        },
        uploadingDoc: { ...get().uploadingDoc, [docType]: false },
      });
    }
  },

  async submitLoanApplication() {
    const { intakeApplicationId, busy } = get();
    if (!intakeApplicationId || busy) return;
    set({ busy: true, error: null });
    try {
      await api.submitApplication(intakeApplicationId);
      // hand off to the existing decision view via pickCase
      set({ busy: false });
      await get().pickCase(intakeApplicationId);
    } catch (e: any) {
      set({ error: e.message, busy: false });
    }
  },
}));
