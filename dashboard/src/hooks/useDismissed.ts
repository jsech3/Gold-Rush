import { useState, useCallback } from 'react'

const STORAGE_KEY = 'goldrush-dismissed'

export type DismissReason = 'no_longer_available' | 'fake_job' | 'not_relevant' | 'didnt_like' | 'no_response' | 'other'

interface DismissedEntry {
  reason: DismissReason
  date: string
  note?: string
}

type DismissedMap = Record<string, DismissedEntry>

function getDismissed(): DismissedMap {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    return JSON.parse(raw)
  } catch {
    return {}
  }
}

function saveDismissed(map: DismissedMap) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(map))
}

export function useDismissed() {
  const [dismissed, setDismissed] = useState<DismissedMap>(getDismissed)

  const dismiss = useCallback((jobId: string, reason: DismissReason, note?: string) => {
    setDismissed(prev => {
      const next = { ...prev, [jobId]: { reason, date: new Date().toISOString(), note } }
      saveDismissed(next)
      return next
    })
  }, [])

  const dismissMany = useCallback((jobIds: string[], reason: DismissReason) => {
    setDismissed(prev => {
      const next = { ...prev }
      const now = new Date().toISOString()
      for (const id of jobIds) {
        next[id] = { reason, date: now }
      }
      saveDismissed(next)
      return next
    })
  }, [])

  const isDismissed = useCallback((jobId: string) => jobId in dismissed, [dismissed])

  const undismiss = useCallback((jobId: string) => {
    setDismissed(prev => {
      const next = { ...prev }
      delete next[jobId]
      saveDismissed(next)
      return next
    })
  }, [])

  return { isDismissed, dismiss, dismissMany, undismiss, dismissedMap: dismissed, dismissedCount: Object.keys(dismissed).length }
}
