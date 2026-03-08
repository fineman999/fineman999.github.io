export function NotifBanner({ permissionState, onEnable }) {
  if (permissionState === 'granted' || permissionState === 'denied') return null

  return (
    <div className="flex items-center justify-between gap-3 rounded-xl bg-blue-50 border border-blue-200 px-4 py-3">
      <p className="text-sm text-blue-800">새 글 알림을 받으시겠어요?</p>
      <button
        onClick={onEnable}
        className="shrink-0 text-sm font-medium text-blue-600 hover:text-blue-800"
      >
        알림 허용
      </button>
    </div>
  )
}
