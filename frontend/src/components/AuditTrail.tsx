import { useEffect, useState } from "react";
import { useStore } from "../store";
import * as api from "../lib/api";

interface Entry {
  id: number;
  action: string;
  title?: string | null;
  subtitle?: string | null;
  full_hash: string;
  created_at: number;
  kind?: string;
}

const ACTION_LABELS: Record<string, string> = {
  case_opened: "Contest opened",
  evidence_uploaded: "Evidence uploaded",
  validator_ran: "Evidence Shield ran",
  evidence_rejected: "Evidence rejected",
  proposal_validated: "Proposal validated",
  contest_submitted: "Contest submitted",
  model_reran: "Model re-evaluated",
  verdict_computed: "Verdict computed",
  webhook_dispatched: "Verdict dispatched",
  webhook_delivered: "Verdict delivered",
  webhook_failed: "Verdict delivery failed",
  case_revoked: "Case revoked",
  review_requested: "Human review requested",
};

export function AuditTrail() {
  const caseId = useStore((s) => s.caseId);
  const [entries, setEntries] = useState<Entry[]>([]);

  useEffect(() => {
    if (!caseId) return;
    let cancelled = false;
    async function load() {
      try {
        const r = await api.getAudit(caseId!);
        if (!cancelled) setEntries(r.entries as Entry[]);
      } catch { /* silent */ }
    }
    load();
    const id = setInterval(load, 2500);
    return () => { cancelled = true; clearInterval(id); };
  }, [caseId]);

  if (!caseId) return null;

  return (
    <aside className="sticky top-[96px] self-start h-[calc(100vh-120px)]">
      <div className="flex h-full flex-col rounded-xl border hairline bg-surface">
        <div className="flex items-center justify-between border-b hairline px-5 py-4">
          <div>
            <div className="display text-base leading-tight">Activity on this case</div>
            <div className="mt-0.5 label">Tamper-evident · SHA-256</div>
          </div>
          <div className="h-2 w-2 animate-pulse rounded-full bg-good" />
        </div>

        <div className="scrollable flex-1 space-y-3 overflow-y-auto px-5 py-4">
          {entries.length === 0 ? (
            <div className="text-sm text-ink-muted italic">Awaiting first event…</div>
          ) : (
            entries.map((e) => (
              <div key={e.id} className="text-sm">
                <div className="flex items-start justify-between gap-2">
                  <div className="font-medium leading-tight">{e.title || ACTION_LABELS[e.action] || e.action}</div>
                  <div className="mono shrink-0 mt-0.5 text-[10px] text-ink-muted">
                    {new Date(e.created_at * 1000).toLocaleTimeString()}
                  </div>
                </div>
                {e.subtitle && <div className="mt-1 text-xs text-ink-muted">{e.subtitle}</div>}
                <div className="mono mt-1 text-[10px] text-ink-muted">0x{e.full_hash.slice(0, 12)}…</div>
              </div>
            ))
          )}
        </div>
      </div>
    </aside>
  );
}
