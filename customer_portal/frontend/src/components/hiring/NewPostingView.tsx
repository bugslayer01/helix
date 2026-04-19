import { useHiring } from "../../store_hiring";

export function NewPostingView() {
  const s = useHiring();
  const canSubmit = s.newTitle.trim().length > 2 && s.newJd.trim().length > 30;
  return (
    <section className="mx-auto max-w-2xl px-6 py-14">
      <div className="label mb-3">New role</div>
      <h1 className="display text-4xl mb-3">Describe the role.</h1>
      <p className="text-ink-muted mb-6 max-w-xl">
        Paste your real job description. The LLM judge extracts the must-have skills,
        years of experience, and required degree from this text.
      </p>
      <div className="card p-5 space-y-4">
        <div>
          <label className="label mb-2 block">Role title</label>
          <input className="input" placeholder="Senior Backend Engineer" value={s.newTitle} onChange={(e) => s.setNewTitle(e.target.value)} />
        </div>
        <div>
          <label className="label mb-2 block">Job description (paste full text)</label>
          <textarea
            rows={14}
            className="input"
            placeholder={"About the role…\nResponsibilities…\nRequirements:\n- 5+ years backend exp\n- Python, Postgres, Kubernetes\n- Bachelor's degree"}
            value={s.newJd}
            onChange={(e) => s.setNewJd(e.target.value)}
          />
          <div className="text-[11px] text-ink-muted mt-1 text-right">{s.newJd.length} chars</div>
        </div>
        {s.error && <div className="rounded-md border border-bad/40 bg-bad/5 px-3 py-2 text-sm text-bad">{s.error}</div>}
        <div className="flex items-center justify-between pt-2">
          <button className="btn-ghost" onClick={() => s.goto("postings")}>← Back</button>
          <button className="btn-primary" disabled={!canSubmit || s.busy} onClick={() => s.createPosting()}>
            {s.busy ? <><span className="spinner" /> Posting…</> : "Post role + screen candidates →"}
          </button>
        </div>
      </div>
    </section>
  );
}
