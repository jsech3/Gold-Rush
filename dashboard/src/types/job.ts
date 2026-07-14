export interface Job {
  id: number
  job_id: string
  title: string
  company: string
  location: string
  salary_min: number | null
  salary_max: number | null
  salary_text: string | null
  link: string
  source: string
  posted_date: string | null
  found_date: string
  goldness_score: number
  tier: 'platinum' | 'gold' | 'silver' | 'bronze'
  emailed: boolean
  applied: boolean
}

export interface Meta {
  last_run: string
  total_jobs: number
  new_jobs_this_run: number
  tier_counts: {
    platinum: number
    gold: number
    silver: number
    bronze: number
  }
  source_counts: Record<string, number>
  export_time: string
  demo?: boolean
  demo_note?: string
}

export type SortField = 'score' | 'date' | 'company'
export type SortDir = 'asc' | 'desc'

export interface Filters {
  tiers: string[]
  sources: string[]
  dateRange: 'today' | '7d' | '30d' | 'all'
  search: string
  hideApplied: boolean
  sort: SortField
  sortDir: SortDir
}
