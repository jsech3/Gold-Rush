import type { ReactNode } from 'react'

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-bg-primary flex flex-col">
      <header className="border-b border-border px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-terminal-green font-bold text-lg">GOLD RUSH</h1>
          <span className="text-text-secondary text-xs hidden sm:inline">// job dashboard</span>
        </div>
        <span className="text-text-secondary text-xs">DAITIQ</span>
      </header>

      <main className="flex-1 p-4 max-w-7xl mx-auto w-full">
        {children}
      </main>

      <footer className="border-t border-border px-4 py-2 text-center text-text-secondary text-xs">
        Gold Rush &middot; DAITIQ
      </footer>
    </div>
  )
}
