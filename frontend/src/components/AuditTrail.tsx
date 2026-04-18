import { useEffect, useRef } from "react";
import gsap from "gsap";
import { useStore } from "../store";

export function AuditTrail() {
  const entries = useStore((s) => s.auditEntries);
  const step = useStore((s) => s.step);
  const listRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!listRef.current) return;
    const items = listRef.current.querySelectorAll<HTMLDivElement>(".audit-item");
    gsap.fromTo(
      items,
      { opacity: 0, x: 10 },
      {
        opacity: 1,
        x: 0,
        duration: 0.35,
        stagger: 0.06,
        ease: "power2.out",
      },
    );
  }, [entries.length]);

  return (
    <aside className="sticky top-[96px] self-start h-[calc(100vh-120px)]">
      <div className="flex h-full flex-col rounded-xl border hairline bg-surface">
        <div className="flex items-center justify-between border-b hairline px-5 py-4">
          <div>
            <div className="display text-base leading-tight">Activity on this case</div>
            <div className="mt-0.5 text-[10px] uppercase tracking-[0.2em] text-ink-muted">
              Tamper-evident · SHA-256
            </div>
          </div>
          <div className="h-2 w-2 animate-pulse rounded-full bg-good" />
        </div>

        <div
          ref={listRef}
          className="scrollable flex-1 space-y-4 overflow-y-auto px-5 py-4"
        >
          {entries.map((e) => {
            const hashColor = e.kind === "success" ? "text-good" : "text-ink-muted";
            return (
              <div key={e.id} className="audit-item text-sm">
                <div className="flex items-start justify-between gap-2">
                  <div className="font-medium leading-tight">{e.title}</div>
                  <div className="mono shrink-0 mt-0.5 text-[10px] text-ink-muted">
                    {e.timestamp}
                  </div>
                </div>
                <div className="mt-1 text-xs text-ink-muted">{e.subtitle}</div>
                <div className={`mono mt-1 text-[10px] ${hashColor}`}>{e.hash}</div>
              </div>
            );
          })}
          {step < 4 && (
            <div className="border-t hairline pt-3 text-xs italic opacity-40">
              Awaiting next action…
            </div>
          )}
        </div>

        <div className="flex items-center justify-between border-t hairline px-5 py-3 text-[10px] uppercase tracking-[0.2em] text-ink-muted">
          <span>Chain verified</span>
          <button className="text-xs normal-case tracking-normal text-ink-muted underline transition-colors hover:text-ink">
            Copy full log
          </button>
        </div>
      </div>
    </aside>
  );
}
