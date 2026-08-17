import { useRef, useState } from 'react'
import { Fingerprint, Upload, Loader2, TriangleAlert, Info } from 'lucide-react'
import { checkFingerprintQuality } from '../services/api'
import type { FingerprintScanSummary } from '../types/profile'
import StatTile from '../components/common/StatTile'
import Meter from '../components/common/Meter'

const QUALITY_STYLES: Record<string, { text: string; bg: string; border: string }> = {
  Good: { text: 'text-status-good', bg: 'bg-status-good/10', border: 'border-status-good/30' },
  Fair: { text: 'text-status-caution', bg: 'bg-status-caution/10', border: 'border-status-caution/30' },
  Poor: { text: 'text-status-warning', bg: 'bg-status-warning/10', border: 'border-status-warning/30' },
}

const PATTERN_LABELS: Record<string, string> = {
  arch: 'Arch',
  loop: 'Loop',
  whorl: 'Whorl',
}

/**
 * Fingerprint Detection: a standalone, self-contained analysis tool. Upload
 * an image, it's analyzed in-memory and discarded by the backend (see
 * backend/app/api/routes_biometric.py's `/biometric/quality-check` endpoint,
 * which this page calls) -- nothing here is enrolled, matched against an
 * identity, or persisted. That's a deliberate scope boundary: the separate
 * "Cognitive Profile" tab owns enrollment/identity/consent; this tab is
 * purely "does this image look like a fingerprint, and what does standard
 * ridge/minutiae/singularity image analysis say about it."
 */
export default function FingerprintDetection() {
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [scan, setScan] = useState<FingerprintScanSummary | null>(null)
  const [dragOver, setDragOver] = useState(false)

  async function analyze(file: Blob) {
    setLoading(true)
    setError(null)
    setScan(null)
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    setPreviewUrl(URL.createObjectURL(file))
    try {
      const res = await checkFingerprintQuality(file)
      setScan(res.scan)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not analyze this image.')
    } finally {
      setLoading(false)
    }
  }

  function handleFileSelect(fileList: FileList | null) {
    const file = fileList?.[0]
    if (file) void analyze(file)
  }

  const qualityStyle = scan ? QUALITY_STYLES[scan.quality.quality_label] ?? QUALITY_STYLES.Fair : null

  return (
    <div className="flex flex-col gap-6">
      <div className="glass-panel p-6">
        <div className="mb-4 flex items-center gap-2">
          <Fingerprint size={18} strokeWidth={1.75} className="text-cyan-accent" />
          <h1 className="text-lg font-semibold text-ink-primary">Fingerprint Detection</h1>
        </div>
        <p className="mb-2 text-sm leading-relaxed text-ink-secondary">
          Upload a fingerprint image to see what standard image-processing analysis detects in it
          - ridge quality, minutiae (endings/bifurcations), and singularity-based pattern
          classification (arch / loop / whorl). This is a self-contained detection tool: the image
          is analyzed in memory and discarded, and nothing here is enrolled, matched against an
          identity, or stored - see the separate{' '}
          <a href="/profile" className="text-cyan-accent underline decoration-cyan-accent/30 underline-offset-2 hover:decoration-cyan-accent">
            Cognitive Profile
          </a>{' '}
          tab if you want the enrollment/identity flow instead.
        </p>
      </div>

      <div className="glass-panel p-6">
        <div
          onDragOver={(e) => {
            e.preventDefault()
            setDragOver(true)
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragOver(false)
            handleFileSelect(e.dataTransfer.files)
          }}
          onClick={() => fileInputRef.current?.click()}
          className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
            dragOver ? 'border-cyan-accent/60 bg-cyan-faint' : 'border-panel-border hover:border-cyan-accent/30'
          }`}
        >
          {previewUrl ? (
            <img src={previewUrl} alt="Uploaded fingerprint preview" className="h-40 w-40 rounded-lg border border-panel-border object-cover" />
          ) : (
            <Upload size={28} strokeWidth={1.5} className="text-ink-muted" />
          )}
          <div>
            <p className="text-sm font-medium text-ink-primary">Click to upload or drag a fingerprint image here</p>
            <p className="mt-1 text-xs text-ink-muted">PNG or JPG, up to 8MB</p>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => handleFileSelect(e.target.files)}
          />
        </div>

        {loading && (
          <div className="mt-4 flex items-center justify-center gap-2 text-sm text-ink-secondary">
            <Loader2 size={15} className="animate-spin" />
            Analyzing image…
          </div>
        )}

        {error && (
          <div className="mt-4 flex items-center gap-3 rounded-lg border border-status-warning/30 bg-status-warning/10 p-3 text-sm text-status-warning">
            <TriangleAlert size={16} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {scan && qualityStyle ? (
        <>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className={`glass-panel p-6 ${qualityStyle.border} border`}>
              <div className="section-label mb-2">Scan Quality</div>
              <div className={`inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-semibold ${qualityStyle.bg} ${qualityStyle.text}`}>
                {scan.quality.quality_label}
                <span className="font-mono text-xs opacity-80">({Math.round(scan.quality.overall_quality * 100)}%)</span>
              </div>
              <div className="mt-4 flex flex-col gap-3">
                <Meter label="Ridge visibility" value={scan.quality.ridge_visibility_pct} />
                <Meter label="Orientation confidence" value={scan.quality.orientation_confidence_pct} />
                <Meter label="Contrast" value={scan.quality.contrast_score * 100} />
                <Meter label="Sharpness" value={scan.quality.sharpness_score * 100} />
                <Meter label="Segmentation quality" value={scan.quality.segmentation_quality * 100} />
                <Meter label="Ridge continuity" value={scan.quality.continuity * 100} />
              </div>
            </div>

            <div className="glass-panel p-6">
              <div className="section-label mb-2">Pattern Classification</div>
              <div className="mb-4 flex items-center gap-3">
                <span className="rounded-lg border border-violet-accent/30 bg-violet-faint px-3 py-1.5 text-sm font-semibold text-violet-accent">
                  {PATTERN_LABELS[scan.pattern] ?? scan.pattern}
                </span>
                <span className="font-mono text-xs text-ink-muted">
                  {Math.round(scan.pattern_confidence * 100)}% confidence
                </span>
              </div>
              <p className="mb-4 text-xs leading-relaxed text-ink-muted">
                Classified from Poincaré-index singularity detection over the ridge orientation
                field - a standard fingerprint image-processing technique, not identity matching.
              </p>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <StatTile label="Minutiae" value={scan.quality.minutiae_detected} />
                <StatTile label="Endings" value={scan.n_endings} />
                <StatTile label="Bifurcations" value={scan.n_bifurcations} />
                <StatTile label="Cores" value={scan.n_cores} />
                <StatTile label="Deltas" value={scan.n_deltas} />
                <StatTile label="Width" value={`${scan.image_width}px`} />
                <StatTile label="Height" value={`${scan.image_height}px`} />
              </div>
            </div>
          </div>

          <div className="glass-panel flex items-start gap-3 p-5">
            <Info size={16} strokeWidth={1.75} className="mt-0.5 shrink-0 text-ink-muted" />
            <p className="text-xs leading-relaxed text-ink-muted">{scan.measurement_note}</p>
          </div>
        </>
      ) : null}
    </div>
  )
}
