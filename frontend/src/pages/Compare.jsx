import React, { useState, useEffect } from 'react'
import { useLang } from '../App'
import { Search, X, Plus } from 'lucide-react'
import ClubLogo from '../components/ClubLogo'

const posColors = { GK: 'text-yellow-400', DEF: 'text-blue-400', MID: 'text-green-400', FWD: 'text-red-400' }
const lineColors = ['#22d3ee', '#f59e0b', '#ef4444', '#22c55e', '#a855f7', '#f97316']

export default function Compare() {
  const { t } = useLang()
  const [selectedIds, setSelectedIds] = useState([])
  const [data, setData] = useState(null)
  const [search, setSearch] = useState('')
  const [searchResults, setSearchResults] = useState([])

  useEffect(() => {
    if (!search && search !== '') return
    fetch(`/api/players/search-for-compare?q=${encodeURIComponent(search)}`)
      .then(r => r.json()).then(setSearchResults).catch(() => {})
  }, [search])

  useEffect(() => {
    if (!selectedIds.length) { setData(null); return }
    fetch(`/api/players/compare?ids=${selectedIds.join(',')}`)
      .then(r => r.json()).then(setData).catch(() => {})
  }, [selectedIds])

  const addPlayer = (id) => {
    if (selectedIds.length >= 6 || selectedIds.includes(id)) return
    setSelectedIds([...selectedIds, id])
    setSearch('')
  }

  const removePlayer = (id) => setSelectedIds(selectedIds.filter(x => x !== id))

  const maxPts = data ? Math.max(...data.players.flatMap(p => Object.values(p.points_by_matchday)), 1) : 1

  return (
    <div className="space-y-4 max-w-4xl mx-auto">
      <h2 className="text-lg font-bold text-white">📊 {t('compareTitle') || 'Compare Players'}</h2>

      {/* Search + selected chips */}
      <div className="space-y-2">
        <div className="flex gap-2 flex-wrap">
          {selectedIds.map((id, i) => {
            const p = data?.players.find(x => x.player.id === id)
            return (
              <span key={id} className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border"
                style={{ borderColor: lineColors[i], color: lineColors[i] }}>
                {p ? <ClubLogo club={p.player.club} size={14} /> : null}
                {p?.player.name || `#${id}`}
                <button onClick={() => removePlayer(id)} className="hover:text-white"><X size={12} /></button>
              </span>
            )
          })}
          {selectedIds.length < 6 && (
            <div className="relative flex-1 min-w-[200px]">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500" />
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Add player to compare..."
                className="w-full bg-ucl-dark border border-ucl-accent/20 rounded-full pl-8 pr-3 py-1.5 text-sm focus:border-ucl-accent focus:outline-none" />
              {search && searchResults.length > 0 && (
                <div className="absolute top-full left-0 right-0 bg-ucl-blue border border-ucl-accent/20 rounded-xl mt-1 max-h-48 overflow-y-auto z-20">
                  {searchResults.filter(p => !selectedIds.includes(p.id)).map(p => (
                    <button key={p.id} onClick={() => addPlayer(p.id)}
                      className="w-full flex items-center gap-2 px-3 py-2 hover:bg-ucl-accent/10 text-left text-sm">
                      <span className={`text-[10px] font-bold ${posColors[p.position]}`}>{p.position}</span>
                      <ClubLogo club={p.club} size={16} />
                      <span className="text-white flex-1">{p.name}</span>
                      <span className="text-xs text-gray-500">€{p.price}M</span>
                      <Plus size={14} className="text-ucl-accent" />
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Chart */}
      {data && data.players.length > 0 && (
        <div className="bg-ucl-blue/20 border border-ucl-accent/10 rounded-xl p-5">
          {/* Stats table */}
          <div className="grid gap-3 mb-6" style={{ gridTemplateColumns: `repeat(${data.players.length}, 1fr)` }}>
            {data.players.map((p, i) => (
              <div key={p.player.id} className="text-center rounded-lg p-2 border" style={{ borderColor: lineColors[i] + '40' }}>
                <div className="flex items-center justify-center gap-1 mb-1">
                  <ClubLogo club={p.player.club} size={16} />
                  <span className="text-xs font-bold text-white truncate">{p.player.name.split(' ').pop()}</span>
                </div>
                <div className="text-[10px] text-gray-500">{p.player.position} · €{p.player.price}M</div>
                <div className="grid grid-cols-3 gap-1 mt-1.5 text-[10px]">
                  <div><div className="text-gray-500">Total</div><div className="font-bold text-white">{p.total_points}</div></div>
                  <div><div className="text-gray-500">Avg</div><div className="font-bold" style={{ color: lineColors[i] }}>{p.avg_points}</div></div>
                  <div><div className="text-gray-500">Max</div><div className="font-bold text-white">{p.max_points}</div></div>
                </div>
              </div>
            ))}
          </div>

          {/* Bar chart */}
          <div className="text-xs text-gray-500 mb-2">Points per matchday</div>
          <div className="space-y-1">
            {data.matchdays.map(md => {
              const hasData = data.players.some(p => p.points_by_matchday[md.id] !== undefined)
              if (!hasData) return null
              return (
                <div key={md.id} className="flex items-center gap-2">
                  <div className="text-[10px] text-gray-600 w-16 text-right truncate">{md.name.replace('Knockout Play-offs','KO').slice(0,10)}</div>
                  <div className="flex-1 flex items-center gap-0.5 h-6">
                    {data.players.map((p, i) => {
                      const pts = p.points_by_matchday[md.id]
                      if (pts === undefined) return <div key={i} className="h-full" style={{ flex: 1 }}></div>
                      const width = Math.max(8, (pts / maxPts) * 100)
                      return (
                        <div key={i} className="h-full flex items-center" style={{ flex: 1 }}>
                          <div className="h-4 rounded-sm relative group" style={{ width: `${width}%`, backgroundColor: lineColors[i] }}>
                            <span className="absolute -top-4 left-0 text-[9px] font-bold" style={{ color: lineColors[i] }}>{pts}</span>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {!data && (
        <div className="text-center py-16 text-gray-600">
          <div className="text-4xl mb-3">📊</div>
          <p>Search and add players to compare their performance across matchdays</p>
        </div>
      )}
    </div>
  )
}
