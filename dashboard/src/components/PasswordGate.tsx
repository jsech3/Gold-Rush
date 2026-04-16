import { useState, type FormEvent } from 'react'

const CORRECT_PASSWORD = import.meta.env.VITE_DASHBOARD_PASSWORD || 'goldrush'
const SESSION_KEY = 'goldrush-auth'

export function useAuth() {
  const [authed, setAuthed] = useState(() => sessionStorage.getItem(SESSION_KEY) === 'true')

  const login = (password: string): boolean => {
    if (password === CORRECT_PASSWORD) {
      sessionStorage.setItem(SESSION_KEY, 'true')
      setAuthed(true)
      return true
    }
    return false
  }

  return { authed, login }
}

export function PasswordGate({ onLogin }: { onLogin: (pw: string) => boolean }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState(false)
  const [shake, setShake] = useState(false)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!onLogin(password)) {
      setError(true)
      setShake(true)
      setTimeout(() => setShake(false), 500)
      setPassword('')
    }
  }

  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center p-4">
      <div className={`w-full max-w-md ${shake ? 'animate-[shake_0.5s_ease-in-out]' : ''}`}>
        <div className="border border-border rounded-lg p-8 bg-bg-card">
          <div className="text-terminal-green text-sm mb-6 font-mono">
            <span className="text-text-secondary">$</span> gold_rush --dashboard
          </div>

          <h1 className="text-terminal-green text-xl font-bold mb-2">GOLD RUSH</h1>
          <p className="text-text-secondary text-xs mb-6">Job hunting dashboard // DAITIQ</p>

          <form onSubmit={handleSubmit}>
            <label className="block text-text-secondary text-xs mb-2">
              Password required:
            </label>
            <div className="flex gap-2">
              <input
                type="password"
                value={password}
                onChange={e => { setPassword(e.target.value); setError(false) }}
                className="flex-1 bg-bg-input border border-border rounded px-3 py-2 text-terminal-green text-sm focus:outline-none focus:border-terminal-dark"
                placeholder="Enter password..."
                autoFocus
              />
              <button
                type="submit"
                className="bg-terminal-dark hover:bg-terminal-dim text-bg-primary px-4 py-2 rounded text-sm font-bold transition-colors"
              >
                &gt;
              </button>
            </div>
            {error && (
              <p className="text-red-500 text-xs mt-2">Access denied.</p>
            )}
          </form>
        </div>
      </div>
    </div>
  )
}
