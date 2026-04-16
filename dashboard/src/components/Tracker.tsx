import type { Job } from '../types/job'
import { TierBadge } from './TierBadge'
import { formatSource } from '../utils/filters'

interface TrackerProps {
  jobs: Job[]
  appliedMap: Record<string, string>
  toggleApplied: (id: string) => void
  onDismiss: (jobId: string) => void
  onDismissMany: (jobIds: string[]) => void
  onBack: () => void
}

type AgingStatus = 'active' | 'stale' | 'cold'

function getAgingStatus(dateApplied: string): AgingStatus {
  const days = (Date.now() - new Date(dateApplied).getTime()) / (1000 * 60 * 60 * 24)
  if (days >= 21) return 'cold'
  if (days >= 14) return 'stale'
  return 'active'
}

function getDaysAgo(dateApplied: string): number {
  return Math.floor((Date.now() - new Date(dateApplied).getTime()) / (1000 * 60 * 60 * 24))
}

const agingBorder: Record<AgingStatus, string> = {
  active: 'border-terminal-dark/40',
  stale: 'border-yellow-500/50',
  cold: 'border-red-500/50',
}

const agingBadgeStyle: Record<AgingStatus, string> = {
  active: '',
  stale: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
  cold: 'bg-red-500/15 text-red-400 border-red-500/30',
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
}

function formatSalary(job: Job): string {
  if (job.salary_text) return job.salary_text
  if (job.salary_min && job.salary_max) {
    return `$${(job.salary_min / 1000).toFixed(0)}k-$${(job.salary_max / 1000).toFixed(0)}k`
  }
  if (job.salary_min) return `$${(job.salary_min / 1000).toFixed(0)}k+`
  return ''
}

interface AppliedJob {
  job: Job
  dateApplied: string
  aging: AgingStatus
  daysAgo: number
}

function TrackerRow({ item, toggleApplied, onDismiss }: { item: AppliedJob; toggleApplied: (id: string) => void; onDismiss: (id: string) => void }) {
  const { job, aging, daysAgo } = item
  const salary = formatSalary(job)

  return (
    <div className={`border rounded-lg p-3 bg-bg-card hover:border-border-hover transition-colors ${agingBorder[aging]} ${aging === 'cold' ? 'opacity-60' : ''}`}>
      <div className="flex items-start gap-3">
        <button
          onClick={() => toggleApplied(job.job_id)}
          className="mt-0.5 shrink-0 text-[10px] text-text-secondary hover:text-red-500 transition-colors"
          title="Remove from tracker"
        >
          ✕
        </button>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <TierBadge tier={job.tier} />
            <span className="text-terminal-green text-xs font-bold">{job.goldness_score}</span>
            {aging !== 'active' && (
              <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold border ${agingBadgeStyle[aging]}`}>
                {daysAgo}d
              </span>
            )}
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
          </div>
        </div>

        {aging === 'cold' ? (
          <button
            onClick={() => onDismiss(job.job_id)}
            className="shrink-0 px-3 py-1.5 rounded border border-red-500/30 text-red-400 text-xs font-bold hover:bg-red-500/10 transition-colors hidden sm:inline-block"
          >
            Archive
          </button>
        ) : (
          <a
            href={job.link}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 px-3 py-1.5 rounded border border-terminal-dark text-terminal-green text-xs font-bold hover:bg-terminal-dark/10 transition-colors hidden sm:inline-block"
          >
            View →
          </a>
        )}
      </div>
    </div>
  )
}

export function Tracker({ jobs, appliedMap, toggleApplied, onDismiss, onDismissMany, onBack }: TrackerProps) {
  const appliedJobs: AppliedJob[] = Object.entries(appliedMap)
    .map(([jobId, dateApplied]) => {
      const job = jobs.find(j => j.job_id === jobId)
      if (!job) return null
      return { job, dateApplied, aging: getAgingStatus(dateApplied), daysAgo: getDaysAgo(dateApplied) }
    })
    .filter((x): x is AppliedJob => x !== null)
    .sort((a, b) => new Date(b.dateApplied).getTime() - new Date(a.dateApplied).getTime())

  const activeJobs = appliedJobs.filter(j => j.aging === 'active')
  const staleJobs = appliedJobs.filter(j => j.aging === 'stale')
  const coldJobs = appliedJobs.filter(j => j.aging === 'cold')

  // Group active+stale by date
  const freshJobs = [...activeJobs, ...staleJobs]
  const grouped: Record<string, AppliedJob[]> = {}
  for (const item of freshJobs) {
    const dateKey = new Date(item.dateApplied).toLocaleDateString('en-US')
    if (!grouped[dateKey]) grouped[dateKey] = []
    grouped[dateKey].push(item)
  }
  const dateKeys = Object.keys(grouped)

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-terminal-green font-bold text-lg">Application Tracker</h2>
          <p className="text-text-secondary text-xs mt-0.5">
            {appliedJobs.length} application{appliedJobs.length !== 1 ? 's' : ''} tracked
            {staleJobs.length > 0 && <span className="text-yellow-400 ml-2">{staleJobs.length} stale</span>}
            {coldJobs.length > 0 && <span className="text-red-400 ml-2">{coldJobs.length} cold</span>}
          </p>
        </div>
        <button
          onClick={onBack}
          className="px-3 py-1.5 rounded border border-border text-text-secondary text-xs hover:border-border-hover hover:text-terminal-green transition-colors"
        >
          ← Dashboard
        </button>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 mb-4 text-[10px] text-text-secondary">
        <span><span className="inline-block w-2 h-2 rounded-full bg-terminal-dark mr-1" /> Active (0–13d)</span>
        <span><span className="inline-block w-2 h-2 rounded-full bg-yellow-500 mr-1" /> Stale (14–20d)</span>
        <span><span className="inline-block w-2 h-2 rounded-full bg-red-500 mr-1" /> Cold (21d+)</span>
      </div>

      {appliedJobs.length === 0 ? (
        <div className="border border-border rounded-lg p-8 bg-bg-card text-center">
          <p className="text-text-secondary text-sm">No applications tracked yet.</p>
          <p className="text-text-secondary text-xs mt-1">
            Check the box next to jobs on the dashboard after you apply.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Active + Stale grouped by date */}
          {dateKeys.map(dateKey => {
            const items = grouped[dateKey]
            const hasStale = items.some(i => i.aging === 'stale')
            return (
              <div key={dateKey}>
                <div className="flex items-center gap-3 mb-2">
                  <h3 className={`text-xs font-bold uppercase ${hasStale ? 'text-yellow-400' : 'text-terminal-dim'}`}>
                    {formatDate(items[0].dateApplied)}
                  </h3>
                  <span className="text-text-secondary text-[10px]">
                    {items.length} app{items.length !== 1 ? 's' : ''}
                  </span>
                  <div className="flex-1 border-t border-border" />
                </div>

                <div className="space-y-2">
                  {items.map(item => (
                    <TrackerRow
                      key={item.job.job_id}
                      item={item}
                      toggleApplied={toggleApplied}
                      onDismiss={onDismiss}
                    />
                  ))}
                </div>
              </div>
            )
          })}

          {/* Cold section */}
          {coldJobs.length > 0 && (
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h3 className="text-xs font-bold uppercase text-red-400">
                  Cold — No Response (21d+)
                </h3>
                <span className="text-text-secondary text-[10px]">
                  {coldJobs.length} job{coldJobs.length !== 1 ? 's' : ''}
                </span>
                <div className="flex-1 border-t border-red-500/20" />
              </div>

              <div className="space-y-2">
                {coldJobs.map(item => (
                  <TrackerRow
                    key={item.job.job_id}
                    item={item}
                    toggleApplied={toggleApplied}
                    onDismiss={onDismiss}
                  />
                ))}
              </div>

              <button
                onClick={() => onDismissMany(coldJobs.map(j => j.job.job_id))}
                className="mt-3 w-full py-2 rounded border border-red-500/30 text-red-400 text-xs font-bold hover:bg-red-500/10 transition-colors"
              >
                Archive all {coldJobs.length} cold job{coldJobs.length !== 1 ? 's' : ''}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
