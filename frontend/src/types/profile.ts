// Mirrors backend/app/models/profile_schemas.py field-for-field.
// The Individual Computational Profile (ICP): a fingerprint-linked
// personalization key + a behaviorally-learned parameter set. Nothing here
// is a biological measurement -- see NOT_A_BIOLOGICAL_MEASUREMENT below.

export const NOT_A_BIOLOGICAL_MEASUREMENT =
  "Simulated computational value — not a biological measurement of this user's brain, hormones, or cognition.";

export const PROFILE_PARAM_NAMES = [
  'attention_baseline',
  'working_memory_baseline',
  'cognitive_control',
  'exploration',
  'exploitation',
  'memory_retrieval',
  'uncertainty_sensitivity',
  'salience_sensitivity',
  'verification_strength',
] as const;

export type ProfileParamName = (typeof PROFILE_PARAM_NAMES)[number];

export type ComputationalProfileParams = Record<ProfileParamName, number>;

export const TASK_CATEGORIES = [
  'mathematics',
  'coding',
  'scientific_reasoning',
  'factual_retrieval',
  'creative_generation',
  'decision_making',
  'social_reasoning',
  'planning',
  'ambiguous',
] as const;

export type TaskCategory = (typeof TASK_CATEGORIES)[number];

// -- Biometric scan / enrollment --------------------------------------------

export interface FingerprintQuality {
  quality_label: 'Good' | 'Fair' | 'Poor';
  overall_quality: number;
  ridge_visibility_pct: number;
  orientation_confidence_pct: number;
  contrast_score: number;
  sharpness_score: number;
  segmentation_quality: number;
  continuity: number;
  minutiae_detected: number;
}

export interface FingerprintScanSummary {
  quality: FingerprintQuality;
  pattern: 'arch' | 'loop' | 'whorl';
  pattern_confidence: number;
  n_cores: number;
  n_deltas: number;
  n_endings: number;
  n_bifurcations: number;
  image_width: number;
  image_height: number;
  measurement_note: string;
}

export interface QualityCheckResponse {
  scan: FingerprintScanSummary;
}

export interface EnrollResponse {
  profile_id: string;
  matched_existing_profile: boolean;
  match_similarity: number;
  scan: FingerprintScanSummary;
  virtual_brain_parameters: ComputationalProfileParams;
  evidence_status: string;
}

// -- Profile lifecycle --------------------------------------------------------

export interface ComputationalProfileOut {
  profile_id: string;
  consent_given: boolean;
  created_at: string;
  updated_at: string;
  evidence_status: string;
  virtual_brain_parameters: ComputationalProfileParams;
  task_profiles: Record<string, ComputationalProfileParams>;
  enrolled_finger_count: number;
}

export interface DeleteProfileResponse {
  deleted: boolean;
}

export interface ResetBiometricResponse {
  reset: boolean;
  note: string;
}

export interface ExportProfileResponse {
  export: Record<string, unknown>;
}

export interface EvolutionHistoryEntry {
  timestamp: string;
  task_category: string;
  pathway: string;
  params_snapshot: ComputationalProfileParams;
}

export interface EvolutionResponse {
  initial: ComputationalProfileParams;
  current: ComputationalProfileParams;
  task_profiles: Record<string, ComputationalProfileParams>;
  n_interactions: number;
  history: EvolutionHistoryEntry[];
  note: string;
}

export interface FeedbackRequest {
  interaction_id: number;
  feedback_score: number;
}

export interface FeedbackResponse {
  updated_parameters: ComputationalProfileParams;
}

// -- Profile influence attached to /api/chat ---------------------------------

export interface ExplanationEntryOut {
  question: string;
  answer: string;
}

export interface ProfileInfluence {
  applied: boolean;
  task_category: string;
  task_category_confidence: number;
  candidate_systems: string[];
  explanation: ExplanationEntryOut[];
  disclaimer: string;
}

// -- Counterfactual simulator -------------------------------------------------

export type CounterfactualOverrides = Partial<ComputationalProfileParams>;

export interface CounterfactualRequest {
  query: string;
  model?: string;
  profile_id?: string | null;
  overrides: CounterfactualOverrides;
}

export interface CounterfactualSide {
  answer: string;
  pathway: string;
  hallucination_risk: number;
  confidence: number;
  uncertainty_agreement: number | null;
  parameters_used: ComputationalProfileParams;
}

export interface CounterfactualResponse {
  baseline: CounterfactualSide;
  counterfactual: CounterfactualSide;
  confidence_delta: number;
  hallucination_risk_delta: number;
  pathway_changed: boolean;
  note: string;
}

// -- Research mode: Condition A/B/C comparison --------------------------------

export interface ResearchCompareRequest {
  profile_id?: string | null;
  model?: string;
  categories?: string[] | null;
  limit_per_category?: number;
}

export interface ConditionSummary {
  condition: 'A' | 'B' | 'C';
  label: string;
  n: number;
  accuracy: number | null;
  mean_hallucination_risk: number;
  abstention_rate: number;
}

export interface ResearchCompareResponse {
  conditions: ConditionSummary[];
  honest_summary: string;
}
