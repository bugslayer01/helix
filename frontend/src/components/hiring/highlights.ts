import type { HighlightSeverity } from "./HighlightSpan";

export interface Highlight {
  id: string;
  severity: HighlightSeverity;
  anchor: string;
  title: string;
  tooltip: string;
  quote: string;
  flaggedFeature?: string;
}

export const HIRING_HIGHLIGHTS: Highlight[] = [
  {
    id: "h1",
    severity: "critical",
    anchor: "experience-bullet-1",
    title: "Skills match lower than target",
    quote:
      "Built out the customer checkout flow in React, partnering with design…",
    tooltip:
      "The role asked for experience with React, TypeScript, and a large-scale design system. Your bullets mention React but not TS or a shared component library.",
    flaggedFeature: "skill_match",
  },
  {
    id: "h2",
    severity: "critical",
    anchor: "summary-years",
    title: "Experience below target",
    quote: "3 years of experience",
    tooltip:
      "Total relevant experience parsed as 3 years; the role targets 5+.",
    flaggedFeature: "years_experience",
  },
  {
    id: "h2b",
    severity: "critical",
    anchor: "experience-title",
    title: "Current title parsed as mid-level",
    quote: "Software Engineer II",
    tooltip:
      "The parser tagged your most recent role as mid-level. Senior-equivalent scope (ownership, mentoring) is not visible in the bullets below.",
    flaggedFeature: "years_experience",
  },
  {
    id: "h3",
    severity: "warning",
    anchor: "gap-2022",
    title: "9-month employment gap",
    quote: "Oct 2022 — Jul 2023 (career break, 9 months)",
    tooltip:
      "A 9-month gap between roles was weighed against you. Upload a caregiver or medical-leave letter to recontextualise.",
    flaggedFeature: "employment_gap",
  },
  {
    id: "h4",
    severity: "suggestion",
    anchor: "skills-section",
    title: "Missing: TypeScript, Next.js, component-library tooling",
    quote: "(missing: TypeScript, Next.js, component-library tooling)",
    tooltip:
      "These keywords from the JD were not matched in your skills list. Certifications or portfolio links that prove them will re-score this.",
    flaggedFeature: "skill_match",
  },
  {
    id: "h5",
    severity: "suggestion",
    anchor: "projects-section",
    title: "Open-source / portfolio not linked",
    quote: "Side projects and open-source contributions are not linked…",
    tooltip:
      "The screener found no external code artefacts. A linked portfolio materially moves this score.",
    flaggedFeature: "skill_match",
  },
];
