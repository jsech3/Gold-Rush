import type { Job } from '../types/job'
import type { DismissReason } from '../hooks/useDismissed'
import { TierBadge } from './TierBadge'
import { formatSource } from '../utils/filters'

interface DismissedEntry {
  reason: DismissReason
  date: string
  note?: string
}

interface DismissedProps {
  jobs: Job[]
  dismissedMap: Record<string, DismissedEntry>
  undismiss: (id: string) => void
  onBack: () => void
}

const reasonLabels: Record<DismissReason, string> = {
  no_longer_available: 'No Longer Available',
  fake_job: 'Fake Job',
  not_relevant: 'Not Relevant',
  didnt_like: "Didn't Like",
  no_response: 'No Response',
  other: 'Other',
}

const reasonColors: Record<DismissReason, string> = {
  no_longer_available: 'text-text-secondary',
  fake_job: 'text-red-400',
  not_relevant: 'text-tier-bronze',
  didnt_like: 'text-text-secondary',
  no_response: 'text-yellow-400',
  other: 'text-text-secondary',
}

function formatSalary(job: Job): string {
  if (job.salary_text) return job.salary_text
  if (job.salary_min && job.salary_max) {
    return `$${(job.salary_min / 1000).toFixed(0)}k-$${(job.salary_max / 1000).toFixed(0)}k`
  }
  if (job.salary_min) return `$${(job.salary_min / 1000).toFixed(0)}k+`
  return ''
}

export function Dismissed({ jobs, dismissedMap, undismiss, onBack }: DismissedProps) {
  const entries = Object.entries(dismissedMap)
    .map(([jobId, entry]) => {
      const job = jobs.find(j => j.job_id === jobId)
      return job ? { job, ...entry } : null
    })
    .filter((x): x is { job: Job; reason: DismissReason; date: string; note?: string } => x !== null)
    .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())

  // Group by reason
  const grouped: Record<string, typeof entries> = {}
  for (const item of entries) {
    const key = item.reason
    if (!grouped[key]) grouped[key] = []
    grouped[key].push(item)
  }

  // Order reasons consistently
  const reasonOrder: DismissReason[] = ['no_response', 'fake_job', 'no_longer_available', 'not_relevant', 'didnt_like', 'other']
  const sortedReasons = reasonOrder.filter(r => grouped[r])

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-terminal-green font-bold text-lg">Dismissed Jobs</h2>
          <p className="text-text-secondary text-xs mt-0.5">
            {entries.length} job{entries.length !== 1 ? 's' : ''} dismissed
          </p>
        </div>
        <button
          onClick={onBack}
          className="px-3 py-1.5 rounded border border-border text-text-secondary text-xs hover:border-border-hover hover:text-terminal-green transition-colors"
        >
          ← Dashboard
        </button>
      </div>

      {entries.length === 0 ? (
        <div className="border border-border rounded-lg p-8 bg-bg-card text-center">
          <p className="text-text-secondary text-sm">No dismissed jobs yet.</p>
          <p className="text-text-secondary text-xs mt-1">
            Click the ✕ on any job to dismiss it.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {sortedReasons.map(reason => (
            <div key={reason}>
              <div className="flex items-center gap-3 mb-2">
                <h3 className={`text-xs font-bold uppercase ${reasonColors[reason]}`}>
                  {reasonLabels[reason]}
                </h3>
                <span className="text-text-secondary text-[10px]">
                  {grouped[reason].length}
                </span>
                <div className="flex-1 border-t border-border" />
              </div>

              <div className="space-y-2">
                {grouped[reason].map(({ job, note, date }) => {
                  const salary = formatSalary(job)
                  return (
                    <div
                      key={job.job_id}
                      className="border border-border rounded-lg p-3 bg-bg-card hover:border-border-hover transition-colors opacity-70"
                    >
                      <div className="flex items-start gap-3">
                        <button
                          onClick={() => undismiss(job.job_id)}
                          className="mt-0.5 shrink-0 text-xs text-text-secondary hover:text-terminal-green transition-colors"
                          title="Restore job"
                        >
                          ↩
                        </button>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <TierBadge tier={job.tier} />
                            <span className="text-terminal-green text-xs font-bold">{job.goldness_score}</span>
                            <a
                              href={job.link}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-sm font-medium text-text-primary hover:text-terminal-green transition-colors truncate"
                            >
                              {job.title}
                            </a>
                          </div>
                          <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-text-secondary">
                            <span className="text-text-primary">{job.company}</span>
                            {job.location && <span>{job.location}</span>}
                            {salary && <span className="text-terminal-dim">{salary}</span>}
                            <span>{formatSource(job.source)}</span>
                            {note && <span className="italic">"{note}"</span>}
                            <span className="ml-auto">dismissed {new Date(date).toLocaleDateString()}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
