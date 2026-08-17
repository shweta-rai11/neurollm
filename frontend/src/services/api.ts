import type {
  ChatRequest,
  ChatResponse,
  AnalyzeRequest,
  AnalyzeResponse,
  UncertaintyRequest,
  UncertaintyResponse,
  ExperimentRequest,
  ExperimentResponse,
  BenchmarkRequest,
  BenchmarkResponse,
  HistoryResponse,
  HealthResponse,
  ConfigResponse,
  ProbeInfoResponse,
} from '../types/cognitiveState'
import type {
  QualityCheckResponse,
  EnrollResponse,
  ComputationalProfileOut,
  DeleteProfileResponse,
  ExportProfileResponse,
  ResetBiometricResponse,
  EvolutionResponse,
  FeedbackRequest,
  FeedbackResponse,
  CounterfactualRequest,
  CounterfactualResponse,
  ResearchCompareRequest,
  ResearchCompareResponse,
} from '../types/profile'

// In the browser (dev server or the FastAPI-served build), the backend is
// same-origin and `/api` (proxied by Vite in dev, served directly by
// FastAPI in prod -- see backend/app/main.py) is correct as-is. The native
// Capacitor shell has no same-origin backend at all -- its webview serves
// the bundled `dist/` from `capacitor://localhost`/`https://localhost`, so
// it needs an absolute URL to a real, network-reachable backend, set via
// `VITE_API_BASE_URL` at build time (see frontend/MOBILE.md).
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json()
    if (body && typeof body === 'object') {
      if (typeof body.detail === 'string') return body.detail
      if (typeof body.message === 'string') return body.message
      if (typeof body.error === 'string') return body.error
    }
  } catch {
    // response had no JSON body - fall through to status text
  }
  return `${response.status} ${response.statusText || 'Request failed'}`
}

async function request<TResponse>(path: string, options: RequestInit = {}): Promise<TResponse> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers ?? {}),
      },
      ...options,
    })
  } catch {
    throw new Error('AI model unavailable - could not reach the backend.')
  }

  if (!response.ok) {
    const message = await extractErrorMessage(response)
    throw new Error(message)
  }

  return (await response.json()) as TResponse
}

function post<TRequest, TResponse>(path: string, body: TRequest): Promise<TResponse> {
  return request<TResponse>(path, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

/** Multipart form upload -- for fingerprint images. Omits the JSON
 * Content-Type header entirely so the browser can set its own multipart
 * boundary (see `request()`, which always sets Content-Type: application/json
 * otherwise). */
async function postForm<TResponse>(path: string, formData: FormData): Promise<TResponse> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, { method: 'POST', body: formData })
  } catch {
    throw new Error('AI model unavailable - could not reach the backend.')
  }
  if (!response.ok) {
    const message = await extractErrorMessage(response)
    throw new Error(message)
  }
  return (await response.json()) as TResponse
}

export function chat(req: ChatRequest): Promise<ChatResponse> {
  return post('/chat', req)
}

export function analyze(req: AnalyzeRequest): Promise<AnalyzeResponse> {
  return post('/analyze', req)
}

export function estimateUncertainty(req: UncertaintyRequest): Promise<UncertaintyResponse> {
  return post('/uncertainty', req)
}

export function runExperiment(req: ExperimentRequest): Promise<ExperimentResponse> {
  return post('/experiment', req)
}

export function runBenchmark(req: BenchmarkRequest): Promise<BenchmarkResponse> {
  return post('/experiment/benchmark', req)
}

export function getHistory(): Promise<HistoryResponse> {
  return request<HistoryResponse>('/history', { method: 'GET' })
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health', { method: 'GET' })
}

export function getConfig(): Promise<ConfigResponse> {
  return request<ConfigResponse>('/config', { method: 'GET' })
}

export function getProbeInfo(): Promise<ProbeInfoResponse> {
  return request<ProbeInfoResponse>('/probes/info', { method: 'GET' })
}

// ---------------------------------------------------------------------------
// Individual Computational Profile: biometric identity and profile lifecycle
// ---------------------------------------------------------------------------

export function checkFingerprintQuality(file: Blob): Promise<QualityCheckResponse> {
  const form = new FormData()
  form.append('file', file, 'fingerprint.png')
  return postForm('/biometric/quality-check', form)
}

export function enrollFingerprint(file: Blob, fingerLabel: string, consent: boolean): Promise<EnrollResponse> {
  const form = new FormData()
  form.append('file', file, 'fingerprint.png')
  form.append('finger_label', fingerLabel)
  form.append('consent', String(consent))
  return postForm('/biometric/enroll', form)
}

export function getComputationalProfile(profileId: string): Promise<ComputationalProfileOut> {
  return request<ComputationalProfileOut>(`/biometric/profile/${profileId}`, { method: 'GET' })
}

export function deleteComputationalProfile(profileId: string): Promise<DeleteProfileResponse> {
  return request<DeleteProfileResponse>(`/biometric/profile/${profileId}`, { method: 'DELETE' })
}

export function exportComputationalProfile(profileId: string): Promise<ExportProfileResponse> {
  return request<ExportProfileResponse>(`/biometric/profile/${profileId}/export`, { method: 'GET' })
}

export function resetBiometric(profileId: string): Promise<ResetBiometricResponse> {
  return request<ResetBiometricResponse>(`/biometric/profile/${profileId}/reset`, { method: 'POST' })
}

export function getProfileEvolution(profileId: string): Promise<EvolutionResponse> {
  return request<EvolutionResponse>(`/profile/${profileId}/evolution`, { method: 'GET' })
}

export function sendProfileFeedback(profileId: string, req: FeedbackRequest): Promise<FeedbackResponse> {
  return post(`/profile/${profileId}/feedback`, req)
}

export function runCounterfactual(req: CounterfactualRequest): Promise<CounterfactualResponse> {
  return post('/profile/counterfactual', req)
}

export function runResearchCompare(req: ResearchCompareRequest): Promise<ResearchCompareResponse> {
  return post('/profile/research/compare', req)
}
