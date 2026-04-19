import { create } from "zustand";
import * as api from "./lib/api";

export type Stage = "picker" | "decision";

interface CaseSummary {
  id: string;
  full_name: string;
  amount: number;
  status: string;
  verdict: string | null;
  prob_bad: number | null;
  decided_at: number | null;
}

interface State {
  stage: Stage;
  applicationId: string | null;
  cases: CaseSummary[];
  detail: any | null;
  decision: any | null;
  contestUrl: string | null;
  error: string | null;
  busy: boolean;

  goto: (stage: Stage) => void;
  loadCases: () => Promise<void>;
  pickCase: (id: string) => Promise<void>;
  requestContest: () => Promise<void>;
  back: () => void;
}

export const useStore = create<State>((set, get) => ({
  stage: "picker",
  applicationId: null,
  cases: [],
  detail: null,
  decision: null,
  contestUrl: null,
  error: null,
  busy: false,

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
    set({ busy: true, error: null, applicationId: id, contestUrl: null });
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
    const { applicationId } = get();
    if (!applicationId) return;
    set({ busy: true, error: null });
    try {
      const r = await api.requestContestLink(applicationId);
      set({ contestUrl: r.contest_url, busy: false });
    } catch (e: any) {
      set({ error: e.message, busy: false });
    }
  },

  back() {
    set({ stage: "picker", applicationId: null, detail: null, decision: null, contestUrl: null });
  },
}));
