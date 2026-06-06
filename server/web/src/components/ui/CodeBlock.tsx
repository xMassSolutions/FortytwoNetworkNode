import { useState } from 'react'

export default function CodeBlock({ children, label = 'shell' }: { children: string; label?: string }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard?.writeText(children).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1400)
    })
  }
  return (
    <div className="code">
      <div className="code-head">
        <span className="code-label">{label}</span>
        <button className="btn sm ghost" onClick={copy}>
          {copied ? 'copied ✓' : 'copy'}
        </button>
      </div>
      <pre className="code-body">{children}</pre>
    </div>
  )
}
