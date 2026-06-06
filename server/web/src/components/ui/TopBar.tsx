import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Logo } from './Logo'
import ThemeToggle from './ThemeToggle'

export default function TopBar({
  children,
  right,
  logoTo = '/dashboard',
}: {
  children?: ReactNode
  right?: ReactNode
  logoTo?: string
}) {
  return (
    <header className="topbar">
      <div className="container">
        <div className="bar">
          <Link to={logoTo} aria-label="Home">
            <Logo />
          </Link>
          <nav className="row gap-4" style={{ marginLeft: 10 }}>
            {children}
          </nav>
          <div className="row gap-8" style={{ marginLeft: 'auto' }}>
            {right}
            <ThemeToggle />
          </div>
        </div>
      </div>
    </header>
  )
}
