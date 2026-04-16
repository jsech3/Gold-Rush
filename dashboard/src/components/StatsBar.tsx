import type { Meta } from '../types/job'
import { formatSource } from '../utils/filters'

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export function StatsBar({ meta, appliedCount, dismissedCount, onTrackerClick, onDismissedClick }: { meta: Meta; appliedCount: number; dismissedCount: number; onTrackerClick?: () => void; onDismissedClick?: () => void }) {
  const { tier_counts: t, source_counts: s } = meta

  return (
    <div className="border border-border rounded-lg p-4 mb-4 bg-bg-card">
      <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs">
        <div>
          <span className="text-text-secondary">Total:</span>{' '}
          <span className="text-terminal-green font-bold">{meta.total_jobs}</span>
        </div>
        <div>
          <span className="text-text-secondary">New:</span>{' '}
          <span className="text-terminal-green font-bold">{meta.new_jobs_this_run}</span>
        </div>
        <div className="flex gap-3">
          {t.platinum > 0 && (
            <span><span className="text-tier-platinum">Plat:</span> {t.platinum}</span>
          )}
          <span><span className="text-tier-gold">Gold:</span> {t.gold}</span>
          <span><span className="text-tier-silver">Silver:</span> {t.silver}</span>
          <span><span className="text-tier-bronze">Bronze:</span> {t.bronze}</span>
        </div>
        <div className="flex gap-3">
          {Object.entries(s).map(([src, count]) => (
            <span key={src}>
              <span className="text-text-secondary">{formatSource(src)}:</span> {count}
            </span>
          ))}
        </div>
        <button onClick={onTrackerClick} className="hover:underline cursor-pointer">
          <span className="text-text-secondary">Applied:</span>{' '}
          <span className="text-terminal-green">{appliedCount}</span>
          <span className="text-text-secondary ml-1">→</span>
        </button>
        {dismissedCount > 0 && (
          <button onClick={onDismissedClick} className="hover:underline cursor-pointer">
            <span className="text-text-secondary">Dismissed:</span>{' '}
            <span className="text-red-400">{dismissedCount}</span>
            <span className="text-text-secondary ml-1">→</span>
          </button>
        )}
        <div className="ml-auto">
          <span className="text-text-secondary">Last run:</span>{' '}
          <span className="text-terminal-dim">{timeAgo(meta.last_run)}</span>
        </div>
      </div>
    </div>
  )
}
