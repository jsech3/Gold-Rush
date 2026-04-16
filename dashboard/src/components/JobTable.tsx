import type { Job } from '../types/job'
import type { DismissReason } from '../hooks/useDismissed'
import { JobRow } from './JobRow'

interface JobTableProps {
  jobs: Job[]
  isApplied: (id: string) => boolean
  toggleApplied: (id: string) => void
  onDismiss: (jobId: string, reason: DismissReason, note?: string) => void
}

export function JobTable({ jobs, isApplied, toggleApplied, onDismiss }: JobTableProps) {
  if (jobs.length === 0) {
    return (
      <div className="border border-border rounded-lg p-8 bg-bg-card text-center">
        <p className="text-text-secondary text-sm">No jobs match your filters.</p>
        <p className="text-text-secondary text-xs mt-1">Try adjusting your search or filters.</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {jobs.map(job => (
        <JobRow
          key={job.job_id}
          job={job}
          isApplied={isApplied(job.job_id)}
          onToggleApplied={() => toggleApplied(job.job_id)}
          onDismiss={(reason, note) => onDismiss(job.job_id, reason, note)}
        />
      ))}
    </div>
  )
}
