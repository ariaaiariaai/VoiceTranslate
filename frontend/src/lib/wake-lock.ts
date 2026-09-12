// Screen Wake Lock — prevents iPhone from dimming during a tour.

let sentinel: WakeLockSentinel | null = null

export async function requestWakeLock(): Promise<boolean> {
  if (!('wakeLock' in navigator)) return false
  try {
    sentinel = await navigator.wakeLock.request('screen')
    sentinel.addEventListener('release', () => {
      sentinel = null
    })
    return true
  } catch (e) {
    console.warn('[wakeLock] failed', e)
    return false
  }
}

export async function releaseWakeLock(): Promise<void> {
  if (sentinel) {
    try {
      await sentinel.release()
    } catch {
      // ignore
    }
    sentinel = null
  }
}

// Re-acquire on visibility change (browsers release it when tab is hidden).
if (typeof document !== 'undefined') {
  document.addEventListener('visibilitychange', async () => {
    if (document.visibilityState === 'visible' && sentinel === null) {
      await requestWakeLock()
    }
  })
}
