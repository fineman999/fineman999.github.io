import { initializeApp } from 'firebase/app'
import { getMessaging, getToken, onMessage } from 'firebase/messaging'

const firebaseConfig = JSON.parse(import.meta.env.VITE_FIREBASE_CONFIG || '{}')
const app = initializeApp(firebaseConfig)
export const messaging = getMessaging(app)

export async function requestFCMToken() {
  const permission = await Notification.requestPermission()
  if (permission !== 'granted') return null

  const registration = await navigator.serviceWorker.getRegistration('/sw.js')
  return getToken(messaging, {
    vapidKey: import.meta.env.VITE_FIREBASE_VAPID_KEY,
    serviceWorkerRegistration: registration
  })
}

export { onMessage }
