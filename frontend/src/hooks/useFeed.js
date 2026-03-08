import { useState, useEffect, useCallback } from 'react'
import { supabase } from '../lib/supabase'

export function useFeed({ siteId = null, limit = 50 } = {}) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchFeed = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      let query = supabase
        .from('items')
        .select('*, sites(name, category)')
        .order('scraped_at', { ascending: false })
        .limit(limit)

      if (siteId) {
        query = query.eq('site_id', siteId)
      }

      const { data, error } = await query
      if (error) throw error
      setItems(data || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [siteId, limit])

  useEffect(() => { fetchFeed() }, [fetchFeed])

  return { items, loading, error, refetch: fetchFeed }
}
