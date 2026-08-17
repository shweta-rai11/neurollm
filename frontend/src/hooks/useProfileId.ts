import { useCallback, useState } from 'react'

const STORAGE_KEY = 'neurollm.profile_id'

/**
 * The app has no accounts/auth system at all (see README) -- this is a
 * demo-grade identifier handed back by /api/biometric/enroll and kept in
 * localStorage, not a hardened session. See the Privacy tab for the
 * explanation shown to the user.
 */
export function useProfileId() {
  const [profileId, setProfileIdState] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY))

  const setProfileId = useCallback((id: string | null) => {
    if (id) {
      localStorage.setItem(STORAGE_KEY, id)
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
    setProfileIdState(id)
  }, [])

  return { profileId, setProfileId }
}
