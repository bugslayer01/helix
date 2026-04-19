import { useEffect, useState } from "react";
import { useStore } from "../store";
import * as api from "../lib/api";

export function HandoffView() {
  const token = useStore((s) => s.token);
  const dob = useStore((s) => s.dob);
  const setDob = useStore((s) => s.setDob);
  const open = useStore((s) => s.openSession);
  const busy = useStore((s) => s.busy);
  const error = useStore((s) => s.error);

  const [preview, setPreview] = useState<api.HandoffPreview | null>(null);
  const [verifying, setVerifying] = useState(true);
  const [previewError, setPreviewError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!token) { setVerifying(false); return; }
      try {
        const r = await api.previewHandoff(token);
        if (!cancelled) { setPreview(r); setVerifying(false); }
      } catch (e: any) {
        if (!cancelled) { setPreviewError(e.message); setVerifying(false); }
      }
    }
    run();
    return () => { cancelled = true; };
  }, [token]);

  if (!token) {
    return (
      <section className="mx-auto max-w-xl px-6 py-20">
        <div className="label mb-3">Handoff</div>
        <h1 className="display text-4xl mb-5">We need a contest link.</h1>
        <p className="text-ink-muted">
          This portal is only accessible via a signed link from your lender.
          Open the rejection email and click the "Contest this decision"
          button.
        </p>
      </section>
    );
  }

  if (verifying) {
    return (
      <section className="mx-auto max-w-xl px-6 py-20">
        <div className="label mb-3">Verifying</div>
        <h1 className="display text-4xl">Checking your contest link…</h1>
      </section>
    );
  }

  if (previewError) {
    return (
      <section className="mx-auto max-w-xl px-6 py-20">
        <div className="label mb-3">Handoff rejected</div>
        <h1 className="display text-4xl mb-4">This link isn't usable.</h1>
        <p className="text-ink-muted mb-4">{previewError}</p>
        <p className="text-sm text-ink-muted">Ask your lender to issue a fresh contest link.</p>
      </section>
    );
  }

  const hoursLeft = preview ? Math.max(0, Math.floor((preview.expires_at - Math.floor(Date.now() / 1000)) / 3600)) : 0;

  return (
    <section className="mx-auto max-w-md px-6 py-16">
      <div className="label mb-3">Secure handoff</div>
      <h1 className="display text-4xl leading-[1.1] mb-3">Confirm it's you.</h1>
      <p className="text-ink-muted mb-8">
        Your lender passed us a signed token identifying you as{" "}
        <span className="mono">{preview?.applicant_id}</span>
        {" "}for case{" "}
        <span className="mono">{preview?.case_id}</span>.{" "}
        Enter your date of birth to prove you're the person on the
        application. Link expires in {hoursLeft}h.
      </p>

      <div className="card p-5">
        <label className="label mb-2 block">Date of birth</label>
        <input
          type="date"
          className="input mono"
          value={dob}
          onChange={(e) => setDob(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") open(); }}
        />
        {error && (
          <div className="mt-4 rounded-md border border-accent/40 bg-accent/5 px-3 py-2 text-sm text-accent">{error}</div>
        )}
        <button className="btn-primary mt-5 w-full" disabled={!dob || busy} onClick={() => open()}>
          {busy ? <><span className="spinner" /> Opening contest…</> : "Open my contest →"}
        </button>
      </div>

      <div className="mt-6 text-[12px] text-ink-muted">
        GDPR Art. 22(3) · DPDP Section 11 · Your right to contest any fully-automated decision.
      </div>
    </section>
  );
}
