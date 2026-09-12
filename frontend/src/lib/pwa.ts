// PWA install helpers.
import { writable } from 'svelte/store'

export const deferredPrompt = writable<any>(null)
export const isInstalled = writable<boolean>(false)

export function initPWA() {
  if (typeof window === 'undefined') return

  // Already installed (iOS sets navigator.standalone)
  const standalone =
    window.matchMedia?.('(display-mode: standalone)').matches ||
    // @ts-ignore
    window.navigator.standalone === true
  isInstalled.set(standalone)

  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault()
    deferredPrompt.set(e)
  })

  window.addEventListener('appinstalled', () => {
    isInstalled.set(true)
    deferredPrompt.set(null)
  })
}

export async function promptInstall(): Promise<boolean> {
  let dp: any = null
  const unsub = deferredPrompt.subscribe((v) => (dp = v))
  unsub()
  if (!dp) return false
  dp.prompt()
  const choice = await dp.userChoice
  deferredPrompt.set(null)
  return choice.outcome === 'accepted'
}
