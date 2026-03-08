import { useState, useEffect } from 'react'
import { supabase } from './lib/supabase'
import { useFeed } from './hooks/useFeed'
import { useFCM } from './hooks/useFCM'
import { FeedCard } from './components/FeedCard'
import { FilterBar } from './components/FilterBar'
import { NotifBanner } from './components/NotifBanner'

export default function App() {
  const [sites, setSites] = useState([])
  const [selectedSiteId, setSelectedSiteId] = useState(null)
  const { items, loading, error } = useFeed({ siteId: selectedSiteId })
  const { permissionState, registerToken } = useFCM()

  useEffect(() => {
    supabase
      .from('sites')
      .select('id, name, category')
      .eq('is_active', true)
      .then(({ data }) => setSites(data || []))
  }, [])

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-10 bg-white border-b border-slate-200 px-4 py-3">
        <h1 className="text-lg font-bold text-slate-900 mb-3">News Feed</h1>
        <FilterBar sites={sites} selectedId={selectedSiteId} onSelect={setSelectedSiteId} />
      </header>

      <main className="max-w-2xl mx-auto px-4 py-4 space-y-3">
        <NotifBanner permissionState={permissionState} onEnable={registerToken} />

        {loading && (
          <p className="text-center text-slate-400 py-8">불러오는 중...</p>
        )}
        {error && (
          <p className="text-center text-red-500 py-8">{error}</p>
        )}
        {!loading && items.map(item => (
          <FeedCard key={item.id} item={item} />
        ))}
        {!loading && items.length === 0 && !error && (
          <p className="text-center text-slate-400 py-8">아직 아이템이 없습니다.</p>
        )}
      </main>
    </div>
  )
}
