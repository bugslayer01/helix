function currentDomain(): "loans" | "hiring" {
  return new URLSearchParams(window.location.search).get("domain") === "hiring" ? "hiring" : "loans";
}

export function DomainSwitcher() {
  const cur = currentDomain();
  const swap = (d: "loans" | "hiring") => {
    const url = new URL(window.location.href);
    url.searchParams.set("domain", d);
    url.searchParams.delete("view");
    window.location.href = url.toString();
  };
  return (
    <div className="inline-flex rounded-md border hairline overflow-hidden text-[12px]">
      <button
        onClick={() => swap("loans")}
        className={`px-3 py-1 ${cur === "loans" ? "bg-brand text-surface" : "bg-surface text-ink-muted hover:text-brand"}`}
      >Loans</button>
      <button
        onClick={() => swap("hiring")}
        className={`px-3 py-1 ${cur === "hiring" ? "bg-brand text-surface" : "bg-surface text-ink-muted hover:text-brand"}`}
      >Hiring</button>
    </div>
  );
}
