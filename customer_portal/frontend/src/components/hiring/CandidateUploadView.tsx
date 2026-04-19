import { useRef } from "react";
import { useHiring } from "../../store_hiring";

export function CandidateUploadView() {
  const s = useHiring();
  const ref = useRef<HTMLInputElement | null>(null);
  const canPick = s.candidate.full_name.trim().length > 2 && s.candidate.dob && s.candidate.email.includes("@");
  return (
    <section className="mx-auto max-w-2xl px-6 py-14">
      <div className="label mb-3">Screen a candidate · {s.selectedPostingTitle}</div>
      <h1 className="display text-4xl mb-3">Upload the candidate's resume.</h1>
      <p className="text-ink-muted mb-6 max-w-xl">
        Tell us who this candidate is, then attach their resume PDF. The LLM judge
        scores resume-vs-JD and returns its reasoning instantly.
      </p>
      <div className="card p-5 space-y-4">
        <div>
          <label className="label mb-2 block">Candidate full name</label>
          <input className="input" placeholder="Asha Verma" value={s.candidate.full_name} onChange={(e) => s.setCandidate("full_name", e.target.value)} />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label mb-2 block">Date of birth</label>
            <input className="input" type="date" value={s.candidate.dob} onChange={(e) => s.setCandidate("dob", e.target.value)} />
          </div>
          <div>
            <label className="label mb-2 block">Email</label>
            <input className="input" type="email" placeholder="asha@example.com" value={s.candidate.email} onChange={(e) => s.setCandidate("email", e.target.value)} />
          </div>
        </div>
        <div>
          <label className="label mb-2 block">Resume PDF</label>
          <input
            ref={ref}
            type="file"
            accept=".pdf,application/pdf"
            className="sr-only"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) s.uploadResume(f);
              e.target.value = "";
            }}
          />
          <button
            className="btn-ghost w-full py-3"
            disabled={!canPick || s.busy}
            onClick={() => ref.current?.click()}
          >
            {s.busy ? <><span className="spinner" /> Scoring…</> : "Choose resume PDF + score"}
          </button>
          {!canPick && (
            <div className="mt-2 text-[12px] text-ink-muted">
              Fill in candidate name, DOB, and email above to enable file pick.
            </div>
          )}
        </div>
        {s.error && <div className="rounded-md border border-bad/40 bg-bad/5 px-3 py-2 text-sm text-bad">{s.error}</div>}
        <div className="pt-2"><button className="btn-ghost" onClick={() => s.goto("postings")}>← All postings</button></div>
      </div>
    </section>
  );
}
