import type { CSSProperties, ReactNode } from 'react'

interface GlassCardProps {
  /** When set, renders the window titlebar (traffic dots + caption). */
  caption?: string
  /** Right-aligned controls in the titlebar / header. */
  actions?: ReactNode
  /** Show the macOS-ish neutral window dots. Default true when caption set. */
  chrome?: boolean
  hover?: boolean
  className?: string
  bodyClass?: string
  style?: CSSProperties
  children: ReactNode
}

/**
 * The signature "glass window" panel. Frosted, floating, with a subtle top
 * sheen. Optionally wears window chrome (a titlebar with neutral dots) to read
 * as a real window/pane.
 */
export default function GlassCard({
  caption,
  actions,
  chrome,
  hover = false,
  className = '',
  bodyClass = '',
  style,
  children,
}: GlassCardProps) {
  const showBar = caption != null || actions != null
  const showChrome = chrome ?? caption != null
  return (
    <section className={`glass ${hover ? 'hover' : ''} ${className}`} style={style}>
      {showBar && (
        <div className="win-bar">
          {showChrome && (
            <span className="win-dots" aria-hidden>
              <i />
              <i />
              <i />
            </span>
          )}
          {caption && <span className="win-cap">{caption}</span>}
          {actions && <span className="win-actions">{actions}</span>}
        </div>
      )}
      <div className={`win-body ${bodyClass}`}>{children}</div>
    </section>
  )
}
