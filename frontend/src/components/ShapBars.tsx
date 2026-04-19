import type { ShapRow } from "../lib/api";

export function ShapBars({ shap, highlightFeature }: { shap: ShapRow[]; highlightFeature?: string }) {
  const rows = shap.filter((r) => !r.protected).sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution));
  const maxAbs = Math.max(0.001, ...rows.map((r) => Math.abs(r.contribution)));

  return (
    <div className="space-y-2">
      {rows.map((r) => {
        const pos = r.contribution >= 0;
        const pct = (Math.abs(r.contribution) / maxAbs) * 100;
        const isHi = highlightFeature === r.feature;
        return (
          <div key={r.feature} className={`grid grid-cols-[160px_1fr_100px] items-center gap-3 py-1 ${isHi ? "ring-1 ring-accent/40 rounded px-2 bg-accent/5" : ""}`}>
            <div className="text-[13px] truncate">
              <div className="font-medium">{r.display_name || r.feature}</div>
              <div className="mono text-[11px] text-ink-muted">{r.value_display ?? String(r.value)}</div>
            </div>
            <div className="relative h-6">
              <div className="absolute top-0 bottom-0 left-1/2 w-px bg-line" />
              {pos ? (
                <div className="absolute top-1 bottom-1 left-1/2 rounded-r bg-good/70" style={{ width: `${pct / 2}%` }} />
              ) : (
                <div className="absolute top-1 bottom-1 right-1/2 rounded-l bg-bad/70" style={{ width: `${pct / 2}%` }} />
              )}
            </div>
            <div className={`mono text-[12px] text-right ${pos ? "text-good" : "text-bad"}`}>
              {pos ? "+" : ""}{r.contribution.toFixed(3)}
            </div>
          </div>
        );
      })}
      <div className="mt-1 text-[11px] text-ink-muted flex justify-between">
        <span>← Pushed toward denial</span>
        <span>Pushed toward approval →</span>
      </div>
    </div>
  );
}
