import type { Filters, SortField } from '../types/job'
import { formatSource } from '../utils/filters'

interface FilterBarProps {
  filters: Filters
  setFilters: (f: Filters) => void
  sources: string[]
  resultCount: number
}

export function FilterBar({ filters, setFilters, sources, resultCount }: FilterBarProps) {
  const update = (partial: Partial<Filters>) => setFilters({ ...filters, ...partial })

  const toggleTier = (tier: string) => {
    const tiers = filters.tiers.includes(tier)
      ? filters.tiers.filter(t => t !== tier)
      : [...filters.tiers, tier]
    update({ tiers })
  }

  const toggleSource = (src: string) => {
    const srcs = filters.sources.includes(src)
      ? filters.sources.filter(s => s !== src)
      : [...filters.sources, src]
    update({ sources: srcs })
  }

  const tierBtn = (tier: string, color: string) => (
    <button
      key={tier}
      onClick={() => toggleTier(tier)}
      className={`px-2 py-1 rounded text-[10px] uppercase font-bold border transition-colors ${
        filters.tiers.includes(tier) || filters.tiers.length === 0
          ? `${color} opacity-100`
          : `${color} opacity-30`
      }`}
    >
      {tier}
    </button>
  )

  return (
    <div className="border border-border rounded-lg p-3 mb-4 bg-bg-card space-y-3">
      {/* Row 1: Search + date range */}
      <div className="flex flex-wrap gap-2 items-center">
        <input
          type="text"
          placeholder="Search jobs..."
          value={filters.search}
          onChange={e => update({ search: e.target.value })}
          className="flex-1 min-w-[200px] bg-bg-input border border-border rounded px-3 py-1.5 text-xs text-text-primary focus:outline-none focus:border-terminal-dark"
        />

        <div className="flex gap-1 text-xs">
          {(['today', '7d', '30d', 'all'] as const).map(range => (
            <button
              key={range}
              onClick={() => update({ dateRange: range })}
              className={`px-2 py-1 rounded border transition-colors ${
                filters.dateRange === range
                  ? 'border-terminal-dark text-terminal-green bg-terminal-dark/10'
                  : 'border-border text-text-secondary hover:border-border-hover'
              }`}
            >
              {range}
            </button>
          ))}
        </div>
      </div>

      {/* Row 2: Tiers + Sources + Sort + Applied toggle */}
      <div className="flex flex-wrap gap-2 items-center">
        <div className="flex gap-1">
          {tierBtn('platinum', 'border-tier-platinum/30 text-tier-platinum')}
          {tierBtn('gold', 'border-tier-gold/30 text-tier-gold')}
          {tierBtn('silver', 'border-tier-silver/30 text-tier-silver')}
          {tierBtn('bronze', 'border-tier-bronze/30 text-tier-bronze')}
        </div>

        <div className="w-px h-5 bg-border hidden sm:block" />

        <div className="flex gap-1">
          {sources.map(src => (
            <button
              key={src}
              onClick={() => toggleSource(src)}
              className={`px-2 py-1 rounded text-[10px] border transition-colors ${
                filters.sources.includes(src) || filters.sources.length === 0
                  ? 'border-terminal-dark/30 text-terminal-dim opacity-100'
                  : 'border-border text-text-secondary opacity-30'
              }`}
            >
              {formatSource(src)}
            </button>
          ))}
        </div>

        <div className="w-px h-5 bg-border hidden sm:block" />

        <select
          value={filters.sort}
          onChange={e => update({ sort: e.target.value as SortField })}
          className="bg-bg-input border border-border rounded px-2 py-1 text-xs text-text-primary focus:outline-none"
        >
          <option value="score">Score</option>
          <option value="date">Date</option>
          <option value="company">Company</option>
        </select>

        <button
          onClick={() => update({ sortDir: filters.sortDir === 'desc' ? 'asc' : 'desc' })}
          className="px-2 py-1 rounded border border-border text-text-secondary text-xs hover:border-border-hover transition-colors"
        >
          {filters.sortDir === 'desc' ? '↓' : '↑'}
        </button>

        <div className="w-px h-5 bg-border hidden sm:block" />

        <label className="flex items-center gap-1.5 text-xs text-text-secondary cursor-pointer">
          <input
            type="checkbox"
            checked={filters.hideApplied}
            onChange={e => update({ hideApplied: e.target.checked })}
            className="accent-terminal-green"
          />
          Hide applied
        </label>

        <span className="ml-auto text-xs text-text-secondary">{resultCount} jobs</span>
      </div>
    </div>
  )
}
