import { useStore } from "../store";

export function ProfileCard() {
  const ev = useStore((s) => s.evaluation);
  if (!ev) return null;

  const valueByFeature = new Map(ev.shap_values.map((s) => [s.feature, s]));
  const schemaByFeature = new Map(ev.feature_schema.map((s) => [s.feature, s]));

  return (
    <aside className="space-y-4">
      <div className="mb-2 text-[10px] uppercase tracking-[0.2em] text-ink-muted">
        Your profile
      </div>

      {ev.profile_groups.map((group) => (
        <div key={group.id} className="rounded-[10px] border hairline bg-surface px-4 py-4">
          <div className="mb-2 flex items-center justify-between">
            <div className="text-xs uppercase tracking-wider text-ink-muted">
              {group.title}
            </div>
            {group.locked && (
              <span className="pill pill-locked">
                {group.locked_hint ?? "Not used to decide"}
              </span>
            )}
          </div>

          {group.field_keys.map((key, i) => {
            const shap = valueByFeature.get(key);
            const schema = schemaByFeature.get(key);
            if (!schema) return null;
            const display = shap?.valueDisplay ?? "—";
            const concern = shap && !shap.protected && shap.contribution < -0.25;
            return (
              <div
                key={key}
                className={`flex items-baseline justify-between py-2 ${i === 0 ? "" : "border-t border-cream-soft"}`}
              >
                <span className="text-sm">{schema.display_name}</span>
                <span className="flex items-center gap-2 text-sm">
                  {display}
                  {concern && <span className="pill pill-concern">High</span>}
                </span>
              </div>
            );
          })}
        </div>
      ))}

      <div className="flex items-center gap-2 px-1 text-[11px] text-ink-muted">
        <span className="lock-dot" aria-hidden />
        Protected — not contestable
      </div>
    </aside>
  );
}
