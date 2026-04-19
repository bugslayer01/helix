import { useStore } from "../store";

export function IntroView() {
  const goto = useStore((s) => s.goto);
  return (
    <section className="mx-auto max-w-2xl px-6 py-16">
      <div className="label mb-4">Personal loan</div>
      <h1 className="display text-5xl leading-[1.05] mb-5">
        Same-day loan decisions, powered by an audited model.
      </h1>
      <p className="text-lg text-ink-muted mb-10 max-w-xl">
        Submit three documents. Our underwriting model scores your application
        on ten independently auditable factors, with a written explanation
        delivered in seconds. If we decline, you have a right to contest.
      </p>

      <div className="card p-6 mb-8">
        <div className="label mb-2">How it works</div>
        <ol className="grid grid-cols-1 gap-4 sm:grid-cols-3 text-sm">
          <li>
            <div className="display text-brand text-xl mb-1">1</div>
            <div className="font-medium mb-1">Tell us about you</div>
            <div className="text-ink-muted text-[13px]">Name, date of birth, how much you need.</div>
          </li>
          <li>
            <div className="display text-brand text-xl mb-1">2</div>
            <div className="font-medium mb-1">Upload documents</div>
            <div className="text-ink-muted text-[13px]">Payslip, bank statement, credit report.</div>
          </li>
          <li>
            <div className="display text-brand text-xl mb-1">3</div>
            <div className="font-medium mb-1">Get a decision</div>
            <div className="text-ink-muted text-[13px]">Approved or declined with reasons you can challenge.</div>
          </li>
        </ol>
      </div>

      <div className="flex items-center gap-3">
        <button className="btn-primary" onClick={() => goto("form")}>
          Start a new application →
        </button>
        <a href="/?view=operator" className="btn-ghost">Operator console</a>
      </div>
      <p className="mt-6 text-[12px] text-ink-muted">
        Fully compliant with DPDP §11 and GDPR Art. 22(3). Every automated
        decline may be contested and re-evaluated.
      </p>
    </section>
  );
}
