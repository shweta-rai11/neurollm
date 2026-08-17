import type { ProfileInfluence } from './profile';

export interface TaskAnalysis {
  complexity: number;
  logical_reasoning: number;
  creativity: number;
  planning: number;
  context_dependency: number;
  verification_requirement: number;
  risk: number;
  ambiguity: number;
  factuality_requirement: number;
}

export interface CandidateResponse {
  text: string;
  cluster_id: number;
}

export interface UncertaintyResult {
  semantic_uncertainty_score: number;
  response_agreement: number;
  candidate_count: number;
  unique_semantic_clusters: number;
  mean_embedding_similarity: number;
  max_embedding_distance: number;
  entropy_raw: number;
  entropy_normalized: number;
  candidates: CandidateResponse[];
  method: string;
}

/** The five MVP virtual brain regions (spec section 22). */
export interface RegionScores {
  language: number;
  memory: number;
  reasoning: number;
  uncertainty: number;
  verification: number;
}

export interface BrainRegions {
  predicted: RegionScores;
  measured: RegionScores | null;
}

/** Virtual Neuromodulation Layer -- computational analogies, not biological hormones. */
export interface NeuromodulatorSignals {
  dopamine_like: number;
  serotonin_like: number;
  norepinephrine_like: number;
  acetylcholine_like: number;
}

export interface HallucinationRisk {
  score: number;
  components: Record<string, number>;
}

export interface GlobalState {
  confidence: number;
  uncertainty: number;
  difficulty: number;
  verification_need: number;
}

export interface StateInterpretation {
  modes: string[];
  status: string;
  contributing_signals: Record<string, string>;
  interpretation: string;
}

export interface Recommendation {
  title: string;
  detail: string;
  icon: string;
  severity: 'info' | 'caution' | 'warning';
}

export interface ProbePrediction {
  predicted_category: string;
  confidence: number;
  probabilities: Record<string, number>;
  probe_type: string;
}

export interface RetrievalSource {
  title: string;
  snippet: string;
  url: string;
}

export interface ResearchDetails {
  num_layers: number;
  layer_hidden_norms: number[];
  layer_attention_entropy: number[];
  token_entropies: number[];
  token_prob_margins: number[];
  activation_features: Record<string, number>;
  probe_prediction: ProbePrediction | null;
  verifier_raw_text: string | null;
  retrieval_raw_text: string | null;
  retrieval_sources: RetrievalSource[];
  routing_reason: string;
}

export interface CognitiveState {
  brain_regions: BrainRegions;
  neuromodulation: NeuromodulatorSignals;
  global_state: GlobalState;
  interpretation: StateInterpretation;
  recommendations: Recommendation[];
}

export type Pathway = 'DIRECT' | 'ANALYTICAL' | 'CREATIVE' | 'VERIFY';

export interface ChatRequest {
  query: string;
  model?: string;
  uncertainty_mode?: boolean;
  num_samples?: number;
  research_mode?: boolean;
  profile_id?: string | null;
}

export interface ChatMetadata {
  model: string;
  duration_ms: number;
  input_tokens: number;
  output_tokens: number;
  provider: string;
}

export interface ChatResponse {
  answer: string;
  pathway: Pathway;
  hallucination_risk: HallucinationRisk;
  cognitive_state: CognitiveState;
  uncertainty: UncertaintyResult | null;
  task_analysis: TaskAnalysis;
  recommendations: Recommendation[];
  metadata: ChatMetadata;
  research: ResearchDetails | null;
  profile_influence: ProfileInfluence | null;
}

export interface AnalyzeRequest { query: string }
export interface AnalyzeResponse { task_analysis: TaskAnalysis }

export interface UncertaintyRequest { query: string; model?: string; num_samples?: number }
export interface UncertaintyResponse { uncertainty: UncertaintyResult }

export interface ExperimentRequest { query_a: string; query_b: string; model?: string; num_samples?: number }
export interface ExperimentSide {
  query: string;
  answer: string;
  pathway: Pathway;
  hallucination_risk: HallucinationRisk;
  task_analysis: TaskAnalysis;
  cognitive_state: CognitiveState;
  uncertainty: UncertaintyResult | null;
}
export interface ExperimentResponse {
  side_a: ExperimentSide;
  side_b: ExperimentSide;
  response_agreement_between_sides: number;
}

export interface HistoryItem {
  id: number;
  timestamp: string;
  query: string;
  model: string;
  pathway: Pathway;
  uncertainty: number;
  confidence: number;
  difficulty: number;
  verification_need: number;
  hallucination_risk: number;
}
export interface HistoryResponse { items: HistoryItem[] }

export interface HealthResponse { status: string; version: string }
export interface ConfigResponse {
  available_models: string[];
  default_model: string;
  default_num_samples: number;
  max_num_samples: number;
  has_openai_key: boolean;
  local_model_name: string | null;
}

// ---------------------------------------------------------------------------
// Condition comparison / benchmark
// ---------------------------------------------------------------------------

export interface BenchmarkRequest {
  model?: string;
  categories?: string[];
  limit_per_category?: number;
}

export interface BenchmarkItemResult {
  id: string;
  category: string;
  query: string;
  expected_answer: string | null;
  condition_normal_answer: string;
  condition_normal_correct: boolean | null;
  condition_routed_answer: string;
  condition_routed_correct: boolean | null;
  condition_routed_pathway: Pathway;
  condition_routed_abstained: boolean;
  hallucination_risk: number;
}

export interface BenchmarkCategorySummary {
  category: string;
  n: number;
  normal_accuracy: number | null;
  routed_accuracy: number | null;
  routed_abstention_rate: number;
  mean_hallucination_risk: number;
}

export interface BenchmarkResponse {
  model: string;
  items: BenchmarkItemResult[];
  category_summaries: BenchmarkCategorySummary[];
  normal_mean_latency_ms: number;
  routed_mean_latency_ms: number;
}

export interface ProbeInfoResponse {
  trained: boolean;
  probe_type: string | null;
  test_accuracy: number | null;
  n_train: number | null;
  n_test: number | null;
  categories: string[];
  trained_at: string | null;
}
