import { useApp } from "../store_app";
import { DomainSwitcher } from "./DomainSwitcher";

export function Header() {
  const domain = useApp((s) => s.domain);
  const view = useApp((s) => s.view);
  const setView = useApp((s) => s.setView);

  return (
    <header className="border-b hairline bg-surface">
      <div className="mx-auto flex max-w-shell items-center justify-between gap-4 px-4 py-4 sm:px-8 sm:py-5">
        <button onClick={() => setView("applicant")} className="flex items-center gap-3 text-ink hover:text-brand min-w-0 text-left">
          <span aria-hidden className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand">
            <span className="h-2.5 w-2.5 rounded-full bg-surface" />
          </span>
          <span className="min-w-0">
            <span className="display block text-lg leading-none">{domain === "hiring" ? "HiringCo" : "LenderCo"}</span>
            <span className="label block mt-1 hidden sm:block">{domain === "hiring" ? "Talent screening · Internal" : "Retail lending · India"}</span>
          </span>
        </button>
        <div className="flex items-center gap-3">
          <DomainSwitcher />
          <nav className="flex items-center gap-2 text-sm sm:gap-3">
            <button
              onClick={() => setView("applicant")}
              className={view === "applicant" ? "text-brand font-medium" : "text-ink-muted hover:text-brand"}
            >
              {domain === "hiring" ? "Recruit" : "Apply"}
            </button>
            <span className="text-ink-muted" aria-hidden>·</span>
            <button
              onClick={() => setView("operator")}
              className={view === "operator" ? "text-brand font-medium" : "text-ink-muted hover:text-brand"}
            >
              Operator
            </button>
          </nav>
        </div>
      </div>
    </header>
  );
}
