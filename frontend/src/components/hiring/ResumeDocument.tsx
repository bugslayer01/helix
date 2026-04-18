import { HighlightSpan } from "./HighlightSpan";
import type { Highlight } from "./highlights";

interface Props {
  highlights: Highlight[];
}

function hl(highlights: Highlight[], id: string): Highlight | undefined {
  return highlights.find((h) => h.id === id);
}

export function ResumeDocument({ highlights }: Props) {
  const h = (id: string, children: React.ReactNode) => {
    const entry = hl(highlights, id);
    if (!entry) return <>{children}</>;
    return (
      <HighlightSpan
        id={entry.id}
        severity={entry.severity}
        tooltip={entry.tooltip}
        title={entry.title}
        flaggedFeature={entry.flaggedFeature}
      >
        {children}
      </HighlightSpan>
    );
  };

  return (
    <article
      className="rounded-2xl border hairline bg-surface p-10 text-ink shadow-[0_1px_0_rgba(0,0,0,0.02)]"
      style={{ fontFamily: '"Fraunces", Georgia, serif' }}
      data-resume
    >
      {/* Header */}
      <header className="mb-8 border-b hairline pb-6" data-section>
        <h1 className="display text-4xl leading-tight">Ananya Kulkarni</h1>
        <div className="mt-1 text-[13px] text-ink-muted" style={{ fontFamily: "Inter, sans-serif" }}>
          Software Engineer · Bengaluru, IN · ananya.k@mail.example · +91 98xxxxxxxx ·{" "}
          <span className="underline decoration-line">linkedin.com/in/ananya-k</span>
        </div>
        <p
          className="mt-5 text-[14.5px] leading-relaxed text-ink"
          style={{ fontFamily: "Inter, sans-serif" }}
        >
          Frontend-leaning software engineer with {h("h2", "3 years of experience")} shipping
          customer-facing web products. Comfortable across React, REST APIs and product
          analytics. Looking for a mid-level role on a design-minded team.
        </p>
      </header>

      {/* Experience */}
      <section className="mb-8" data-section>
        <div
          className="mb-4 text-[10px] uppercase tracking-[0.22em] text-ink-muted"
          style={{ fontFamily: "Inter, sans-serif" }}
        >
          Experience
        </div>

        <div className="mb-6">
          <div className="flex items-baseline justify-between">
            <div>
              <div className="text-[16px] font-medium">
                {h("h2b", "Software Engineer II")} · Zinnia Retail
              </div>
              <div className="text-[13px] text-ink-muted" style={{ fontFamily: "Inter, sans-serif" }}>
                Bengaluru · Aug 2023 — Present
              </div>
            </div>
          </div>
          <ul
            className="mt-3 list-disc space-y-1.5 pl-5 text-[14px] leading-relaxed"
            style={{ fontFamily: "Inter, sans-serif" }}
          >
            <li>
              {h(
                "h1",
                "Built out the customer checkout flow in React, partnering with design on interaction details.",
              )}
            </li>
            <li>
              Owned the email-notification service; reduced bounce rate by 18% through
              template A/B tests.
            </li>
            <li>
              Paired with QA to add end-to-end coverage for the cart, shipping 40+ Cypress
              specs.
            </li>
          </ul>
        </div>

        <div className="mb-6">
          <div className="flex items-baseline justify-between">
            <div>
              <div className="text-[16px] font-medium">
                Junior Developer · Fernwork Labs
              </div>
              <div className="text-[13px] text-ink-muted" style={{ fontFamily: "Inter, sans-serif" }}>
                Pune · Jun 2021 — Oct 2022
              </div>
            </div>
          </div>
          <ul
            className="mt-3 list-disc space-y-1.5 pl-5 text-[14px] leading-relaxed"
            style={{ fontFamily: "Inter, sans-serif" }}
          >
            <li>
              Contributed to a React dashboard used by 12 internal analysts; migrated one
              module from class components to hooks.
            </li>
            <li>
              Fixed recurring data-freshness bugs in the weekly ETL by adding idempotency
              keys to the job runner.
            </li>
          </ul>
        </div>

        <div>
          <div className="flex items-baseline justify-between">
            <div>
              <div className="text-[16px] font-medium">Intern · Cellpoint</div>
              <div className="text-[13px] text-ink-muted" style={{ fontFamily: "Inter, sans-serif" }}>
                Remote ·{" "}
                {h(
                  "h3",
                  "Oct 2022 — Jul 2023 (career break, 9 months)",
                )}
              </div>
            </div>
          </div>
          <ul
            className="mt-3 list-disc space-y-1.5 pl-5 text-[14px] leading-relaxed"
            style={{ fontFamily: "Inter, sans-serif" }}
          >
            <li>
              Returned to industry via a 3-month contract rebuild of an internal
              admin-console after a family-care leave.
            </li>
          </ul>
        </div>
      </section>

      {/* Education */}
      <section className="mb-8" data-section>
        <div
          className="mb-4 text-[10px] uppercase tracking-[0.22em] text-ink-muted"
          style={{ fontFamily: "Inter, sans-serif" }}
        >
          Education
        </div>
        <div className="flex items-baseline justify-between">
          <div>
            <div className="text-[15.5px] font-medium">
              B.E., Information Technology · Pune Institute of Tech
            </div>
            <div className="text-[13px] text-ink-muted" style={{ fontFamily: "Inter, sans-serif" }}>
              2017 — 2021 · GPA 8.1 / 10
            </div>
          </div>
        </div>
      </section>

      {/* Skills */}
      <section className="mb-8" data-section>
        <div
          className="mb-4 text-[10px] uppercase tracking-[0.22em] text-ink-muted"
          style={{ fontFamily: "Inter, sans-serif" }}
        >
          Skills
        </div>
        <div
          className="flex flex-wrap gap-2 text-[13px]"
          style={{ fontFamily: "Inter, sans-serif" }}
        >
          {[
            "React",
            "JavaScript",
            "HTML / CSS",
            "REST APIs",
            "Node.js",
            "Cypress",
            "Git",
          ].map((s) => (
            <span
              key={s}
              className="rounded-full border hairline bg-cream-soft px-3 py-1 text-ink"
            >
              {s}
            </span>
          ))}
          {h(
            "h4",
            <span className="ml-1 italic text-ink-muted">
              (missing: TypeScript, Next.js, component-library tooling)
            </span>,
          )}
        </div>
      </section>

      {/* Projects */}
      <section data-section>
        <div
          className="mb-4 text-[10px] uppercase tracking-[0.22em] text-ink-muted"
          style={{ fontFamily: "Inter, sans-serif" }}
        >
          Projects & Leadership
        </div>
        <div
          className="text-[14px] leading-relaxed"
          style={{ fontFamily: "Inter, sans-serif" }}
        >
          <div className="mb-2">
            <span className="font-medium">Women-in-Tech Bengaluru chapter</span> —
            co-organised 6 quarterly meetups on frontend engineering (2024).
          </div>
          <div>
            {h(
              "h5",
              "Side projects and open-source contributions are not linked in this version of the resume.",
            )}
          </div>
        </div>
      </section>
    </article>
  );
}
