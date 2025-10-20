'use client'

import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { useAuth } from '../src/lib/auth-context'

export default function Watchlist() {
  const { user } = useAuth()
  const apiBase = process.env.NEXT_PUBLIC_API_URL

  const [loading, setLoading] = useState(true)
  const [watchlist, setWatchlist] = useState<string[]>([])

  useEffect(() => {
    const load = async () => {
      if (!user?.id) {
        setWatchlist([])
        setLoading(false)
        return
      }

      try {
        const res = await fetch(`${apiBase}/api/user/preferences?user_id=${encodeURIComponent(user.id)}`)
        if (!res.ok) throw new Error('Failed to fetch watchlist')
        const data = await res.json()
        setWatchlist(data.watchlist_stocks || [])
      } catch (e) {
        toast.error('Failed to load watchlist')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [apiBase, user?.id])

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Watchlist</h2>
      {loading ? (
        <div className="text-sm text-gray-600 dark:text-gray-300">Loading...</div>
      ) : watchlist.length === 0 ? (
        <div className="text-sm text-gray-600 dark:text-gray-300">No symbols in your watchlist.</div>
      ) : (
        <ul className="space-y-2">
          {watchlist.map((sym) => (
            <li key={sym} className="text-sm text-gray-800 dark:text-gray-100">{sym}</li>
          ))}
        </ul>
      )}
    </div>
  )
}


