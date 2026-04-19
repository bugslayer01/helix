import { useRef, useState } from "react";
import { useHiring } from "../../store_hiring";

const MAILINATOR = "@mailinator.com";
const LOCAL_RX = /^[A-Za-z0-9._+\-]+$/;

export function CandidateUploadView() {
  const s = useHiring();
  const ref = useRef<HTMLInputElement | null>(null);

  // Email is split: user types only the local part; we append @mailinator.com.
  const initialLocal = s.candidate.email.endsWith(MAILINATOR)
    ? s.candidate.email.slice(0, -MAILINATOR.length)
    : "";
  const [local, setLocal] = useState(initialLocal);

  const localOk = LOCAL_RX.test(local) && local.length > 0;
  const fullEmail = localOk ? `${local}${MAILINATOR}` : "";
  const canPick =
    s.candidate.full_name.trim().length > 2 &&
    !!s.candidate.dob &&
    localOk;

  const updateEmail = (v: string) => {
    const cleaned = v.replace(MAILINATOR, "").replace(/@.*$/, "");
    setLocal(cleaned);
    s.setCandidate("email", cleaned ? `${cleaned}${MAILINATOR}` : "");
  };

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
            <label className="label mb-2 block">Email (mailinator)</label>
            <div className="flex items-stretch rounded-md border hairline bg-surface focus-within:border-brand">
              <input
                className="flex-1 min-w-0 bg-transparent px-3 py-2 text-base text-ink placeholder:text-ink-muted/60 focus:outline-none"
                placeholder="asha"
                value={local}
                onChange={(e) => updateEmail(e.target.value)}
                aria-label="Mailinator inbox name"
              />
              <span className="flex items-center px-3 mono text-[13px] text-ink-muted bg-cream-soft border-l hairline rounded-r-md">
                {MAILINATOR}
              </span>
            </div>
            <div className="mt-1 text-[11px] text-ink-muted">
              Demo restriction: only mailinator.com inboxes (judges can read the mail without auth).
              {local && !localOk && <span className="text-bad ml-1">Use letters/digits/._+- only.</span>}
            </div>
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
              Fill in candidate name, DOB, and a mailinator email to enable file pick.
            </div>
          )}
          {fullEmail && (
            <div className="mt-2 text-[11px] text-ink-muted">
              Will email contest link to <span className="mono text-ink">{fullEmail}</span> on denial.
            </div>
          )}
        </div>
        {s.error && <div className="rounded-md border border-bad/40 bg-bad/5 px-3 py-2 text-sm text-bad">{s.error}</div>}
        <div className="pt-2"><button className="btn-ghost" onClick={() => s.goto("postings")}>← All postings</button></div>
      </div>
    </section>
  );
}
