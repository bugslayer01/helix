export type Decision = "approved" | "denied";

export type Stage =
  | "handoff"       // JWT + DOB entry
  | "understand"    // see snapshot, SHAP, reasons
  | "contest"       // upload evidence, see shield, build proposals
  | "review"        // path 3 — human reviewer
  | "outcome";      // flipped / held
