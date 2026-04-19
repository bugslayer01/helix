import { create } from "zustand";
import * as api from "./lib/api_hiring";

export type HiringStage = "postings" | "newPosting" | "candidateUpload" | "decision";

interface State {
  stage: HiringStage;
  postings: api.Posting[];
  selectedPostingId: string | null;
  selectedPostingTitle: string;
  selectedPostingJd: string;
  newTitle: string;
  newJd: string;
  candidate: { full_name: string; dob: string; email: string };
  applicationId: string | null;
  decision: any | null;
  contestUrl: string | null;
  mailStatus: { ok: boolean; mailinator_inbox?: string; error?: string; skipped?: boolean } | null;
  busy: boolean;
  error: string | null;

  goto(stage: HiringStage): void;
  loadPostings(): Promise<void>;
  setNewTitle(v: string): void;
  setNewJd(v: string): void;
  setCandidate(k: keyof State["candidate"], v: string): void;
  createPosting(): Promise<void>;
  selectPosting(p: api.Posting): void;
  uploadResume(file: File): Promise<void>;
  requestContest(): Promise<void>;
  reset(): void;
}

export const useHiring = create<State>((set, get) => ({
  stage: "postings",
  postings: [],
  selectedPostingId: null,
  selectedPostingTitle: "",
  selectedPostingJd: "",
  newTitle: "",
  newJd: "",
  candidate: { full_name: "", dob: "", email: "" },
  applicationId: null,
  decision: null,
  contestUrl: null,
  mailStatus: null,
  busy: false,
  error: null,

  goto(stage) { set({ stage, error: null }); },
  setNewTitle(v) { set({ newTitle: v }); },
  setNewJd(v) { set({ newJd: v }); },
  setCandidate(k, v) { set({ candidate: { ...get().candidate, [k]: v } }); },

  async loadPostings() {
    set({ busy: true, error: null });
    try { const r = await api.listPostings(); set({ postings: r.postings, busy: false }); }
    catch (e: any) { set({ error: e.message, busy: false }); }
  },

  async createPosting() {
    const { newTitle, newJd } = get();
    set({ busy: true, error: null });
    try {
      const r = await api.createPosting(newTitle, newJd);
      set({ busy: false, selectedPostingId: r.posting_id, selectedPostingTitle: r.title, selectedPostingJd: newJd, stage: "candidateUpload", newTitle: "", newJd: "" });
    } catch (e: any) { set({ error: e.message, busy: false }); }
  },

  selectPosting(p) {
    set({ selectedPostingId: p.id, selectedPostingTitle: p.title, selectedPostingJd: p.jd_text || "", stage: "candidateUpload" });
  },

  async uploadResume(file) {
    const { selectedPostingId, candidate } = get();
    if (!selectedPostingId) return;
    set({ busy: true, error: null });
    try {
      const r = await api.submitCandidate(selectedPostingId, candidate, file);
      set({ busy: false, applicationId: r.application_id, decision: r.decision, stage: "decision" });
    } catch (e: any) { set({ error: e.message, busy: false }); }
  },

  async requestContest() {
    const { applicationId } = get();
    if (!applicationId) return;
    set({ busy: true, error: null });
    try {
      const r = await api.requestContestLink(applicationId);
      set({ contestUrl: r.contest_url, mailStatus: (r as any).email || null, busy: false });
    } catch (e: any) { set({ error: e.message, busy: false }); }
  },

  reset() { set({ stage: "postings", selectedPostingId: null, selectedPostingTitle: "", selectedPostingJd: "", candidate: { full_name: "", dob: "", email: "" }, applicationId: null, decision: null, contestUrl: null, mailStatus: null, error: null }); },
}));
