import { useEffect, useRef, useState } from 'react'
import { AuthError, goToLogin } from '../lib/api'

interface PollState<T> {
  data: T | null
  error: string | null
  loading: boolean
  lastUpdated: number | null
}

/**
 * Poll `fn` every `intervalMs`. Pauses while the tab is hidden and refreshes
 * immediately on return. A 401 (AuthError) bounces to the login page.
 * `key` re-subscribes when it changes (e.g. switching node id).
 */
export function usePoll<T>(fn: () => Promise<T>, intervalMs: number, key: string | number = ''): PollState<T> {
  const [state, setState] = useState<PollState<T>>({
    data: null,
    error: null,
    loading: true,
    lastUpdated: null,
  })
  const fnRef = useRef(fn)
  fnRef.current = fn

  useEffect(() => {
    let timer: ReturnType<typeof setInterval> | null = null
    let alive = true

    const tick = async () => {
      try {
        const data = await fnRef.current()
        if (!alive) return
        setState({ data, error: null, loading: false, lastUpdated: Date.now() })
      } catch (e) {
        if (e instanceof AuthError) {
          goToLogin()
          return
        }
        if (!alive) return
        setState((s) => ({ ...s, error: (e as Error).message, loading: false }))
      }
    }

    const start = () => {
      if (timer) return
      timer = setInterval(tick, intervalMs)
    }
    const stop = () => {
      if (timer) {
        clearInterval(timer)
        timer = null
      }
    }

    const onVis = () => {
      if (document.hidden) {
        stop()
      } else {
        tick()
        start()
      }
    }

    tick()
    start()
    document.addEventListener('visibilitychange', onVis)
    return () => {
      alive = false
      stop()
      document.removeEventListener('visibilitychange', onVis)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs, key])

  return state
}
