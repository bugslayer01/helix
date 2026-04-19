export function Header({ operatorMode }: { operatorMode: boolean }) {
  return (
    <header className="border-b hairline bg-surface">
      <div className="mx-auto flex max-w-shell items-center justify-between px-8 py-5">
        <a href="/" className="flex items-center gap-3 text-ink hover:text-brand">
          <span aria-hidden className="flex h-8 w-8 items-center justify-center rounded-full bg-brand">
            <span className="h-2.5 w-2.5 rounded-full bg-surface" />
          </span>
          <span>
            <span className="display block text-lg leading-none">LenderCo</span>
            <span className="label block mt-1">Retail lending · India</span>
          </span>
        </a>
        <nav className="flex items-center gap-3 text-sm">
          <a href="/" className={operatorMode ? "text-ink-muted hover:text-brand" : "text-brand font-medium"}>Apply</a>
          <span className="text-ink-muted">·</span>
          <a href="/?view=operator" className={operatorMode ? "text-brand font-medium" : "text-ink-muted hover:text-brand"}>Operator</a>
        </nav>
      </div>
    </header>
  );
}
