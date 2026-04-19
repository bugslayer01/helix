import { useState } from "react";
import { useStore } from "../store";

const MAILINATOR = "@mailinator.com";
const LOCAL_RX = /^[A-Za-z0-9._+\-]+$/;

export function NewLoanApplicationView() {
  const form = useStore((s) => s.applicantForm);
  const setField = useStore((s) => s.setApplicantField);
  const createApplication = useStore((s) => s.createApplication);
  const goto = useStore((s) => s.goto);
  const busy = useStore((s) => s.busy);
  const error = useStore((s) => s.error);

  const initialLocal = form.email.endsWith(MAILINATOR) ? form.email.slice(0, -MAILINATOR.length) : "";
  const [local, setLocal] = useState(initialLocal);

  const localOk = LOCAL_RX.test(local) && local.length > 0;
  const fullEmail = localOk ? `${local}${MAILINATOR}` : "";

  const updateEmail = (v: string) => {
    const cleaned = v.replace(MAILINATOR, "").replace(/@.*$/, "");
    setLocal(cleaned);
    setField("email", cleaned ? `${cleaned}${MAILINATOR}` : "");
  };

  const canSubmit =
    form.full_name.trim().length > 2 &&
    !!form.dob &&
    localOk &&
    form.amount > 0;

  return (
    <section className="mx-auto max-w-2xl px-6 py-14">
      <div className="label mb-3">New loan application</div>
      <h1 className="display text-4xl mb-3">Tell us about the applicant.</h1>
      <p className="text-ink-muted mb-6 max-w-xl">
        Enter the applicant's identity and the loan they're requesting. We'll
        then collect a payslip, bank statement, and credit report before the
        underwriting model scores the file.
      </p>
      <div className="card p-5 space-y-4">
        <div>
          <label className="label mb-2 block">Full name</label>
          <input
            className="input"
            placeholder="Asha Verma"
            value={form.full_name}
            onChange={(e) => setField("full_name", e.target.value)}
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label mb-2 block">Date of birth</label>
            <input
              className="input"
              type="date"
              value={form.dob}
              onChange={(e) => setField("dob", e.target.value)}
            />
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
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label mb-2 block">Phone (optional)</label>
            <input
              className="input"
              placeholder="+91 98xxxxxxxx"
              value={form.phone}
              onChange={(e) => setField("phone", e.target.value)}
            />
          </div>
          <div>
            <label className="label mb-2 block">Amount (INR)</label>
            <input
              className="input"
              type="number"
              step={10000}
              min={0}
              value={form.amount}
              onChange={(e) => setField("amount", Number(e.target.value) || 0)}
            />
          </div>
        </div>
        <div>
          <label className="label mb-2 block">Purpose</label>
          <input
            className="input"
            placeholder="Home renovation, wedding, business expansion…"
            value={form.purpose}
            onChange={(e) => setField("purpose", e.target.value)}
          />
        </div>
        {fullEmail && (
          <div className="text-[11px] text-ink-muted">
            Applicant inbox: <span className="mono text-ink">{fullEmail}</span>
          </div>
        )}
        {error && (
          <div className="rounded-md border border-bad/40 bg-bad/5 px-3 py-2 text-sm text-bad">{error}</div>
        )}
        <div className="flex items-center justify-between pt-2">
          <button className="btn-ghost" onClick={() => goto("picker")}>← Back</button>
          <button
            className="btn-primary"
            disabled={!canSubmit || busy}
            onClick={() => createApplication()}
          >
            {busy ? <><span className="spinner" /> Creating…</> : "Create application →"}
          </button>
        </div>
      </div>
    </section>
  );
}
