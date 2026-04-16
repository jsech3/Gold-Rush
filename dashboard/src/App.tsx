import { useState } from 'react'
import { PasswordGate, useAuth } from './components/PasswordGate'
import { Layout } from './components/Layout'
import { StatsBar } from './components/StatsBar'
import { FilterBar } from './components/FilterBar'
import { JobTable } from './components/JobTable'
import { Tracker } from './components/Tracker'
import { Dismissed } from './components/Dismissed'
import { useJobs } from './hooks/useJobs'
import { useApplied } from './hooks/useApplied'
import { useDismissed } from './hooks/useDismissed'
import { filterJobs, getUniqueSources } from './utils/filters'
import type { Filters } from './types/job'

const defaultFilters: Filters = {
  tiers: [],
  sources: [],
  dateRange: 'all',
  search: '',
  hideApplied: false,
  sort: 'score',
  sortDir: 'desc',
}

function Dashboard() {
  const { jobs, meta, loading, error } = useJobs()
  const { isApplied, toggleApplied, appliedCount, appliedMap } = useApplied()
  const { isDismissed, dismiss, dismissMany, undismiss, dismissedMap, dismissedCount } = useDismissed()
  const [filters, setFilters] = useState<Filters>(defaultFilters)
  const [page, setPage] = useState<'dashboard' | 'tracker' | 'dismissed'>('dashboard')

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <span className="text-terminal-green text-sm">
            Loading<span className="cursor-blink">_</span>
          </span>
        </div>
      </Layout>
    )
  }

  if (error) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <span className="text-red-500 text-sm">Error: {error}</span>
        </div>
      </Layout>
    )
  }

  if (page === 'tracker') {
    return (
      <Layout>
        <Tracker
          jobs={jobs}
          appliedMap={appliedMap}
          toggleApplied={toggleApplied}
          onDismiss={(jobId) => { dismiss(jobId, 'no_response'); toggleApplied(jobId) }}
          onDismissMany={(jobIds) => { dismissMany(jobIds, 'no_response'); jobIds.forEach(id => toggleApplied(id)) }}
          onBack={() => setPage('dashboard')}
        />
      </Layout>
    )
  }

  if (page === 'dismissed') {
    return (
      <Layout>
        <Dismissed
          jobs={jobs}
          dismissedMap={dismissedMap}
          undismiss={undismiss}
          onBack={() => setPage('dashboard')}
        />
      </Layout>
    )
  }

  const visible = jobs.filter(j => !isDismissed(j.job_id))
  const filtered = filterJobs(visible, filters, isApplied)
  const sources = getUniqueSources(visible)

  return (
    <Layout>
      {meta && <StatsBar meta={meta} appliedCount={appliedCount} dismissedCount={dismissedCount} onTrackerClick={() => setPage('tracker')} onDismissedClick={() => setPage('dismissed')} />}
      <FilterBar
        filters={filters}
        setFilters={setFilters}
        sources={sources}
        resultCount={filtered.length}
      />
      <JobTable
        jobs={filtered}
        isApplied={isApplied}
        toggleApplied={toggleApplied}
        onDismiss={(jobId, reason, note) => dismiss(jobId, reason, note)}
      />
    </Layout>
  )
}

export default function App() {
  const { authed, login } = useAuth()

  if (!authed) {
    return <PasswordGate onLogin={login} />
  }

  return <Dashboard />
}
