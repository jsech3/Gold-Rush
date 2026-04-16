import { useState, useEffect } from 'react'
import type { Job, Meta } from '../types/job'

export function useJobs() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [meta, setMeta] = useState<Meta | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchData() {
      try {
        const [jobsRes, metaRes] = await Promise.all([
          fetch('/jobs.json'),
          fetch('/meta.json'),
        ])

        if (!jobsRes.ok) throw new Error('Failed to load jobs.json')
        if (!metaRes.ok) throw new Error('Failed to load meta.json')

        const jobsData: Job[] = await jobsRes.json()
        const metaData: Meta = await metaRes.json()

        setJobs(jobsData)
        setMeta(metaData)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  return { jobs, meta, loading, error }
}
