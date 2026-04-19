export function SubmittingView() {
  const steps = [
    "Reading your documents",
    "Extracting financial features",
    "Running underwriting model",
    "Computing explanations",
    "Producing decision",
  ];
  return (
    <section className="mx-auto max-w-xl px-6 py-16">
      <div className="label mb-3">Scoring in progress</div>
      <h1 className="display text-4xl mb-6">Holding still for a few seconds…</h1>
      <ul className="space-y-3 text-[15px] text-ink-muted">
        {steps.map((s, i) => (
          <li key={s} className="flex items-center gap-3">
            <span
              className="h-2 w-2 rounded-full bg-brand"
              style={{ animation: `pulse 1.6s ${i * 0.3}s ease-in-out infinite` }}
            />
            {s}
          </li>
        ))}
      </ul>
      <style>{`@keyframes pulse { 0%, 100% { opacity: 0.25 } 50% { opacity: 1 } }`}</style>
    </section>
  );
}
