import { useEffect } from "react";
import { useHiring } from "../../store_hiring";

export function PostingsView() {
  const postings = useHiring((s) => s.postings);
  const load = useHiring((s) => s.loadPostings);
  const select = useHiring((s) => s.selectPosting);
  const goto = useHiring((s) => s.goto);

  useEffect(() => { load(); }, []);

  return (
    <section className="mx-auto max-w-3xl px-6 py-14">
      <div className="label mb-3">Hiring · Open roles</div>
      <h1 className="display text-4xl mb-3">Pick a role to screen candidates for.</h1>
      <p className="text-ink-muted mb-8 max-w-xl">
        Each role holds a job description the LLM judge compares every candidate against.
        Pick one to upload a resume, or post a new role.
      </p>
      <div className="card overflow-x-auto mb-6">
        <table className="w-full min-w-[560px] text-[14px]">
          <thead className="text-ink-muted">
            <tr className="border-b hairline">
              <th className="text-left px-4 py-3">Role</th>
              <th className="text-left px-4 py-3">Posting ID</th>
              <th className="text-left px-4 py-3">Posted</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {postings.map((p) => (
              <tr key={p.id} className="border-b hairline hover:bg-brand-soft/30">
                <td className="px-4 py-3 font-medium">{p.title}</td>
                <td className="px-4 py-3 mono text-[12px] text-ink-muted">{p.id}</td>
                <td className="px-4 py-3">{new Date(p.created_at * 1000).toLocaleDateString()}</td>
                <td className="px-4 py-3 text-right"><button className="btn-primary text-[13px] py-1.5" onClick={() => select(p)}>Open →</button></td>
              </tr>
            ))}
            {postings.length === 0 && (
              <tr><td colSpan={4} className="px-4 py-6 text-sm text-ink-muted">No postings yet. Create one or run <span className="mono">make seed-hiring</span>.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      <button className="btn-primary" onClick={() => goto("newPosting")}>+ Post a new role</button>
    </section>
  );
}
