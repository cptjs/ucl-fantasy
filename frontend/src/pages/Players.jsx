import React, { useEffect, useState } from 'react'
import { useLang } from '../App'

export default function Players() {
  const { t } = useLang()
  const [players, setPlayers] = useState([])
  const [filterPos, setFilterPos] = useState('')
  const [filterClub, setFilterClub] = useState('')
  const [clubs, setClubs] = useState([])

  const load = () => {
    const params = new URLSearchParams()
    if (filterPos) params.set('position', filterPos)
    if (filterClub) params.set('club', filterClub)
    fetch(`/api/players?${params}`).then(r => r.json()).then(setPlayers).catch(() => {})
    fetch('/api/clubs').then(r => r.json()).then(setClubs).catch(() => {})
  }

  useEffect(load, [filterPos, filterClub])

  const posColors = { GK: 'bg-yellow-500/20 text-yellow-400', DEF: 'bg-blue-500/20 text-blue-400', MID: 'bg-green-500/20 text-green-400', FWD: 'bg-red-500/20 text-red-400' }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <select value={filterPos} onChange={e => setFilterPos(e.target.value)}
          className="bg-ucl-dark border border-ucl-accent/20 rounded-lg px-3 py-2 text-sm">
          <option value="">{t('position')}: All</option>
          {['GK','DEF','MID','FWD'].map(p => <option key={p} value={p}>{p}</option>)}
        </select>
        <select value={filterClub} onChange={e => setFilterClub(e.target.value)}
          className="bg-ucl-dark border border-ucl-accent/20 rounded-lg px-3 py-2 text-sm">
          <option value="">{t('club')}: All</option>
          {clubs.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <span className="text-sm text-gray-500 self-center">{players.length} players</span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-400 border-b border-ucl-accent/10">
              <th className="py-2 px-3">{t('name')}</th>
              <th className="py-2 px-3">{t('position')}</th>
              <th className="py-2 px-3">{t('club')}</th>
              <th className="py-2 px-3">{t('price')}</th>
              <th className="py-2 px-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {players.map(p => (
              <tr key={p.id} className="border-b border-ucl-accent/5 hover:bg-ucl-blue/20 transition">
                <td className="py-2 px-3 font-medium text-white">{p.name}</td>
                <td className="py-2 px-3">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${posColors[p.position]}`}>{p.position}</span>
                </td>
                <td className="py-2 px-3">{p.club}</td>
                <td className="py-2 px-3 text-ucl-gold">€{p.price}M</td>
                <td className="py-2 px-3">
                  {p.injury_status === 'fit' ? '✅' : p.injury_status === 'doubt' ? '⚠️' : '❌'}
                  {p.is_set_piece_taker ? ' 🎯' : ''}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {players.length === 0 && <p className="text-center text-gray-500 py-8">{t('noData')}</p>}
    </div>
  )
}
