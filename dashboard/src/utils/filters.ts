import type { Job, Filters } from '../types/job'

export function filterJobs(
  jobs: Job[],
  filters: Filters,
  isApplied: (id: string) => boolean
): Job[] {
  const now = new Date()

  return jobs
    .filter(job => {
      // Tier filter
      if (filters.tiers.length > 0 && !filters.tiers.includes(job.tier)) return false

      // Source filter
      if (filters.sources.length > 0 && !filters.sources.includes(job.source)) return false

      // Date range
      if (filters.dateRange !== 'all' && job.found_date) {
        const found = new Date(job.found_date)
        const diffMs = now.getTime() - found.getTime()
        const diffDays = diffMs / (1000 * 60 * 60 * 24)
        if (filters.dateRange === 'today' && diffDays > 1) return false
        if (filters.dateRange === '7d' && diffDays > 7) return false
        if (filters.dateRange === '30d' && diffDays > 30) return false
      }

      // Search
      if (filters.search) {
        const q = filters.search.toLowerCase()
        const searchable = `${job.title} ${job.company} ${job.location} ${job.salary_text || ''}`.toLowerCase()
        if (!searchable.includes(q)) return false
      }

      // Hide applied
      if (filters.hideApplied && (isApplied(job.job_id) || job.applied)) return false

      return true
    })
    .sort((a, b) => {
      const dir = filters.sortDir === 'asc' ? -1 : 1
      switch (filters.sort) {
        case 'score':
          return (b.goldness_score - a.goldness_score) * dir
        case 'date': {
          const da = new Date(a.found_date).getTime()
          const db = new Date(b.found_date).getTime()
          return (db - da) * dir
        }
        case 'company':
          return a.company.localeCompare(b.company) * dir
        default:
          return 0
      }
    })
}

export function getUniqueSources(jobs: Job[]): string[] {
  return [...new Set(jobs.map(j => j.source))].sort()
}

export function formatSource(source: string): string {
  const map: Record<string, string> = {
    jsearch_api: 'JSearch',
    linkedin_email: 'LinkedIn',
    indeed_email: 'Indeed',
    hacker_news: 'HN',
  }
  return map[source] || source
}
