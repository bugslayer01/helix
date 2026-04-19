import { DomainSwitcher } from "./DomainSwitcher";

export function Header({ operatorMode, domain }: { operatorMode: boolean; domain: "loans" | "hiring" }) {
  return (
    <header className="border-b hairline bg-surface">
      <div className="mx-auto flex max-w-shell items-center justify-between gap-4 px-4 py-4 sm:px-8 sm:py-5">
        <a href="/" className="flex items-center gap-3 text-ink hover:text-brand min-w-0">
          <span aria-hidden className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand">
            <span className="h-2.5 w-2.5 rounded-full bg-surface" />
          </span>
          <span className="min-w-0">
            <span className="display block text-lg leading-none">LenderCo</span>
            <span className="label block mt-1 hidden sm:block">{domain === "hiring" ? "Hiring · Internal" : "Retail lending · India"}</span>
          </span>
        </a>
        <div className="flex items-center gap-3">
          <DomainSwitcher />
          <nav className="flex items-center gap-2 text-sm sm:gap-3">
            <a href={`/?domain=${domain}`} className={operatorMode ? "text-ink-muted hover:text-brand" : "text-brand font-medium"}>{domain === "hiring" ? "Recruit" : "Apply"}</a>
            <span className="text-ink-muted">·</span>
            <a href={`/?domain=${domain}&view=operator`} className={operatorMode ? "text-brand font-medium" : "text-ink-muted hover:text-brand"}>Operator</a>
          </nav>
        </div>
      </div>
    </header>
  );
}
