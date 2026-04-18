export type Decision = "approved" | "denied";
export type Domain = "loans" | "hiring" | "moderation" | "admissions" | "fraud";
export type ContestPath = "correction" | "new_evidence" | "human_review";
export type ReasonCategory =
  | "stale_data"
  | "data_entry_error"
  | "circumstances_changed"
  | "missing_information"
  | "protected_attribute"
  | "other"
  | string;

export interface ShapEntry {
  feature: string;
  displayName: string;
  value: number | string;
  valueDisplay: string;
  contribution: number;
  contestable: boolean;
  protected: boolean;
}

export interface EvidenceRef {
  feature: string;
  evidence_type: string;
  filename?: string;
  evidence_hash?: string;
}

export interface VerbSet {
  subject_noun: string;
  approved_label: string;
  denied_label: string;
  hero_question: string;
  hero_subtitle: string;
  outcome_title_flipped: string;
  outcome_title_same: string;
  outcome_review_title: string;
  correction_title: string;
  correction_sub: string;
  new_evidence_title: string;
  new_evidence_sub: string;
  review_title: string;
  review_sub: string;
  correction_button: string;
  correction_body: string;
  new_evidence_body: string;
  review_body: string;
}

export interface ProfileGroup {
  id: string;
  title: string;
  locked: boolean;
  locked_hint?: string;
  field_keys: string[];
}

export type CorrectionPolicy = "user_editable" | "evidence_driven" | "locked";

export interface FeatureSchemaEntry {
  feature: string;
  form_key: string;
  display_name: string;
  group: string;
  contestable: boolean;
  protected: boolean;
  correction_policy: CorrectionPolicy;
  evidence_types: string[];
  unit: string;
  hint: string;
  hint_placeholder: string;
  min?: number | null;
  max?: number | null;
  step?: number | null;
  realistic_delta_multiplier: number;
}

export interface PathReason {
  value: string;
  label: string;
}

export interface EvaluationResult {
  case_id: string;
  domain: Domain;
  display_name: string;
  decision: Decision;
  confidence: number;
  model_version_hash: string;
  shap_values: ShapEntry[];
  plain_language_reason: string;
  suggested_evidence: Array<{
    feature: string;
    evidence_type: string;
    target_value_hint?: number | string;
    source?: string;
  }>;
  verbs: VerbSet;
  profile_groups: ProfileGroup[];
  feature_schema: FeatureSchemaEntry[];
  path_reasons: { contest: PathReason[]; review: PathReason[] };
  legal_citations: string[];
  feature_values: Record<string, number | string>;
  applicant_name?: string;
}

export interface FeatureDelta {
  feature: string;
  displayName: string;
  old_value: number | string;
  new_value: number | string;
  old_value_display: string;
  new_value_display: string;
  old_contribution: number;
  new_contribution: number;
  contribution_delta: number;
}

export interface ContestResult {
  case_id: string;
  contest_path: ContestPath;
  before: {
    decision: Decision;
    confidence: number;
    shap_values: ShapEntry[];
  };
  after: {
    decision: Decision;
    confidence: number;
    shap_values: ShapEntry[];
  } | null;
  delta: {
    decision_flipped: boolean;
    confidence_change: number;
    feature_deltas: FeatureDelta[];
  } | null;
  anomaly_flags: string[];
  audit_entry_id: string;
  audit_hash: string;
}

export interface ReviewResult {
  case_id: string;
  queue_position: number;
  estimated_review_window: string;
  audit_entry_id: string;
  audit_hash: string;
  status: "queued_for_human_review";
}

export interface AuditEntry {
  id: string;
  case_id: string;
  timestamp: string;
  title: string;
  subtitle: string;
  hash: string;
  kind?: "info" | "success" | "warning";
}

export type Step = 0 | 1 | 2 | 3 | 4;

export interface DomainCase {
  case_id: string;
  applicant_reference: string;
  applicant_name?: string;
  date_of_birth: string;
}

export interface DomainsCatalog {
  domains: { id: Domain; display_name: string }[];
  cases_by_domain: Record<Domain, DomainCase[]>;
}
