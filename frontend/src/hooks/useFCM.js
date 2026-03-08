import { useState } from 'react'
import { messaging, requestFCMToken, onMessage } from '../lib/firebase'
import { supabase } from '../lib/supabase'

const TOKEN_ID_KEY = 'fcm_token_id'

export function useFCM() {
  const [tokenId, setTokenId] = useState(() => localStorage.getItem(TOKEN_ID_KEY))
  const [permissionState, setPermissionState] = useState(
    typeof Notification !== 'undefined' ? Notification.permission : 'default'
  )

  async function registerToken() {
    const fcmToken = await requestFCMToken()
    if (!fcmToken) {
      setPermissionState(Notification.permission)
      return
    }

    const { data, error } = await supabase
      .from('fcm_tokens')
      .upsert({ token: fcmToken }, { onConflict: 'token' })
      .select('id')
      .single()

    if (!error && data) {
      localStorage.setItem(TOKEN_ID_KEY, data.id)
      setTokenId(data.id)
    }
    setPermissionState(Notification.permission)
  }

  // 포그라운드 메시지: 서비스 워커가 백그라운드 처리, 여기선 콘솔만
  onMessage(messaging, () => {
    console.log('Foreground FCM message received — handled by SW on next visit')
  })

  return { tokenId, permissionState, registerToken }
}
