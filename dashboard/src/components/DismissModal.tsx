import { useState } from 'react'
import type { DismissReason } from '../hooks/useDismissed'

interface DismissModalProps {
  jobTitle: string
  onConfirm: (reason: DismissReason, note?: string) => void
  onCancel: () => void
}

const reasons: { value: DismissReason; label: string }[] = [
  { value: 'no_longer_available', label: 'No longer available' },
  { value: 'fake_job', label: 'Fake job' },
  { value: 'not_relevant', label: 'Not relevant' },
  { value: 'didnt_like', label: "Just didn't like" },
  { value: 'other', label: 'Other' },
]

export function DismissModal({ jobTitle, onConfirm, onCancel }: DismissModalProps) {
  const [selected, setSelected] = useState<DismissReason | null>(null)
  const [note, setNote] = useState('')

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" onClick={onCancel}>
      <div
        className="w-full max-w-sm border border-border rounded-lg bg-bg-card p-5"
        onClick={e => e.stopPropagation()}
      >
        <h3 className="text-terminal-green text-sm font-bold mb-1">Remove Job</h3>
        <p className="text-text-secondary text-xs mb-4 truncate" title={jobTitle}>
          {jobTitle}
        </p>

        <p className="text-text-secondary text-xs mb-2">Why are you removing this?</p>

        <div className="space-y-1.5 mb-4">
          {reasons.map(r => (
            <button
              key={r.value}
              onClick={() => setSelected(r.value)}
              className={`w-full text-left px-3 py-2 rounded text-xs border transition-colors ${
                selected === r.value
                  ? 'border-terminal-dark text-terminal-green bg-terminal-dark/10'
                  : 'border-border text-text-secondary hover:border-border-hover'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>

        {selected === 'other' && (
          <input
            type="text"
            placeholder="Reason..."
            value={note}
            onChange={e => setNote(e.target.value)}
            className="w-full bg-bg-input border border-border rounded px-3 py-1.5 text-xs text-text-primary focus:outline-none focus:border-terminal-dark mb-4"
            autoFocus
          />
        )}

        <div className="flex gap-2 justify-end">
          <button
            onClick={onCancel}
            className="px-3 py-1.5 rounded border border-border text-text-secondary text-xs hover:border-border-hover transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => selected && onConfirm(selected, selected === 'other' ? note : undefined)}
            disabled={!selected}
            className={`px-3 py-1.5 rounded text-xs font-bold transition-colors ${
              selected
                ? 'border border-red-500/50 text-red-400 hover:bg-red-500/10 cursor-pointer'
                : 'border border-border text-text-secondary opacity-40 cursor-not-allowed'
            }`}
          >
            Remove
          </button>
        </div>
      </div>
    </div>
  )
}
