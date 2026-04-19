import { useStore } from "../store";

export function FormView() {
  const s = useStore();
  const canSubmit = s.applicantName.trim().length > 2 && s.dob && s.email.includes("@") && s.amount > 0;

  return (
    <section className="mx-auto max-w-xl px-6 py-12">
      <div className="label mb-3">Step 1 of 3 · About you</div>
      <h1 className="display text-4xl mb-8">Tell us who's applying.</h1>

      <div className="space-y-5">
        <div>
          <label className="label mb-2 block">Full legal name</label>
          <input
            className="input"
            placeholder="Priya Sharma"
            value={s.applicantName}
            onChange={(e) => s.setField("applicantName", e.target.value)}
            autoFocus
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label mb-2 block">Date of birth</label>
            <input
              className="input"
              type="date"
              value={s.dob}
              onChange={(e) => s.setField("dob", e.target.value)}
            />
          </div>
          <div>
            <label className="label mb-2 block">Phone (optional)</label>
            <input
              className="input"
              inputMode="numeric"
              placeholder="+91 …"
              value={s.phone}
              onChange={(e) => s.setField("phone", e.target.value)}
            />
          </div>
        </div>
        <div>
          <label className="label mb-2 block">Email</label>
          <input
            className="input"
            type="email"
            placeholder="you@example.com"
            value={s.email}
            onChange={(e) => s.setField("email", e.target.value)}
          />
        </div>
        <div className="grid grid-cols-[1fr_180px] gap-4">
          <div>
            <label className="label mb-2 block">Loan amount (₹)</label>
            <input
              className="input mono"
              type="number"
              min={10000}
              step={10000}
              value={s.amount}
              onChange={(e) => s.setAmount(Number(e.target.value) || 0)}
            />
          </div>
          <div>
            <label className="label mb-2 block">Purpose</label>
            <select className="input" value={s.purpose} onChange={(e) => s.setField("purpose", e.target.value)}>
              <option>Home renovation</option>
              <option>Education</option>
              <option>Medical</option>
              <option>Debt consolidation</option>
              <option>Wedding</option>
              <option>Other</option>
            </select>
          </div>
        </div>
      </div>

      {s.error && (
        <div className="mt-5 rounded-md border border-bad/40 bg-bad/5 px-3 py-2 text-sm text-bad">{s.error}</div>
      )}

      <div className="mt-8 flex items-center justify-between">
        <button className="btn-ghost" onClick={() => s.goto("intro")}>← Back</button>
        <button
          className="btn-primary"
          disabled={!canSubmit || s.busy}
          onClick={() => s.startApplication()}
        >
          {s.busy ? <><span className="spinner" /> Starting…</> : "Continue to documents →"}
        </button>
      </div>
    </section>
  );
}
