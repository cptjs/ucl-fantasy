import React, { useEffect, useState } from 'react'
import { useLang } from '../App'
import { ChevronDown, ChevronUp, ArrowUpDown, Search } from 'lucide-react'

const posColors = { GK: 'bg-yellow-500/20 text-yellow-400', DEF: 'bg-blue-500/20 text-blue-400', MID: 'bg-green-500/20 text-green-400', FWD: 'bg-red-500/20 text-red-400' }
const confColor = { high: 'text-ucl-green', medium: 'text-yellow-400', low: 'text-ucl-red' }
const riskColor = { low: 'text-ucl-green', medium: 'text-yellow-400', high: 'text-ucl-red' }
const riskDot = { low: 'bg-ucl-green', medium: 'bg-yellow-400', high: 'bg-ucl-red' }

export default function Predictions() {
  const { t } = useLang()
  const [predictions, setPredictions] = useState([])
  const [expanded, setExpanded] = useState(null)
  const [filterPos, setFilterPos] = useState('')
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState('expected_points')
  const [sortDir, setSortDir] = useState(-1)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch('/api/predictions')
      .then(r => { if (!r.ok) throw new Error(); return r.json() })
      .then(setPredictions)
      .catch(() => setError(t('noData')))
  }, [])

  const toggleSort = (field) => {
    if (sortBy === field) setSortDir(-sortDir)
    else { setSortBy(field); setSortDir(-1) }
  }

  let filtered = predictions
  if (filterPos) filtered = filtered.filter(p => p.position === filterPos)
  if (search) filtered = filtered.filter(p => p.name.toLowerCase().includes(search.toLowerCase()) || p.club.toLowerCase().includes(search.toLowerCase()))
  filtered = [...filtered].sort((a, b) => (a[sortBy] > b[sortBy] ? sortDir : -sortDir))

  if (error) return <p className="text-center text-gray-500 py-16">{error}</p>

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-2 flex-wrap items-center">
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search player or club..."
            className="w-full bg-ucl-dark border border-ucl-accent/20 rounded-lg pl-9 pr-3 py-2 text-sm focus:border-ucl-accent focus:outline-none" />
        </div>
        <div className="flex rounded-lg overflow-hidden border border-ucl-accent/20">
          <button onClick={() => setFilterPos('')}
            className={`px-3 py-2 text-xs font-medium transition ${!filterPos ? 'bg-ucl-accent text-ucl-dark' : 'bg-ucl-dark text-gray-400 hover:text-white'}`}>
            All
          </button>
          {['GK','DEF','MID','FWD'].map(p => (
            <button key={p} onClick={() => setFilterPos(filterPos === p ? '' : p)}
              className={`px-3 py-2 text-xs font-medium transition ${filterPos === p ? 'bg-ucl-accent text-ucl-dark' : 'bg-ucl-dark text-gray-400 hover:text-white'}`}>
              {p}
            </button>
          ))}
        </div>
        <span className="text-xs text-gray-500">{filtered.length} players</span>
      </div>

      {/* Sort buttons */}
      <div className="flex gap-2 text-xs">
        {[
          { key: 'expected_points', label: 'Exp. Pts' },
          { key: 'points_per_million', label: 'Pts/€M' },
          { key: 'price', label: 'Price' },
        ].map(s => (
          <button key={s.key} onClick={() => toggleSort(s.key)}
            className={`flex items-center gap-1 px-2 py-1 rounded transition ${
              sortBy === s.key ? 'bg-ucl-accent/20 text-ucl-accent' : 'text-gray-500 hover:text-gray-300'
            }`}>
            <ArrowUpDown size={10} />
            {s.label}
          </button>
        ))}
      </div>

      {/* Player List */}
      <div className="space-y-1.5">
        {filtered.map((p, i) => (
          <div key={p.player_id} className="bg-ucl-blue/20 border border-ucl-accent/10 rounded-xl overflow-hidden hover:border-ucl-accent/25 transition">
            <div
              className="flex items-center gap-2 px-3 py-2.5 cursor-pointer"
              onClick={() => setExpanded(expanded === i ? null : i)}
            >
              <span className="text-gray-600 w-5 text-right text-xs">{i + 1}</span>
              <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${posColors[p.position]}`}>{p.position}</span>
              <div className="flex-1 min-w-0">
                <span className={`font-medium text-sm ${p.fixture_played ? 'text-gray-400' : 'text-white'}`}>{p.name}</span>
                <span className="text-xs text-gray-500 ml-2">{p.club}</span>
                {p.fixture_played && <span className="ml-2 text-[9px] px-1.5 py-0.5 rounded bg-gray-700 text-gray-400">PLAYED</span>}
              </div>
              <span className="text-ucl-gold text-xs">€{p.price}M</span>
              <div className={`w-1.5 h-1.5 rounded-full ${riskDot[p.risk_level]}`}></div>
              {p.fixture_played ? (
                <div className="text-right w-20">
                  {p.actual_points != null ? (
                    <div>
                      <span className="text-base font-bold text-white">{p.actual_points}</span>
                      <span className="text-[10px] text-gray-500 block">pred: {p.expected_points}</span>
                    </div>
                  ) : (
                    <span className="text-base font-bold text-gray-500 line-through">{p.expected_points}</span>
                  )}
                </div>
              ) : (
                <>
                  <span className="text-base font-bold text-ucl-accent w-12 text-right">{p.expected_points}</span>
                  <span className="text-[10px] text-gray-500 w-10 text-right">{p.points_per_million}/M</span>
                </>
              )}
              {expanded === i ? <ChevronUp size={14} className="text-gray-500" /> : <ChevronDown size={14} className="text-gray-500" />}
            </div>
            {expanded === i && (
              <div className="px-3 pb-3 pt-1 border-t border-ucl-accent/10 text-xs space-y-2">
                <div className="flex gap-6">
                  <span>{t('confidence')}: <span className={`font-medium ${confColor[p.confidence]}`}>{t(p.confidence)}</span></span>
                  <span>{t('risk')}: <span className={`font-medium ${riskColor[p.risk_level]}`}>{t(p.risk_level)}</span></span>
                </div>
                <div className="text-gray-400">
                  <span className="font-medium text-gray-300">{t('reasoning')}:</span>
                  <ul className="list-disc list-inside mt-1 space-y-0.5">
                    {p.reasoning.map((r, j) => <li key={j}>{r}</li>)}
                  </ul>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {filtered.length === 0 && !error && (
        <div className="text-center py-16 text-gray-500">
          <p>No predictions available. Import data first.</p>
        </div>
      )}
    </div>
  )
}
