import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ShieldCheck, Download, RotateCcw, Trash2, Loader2, Fingerprint } from 'lucide-react'
import { deleteComputationalProfile, exportComputationalProfile, resetBiometric } from '../../services/api'
import { useProfileId } from '../../hooks/useProfileId'

type ConfirmTarget = 'delete' | 'reset' | null

export default function Privacy() {
  const { profileId, setProfileId } = useProfileId()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [confirmTarget, setConfirmTarget] = useState<ConfirmTarget>(null)

  async function handleExport() {
    if (!profileId) return
    setBusy(true)
    setError(null)
    try {
      const res = await exportComputationalProfile(profileId)
      const blob = new Blob([JSON.stringify(res.export, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `computational-profile-${profileId.slice(0, 8)}.json`
      a.click()
      URL.revokeObjectURL(url)
      setMessage('Profile exported.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed.')
    } finally {
      setBusy(false)
    }
  }

  async function handleReset() {
    if (!profileId) return
    setBusy(true)
    setError(null)
    try {
      await resetBiometric(profileId)
      setMessage('Fingerprint templates removed. Your learned computational profile was kept - re-enroll to link a fingerprint again.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Reset failed.')
    } finally {
      setBusy(false)
      setConfirmTarget(null)
    }
  }

  async function handleDelete() {
    if (!profileId) return
    setBusy(true)
    setError(null)
    try {
      await deleteComputationalProfile(profileId)
      setProfileId(null)
      setMessage('Profile deleted.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed.')
    } finally {
      setBusy(false)
      setConfirmTarget(null)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="glass-panel p-6">
        <div className="mb-3 flex items-center gap-2">
          <ShieldCheck size={18} strokeWidth={1.75} className="text-cyan-accent" />
          <h1 className="text-lg font-semibold text-ink-primary">Privacy</h1>
        </div>
        <div className="flex flex-col gap-3 text-sm leading-relaxed text-ink-secondary">
          <p>Fingerprints are sensitive biometric data. This app handles them as follows:</p>
          <ul className="list-inside list-disc space-y-1.5 text-ink-secondary">
            <li>The raw fingerprint image is processed in memory for one request and is <strong className="text-ink-primary">never written to disk or a database</strong> - anywhere.</li>
            <li>Only a derived numeric template (ridge/minutiae/pattern features) is stored, and it's <strong className="text-ink-primary">encrypted at rest</strong>.</li>
            <li>Enrollment requires explicit consent - it's rejected otherwise.</li>
            <li>Your fingerprint is used only as an identity/personalization key. It is never used to infer a cognitive trait - see the Overview and About pages.</li>
            <li>This app has no account/login system. Your <code className="rounded bg-panel-light px-1 py-0.5 font-mono text-[11px]">profile_id</code> is kept in your browser's local storage, not a hardened session - clearing browser data loses the link to your profile (the profile itself remains on the server until deleted).</li>
            <li>You can export, reset your biometric enrollment, or fully delete your profile below at any time.</li>
          </ul>
        </div>
      </div>

      {!profileId ? (
        <div className="glass-panel flex flex-col items-center gap-4 p-10 text-center">
          <Fingerprint size={32} className="text-ink-muted" />
          <p className="text-sm text-ink-secondary">No profile loaded - nothing to manage yet.</p>
          <Link to="/profile/enroll" className="rounded-lg border border-cyan-accent/40 bg-cyan-faint px-4 py-2 text-sm font-medium text-cyan-accent hover:bg-cyan-accent/20">
            Scan fingerprint
          </Link>
        </div>
      ) : (
        <div className="glass-panel p-6">
          <div className="section-label mb-4">Manage this profile</div>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              disabled={busy}
              onClick={handleExport}
              className="flex items-center gap-2 rounded-lg border border-panel-border bg-panel-light px-4 py-2 text-sm text-ink-secondary transition-colors hover:border-cyan-accent/30 hover:text-ink-primary disabled:opacity-50"
            >
              <Download size={15} strokeWidth={1.75} />
              Export profile
            </button>

            <button
              type="button"
              disabled={busy}
              onClick={() => setConfirmTarget('reset')}
              className="flex items-center gap-2 rounded-lg border border-status-caution/30 bg-status-caution/10 px-4 py-2 text-sm text-status-caution transition-colors hover:bg-status-caution/20 disabled:opacity-50"
            >
              <RotateCcw size={15} strokeWidth={1.75} />
              Reset biometric (re-enroll)
            </button>

            <button
              type="button"
              disabled={busy}
              onClick={() => setConfirmTarget('delete')}
              className="flex items-center gap-2 rounded-lg border border-status-warning/30 bg-status-warning/10 px-4 py-2 text-sm text-status-warning transition-colors hover:bg-status-warning/20 disabled:opacity-50"
            >
              <Trash2 size={15} strokeWidth={1.75} />
              Delete profile
            </button>
          </div>

          {confirmTarget ? (
            <div className="mt-4 flex items-center gap-3 rounded-lg border border-status-warning/30 bg-status-warning/10 px-4 py-3 text-sm text-status-warning">
              <span>
                {confirmTarget === 'delete'
                  ? 'Permanently delete this profile and all its data? This cannot be undone.'
                  : 'Remove all enrolled fingerprint templates? Your learned computational profile is kept.'}
              </span>
              <button
                type="button"
                onClick={confirmTarget === 'delete' ? handleDelete : handleReset}
                className="ml-auto flex items-center gap-1.5 rounded-md border border-status-warning/40 bg-status-warning/20 px-3 py-1.5 font-medium"
              >
                {busy ? <Loader2 size={13} className="animate-spin" /> : null}
                Confirm
              </button>
              <button type="button" onClick={() => setConfirmTarget(null)} className="rounded-md border border-panel-border px-3 py-1.5 text-ink-secondary">
                Cancel
              </button>
            </div>
          ) : null}

          {message ? <p className="mt-4 text-sm text-status-good">{message}</p> : null}
          {error ? <p className="mt-4 text-sm text-status-warning">{error}</p> : null}
        </div>
      )}
    </div>
  )
}
