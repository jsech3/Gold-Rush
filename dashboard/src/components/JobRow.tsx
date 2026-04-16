import { useState } from 'react'
import type { Job } from '../types/job'
import type { DismissReason } from '../hooks/useDismissed'
import { TierBadge } from './TierBadge'
import { DismissModal } from './DismissModal'
import { formatSource } from '../utils/filters'

interface JobRowProps {
  job: Job
  isApplied: boolean
  onToggleApplied: () => void
  onDismiss: (reason: DismissReason, note?: string) => void
}

function formatSalary(job: Job): string {
  if (job.salary_text) return job.salary_text
  if (job.salary_min && job.salary_max) {
    return `$${(job.salary_min / 1000).toFixed(0)}k-$${(job.salary_max / 1000).toFixed(0)}k`
  }
  if (job.salary_min) return `$${(job.salary_min / 1000).toFixed(0)}k+`
  return ''
}

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const hrs = Math.floor(diff / 3600000)
  if (hrs < 1) return 'just now'
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

export function JobRow({ job, isApplied, onToggleApplied, onDismiss }: JobRowProps) {
  const [showModal, setShowModal] = useState(false)
  const salary = formatSalary(job)
  const applied = isApplied || job.applied

  return (
    <>
      <div className={`border border-border rounded-lg p-3 bg-bg-card hover:border-border-hover transition-colors ${applied ? 'opacity-50' : ''}`}>
        <div className="flex items-start gap-3">
          {/* Applied checkbox */}
          <input
            type="checkbox"
            checked={applied}
            onChange={onToggleApplied}
            className="mt-1 accent-terminal-green shrink-0"
            title="Mark as applied"
          />

          {/* Main content */}
          <div className="flex-1 min-w-0">
            {/* Top row: tier + score + title */}
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <TierBadge tier={job.tier} />
              <span className="text-terminal-green text-xs font-bold">{job.goldness_score}</span>
              <a
                href={job.link}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-medium text-text-primary hover:text-terminal-green transition-colors truncate"
                title={job.title}
              >
                {job.title}
              </a>
            </div>

            {/* Bottom row: company, location, salary, source, time */}
            <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-text-secondary">
              <span className="text-text-primary">{job.company}</span>
              {job.location && <span>{job.location}</span>}
              {salary && <span className="text-terminal-dim">{salary}</span>}
              <span>{formatSource(job.source)}</span>
              <span>{timeAgo(job.found_date)}</span>
            </div>
          </div>

          {/* Dismiss button */}
          <button
            onClick={() => setShowModal(true)}
            className="shrink-0 mt-0.5 w-6 h-6 flex items-center justify-center rounded text-text-secondary hover:text-red-500 hover:bg-red-500/10 transition-colors text-xs"
            title="Remove job"
          >
            ✕
          </button>

          {/* Apply button */}
          <a
            href={job.link}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 px-3 py-1.5 rounded border border-terminal-dark text-terminal-green text-xs font-bold hover:bg-terminal-dark/10 transition-colors hidden sm:inline-block"
          >
            Apply →
          </a>
        </div>
      </div>

      {showModal && (
        <DismissModal
          jobTitle={job.title}
          onConfirm={(reason, note) => {
            onDismiss(reason, note)
            setShowModal(false)
          }}
          onCancel={() => setShowModal(false)}
        />
      )}
    </>
  )
}
