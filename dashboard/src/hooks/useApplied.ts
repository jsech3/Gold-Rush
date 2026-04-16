import { useState, useCallback } from 'react'

const STORAGE_KEY = 'goldrush-applied'

// Map of jobId → ISO date string when marked applied
type AppliedMap = Record<string, string>

function getApplied(): AppliedMap {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw)

    // Migrate from old format (array of IDs) to new format (map with dates)
    if (Array.isArray(parsed)) {
      const migrated: AppliedMap = {}
      for (const id of parsed) {
        migrated[id] = new Date().toISOString()
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(migrated))
      return migrated
    }

    return parsed
  } catch {
    return {}
  }
}

function saveApplied(map: AppliedMap) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(map))
}

export function useApplied() {
  const [applied, setApplied] = useState<AppliedMap>(getApplied)

  const toggleApplied = useCallback((jobId: string) => {
    setApplied(prev => {
      const next = { ...prev }
      if (next[jobId]) {
        delete next[jobId]
      } else {
        next[jobId] = new Date().toISOString()
      }
      saveApplied(next)
      return next
    })
  }, [])

  const isApplied = useCallback((jobId: string) => jobId in applied, [applied])

  const getAppliedDate = useCallback((jobId: string) => applied[jobId] || null, [applied])

  return {
    isApplied,
    toggleApplied,
    getAppliedDate,
    appliedCount: Object.keys(applied).length,
    appliedMap: applied,
  }
}
