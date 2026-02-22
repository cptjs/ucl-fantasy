import React, { useEffect, useState } from 'react'
import { useLang } from '../App'
import { Calendar, Flame, Star, ChevronDown } from 'lucide-react'
import ClubLogo from '../components/ClubLogo'

const diffColors = {
  1: 'bg-green-500', 2: 'bg-green-400', 3: 'bg-yellow-500', 4: 'bg-orange-500', 5: 'bg-red-500'
}
const diffText = {
  1: 'text-green-400', 2: 'text-green-300', 3: 'text-yellow-400', 4: 'text-orange-400', 5: 'text-red-400'
}

const posBadge = {
  GK: 'bg-yellow-500/20 text-yellow-400',
  DEF: 'bg-blue-500/20 text-blue-400',
  MID: 'bg-green-500/20 text-green-400',
  FWD: 'bg-red-500/20 text-red-400',
}

export default function FixtureCalendar() {
  const { t } = useLang()
  const [tab, setTab] = useState('calendar')
  const [calendar, setCalendar] = useState(null)
  const [hotPicks, setHotPicks] = useState(null)
  const [posFilter, setPosFilter] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch('/api/fixture-calendar').then(r => r.json()),
      fetch('/api/hot-picks').then(r => r.json()),
    ]).then(([cal, picks]) => {
      setCalendar(cal)
      setHotPicks(picks)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-center py-20 text-gray-500">Loading...</div>

  return (
    <div className="space-y-4">
      {/* Tabs */}
      <div className="flex gap-2">
        <button onClick={() => setTab('calendar')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition ${
            tab === 'calendar' ? 'bg-ucl-accent text-ucl-dark' : 'bg-ucl-blue/30 text-gray-400 hover:text-white'
          }`}>
          <Calendar size={16} /> {t('fixtureCalendar') || 'Fixture Calendar'}
        </button>
        <button onClick={() => setTab('hotpicks')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition ${
            tab === 'hotpicks' ? 'bg-ucl-accent text-ucl-dark' : 'bg-ucl-blue/30 text-gray-400 hover:text-white'
          }`}>
          <Flame size={16} /> {t('hotPicks') || 'Hot Picks'}
        </button>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-3 text-xs text-gray-400">
        <span>Difficulty:</span>
        {[1,2,3,4,5].map(d => (
          <span key={d} className="flex items-center gap-1">
            <span className={`w-3 h-3 rounded ${diffColors[d]}`}></span>
            {d}
          </span>
        ))}
        <span className="ml-2">1=easy 5=hard</span>
      </div>

      {tab === 'calendar' && calendar && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-ucl-accent/10">
                <th className="text-left py-2 px-3 text-gray-400 text-xs font-medium sticky left-0 bg-ucl-dark z-10 min-w-[140px]">Club</th>
                {calendar.matchdays.map(md => (
                  <th key={md.id} className={`py-2 px-2 text-center text-[10px] font-medium min-w-[90px] ${
                    md.is_active ? 'text-ucl-accent' : 'text-gray-500'
                  }`}>
                    {md.name.replace('Knockout Play-offs', 'KO').replace('Round of 16', 'R16').replace('Quarter-finals', 'QF').replace('Semi-finals', 'SF')}
                    {md.is_active && <span className="block text-ucl-accent">● active</span>}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {calendar.clubs.map(club => (
                <tr key={club} className="border-b border-ucl-accent/5 hover:bg-ucl-blue/10 transition">
                  <td className="py-2 px-3 sticky left-0 bg-ucl-dark z-10">
                    <div className="flex items-center gap-2">
                      <ClubLogo club={club} size={18} />
                      <span className="text-white text-xs font-medium truncate">{club}</span>
                    </div>
                  </td>
                  {calendar.matchdays.map(md => {
                    const fix = (calendar.calendar[club] || []).find(f => f.matchday_id === md.id)
                    if (!fix) return <td key={md.id} className="py-2 px-2 text-center text-gray-700 text-xs">—</td>
                    
                    const isPlayed = fix.status === 'played'
                    return (
                      <td key={md.id} className="py-1.5 px-1 text-center">
                        <div className={`rounded-lg px-1.5 py-1.5 ${isPlayed ? 'opacity-50' : ''}`}>
                          <div className="flex items-center justify-center gap-1 mb-0.5">
                            <span className={`w-2 h-2 rounded-sm ${diffColors[fix.difficulty]}`}></span>
                            <span className={`text-[10px] font-bold ${diffText[fix.difficulty]}`}>
                              {fix.difficulty}
                            </span>
                          </div>
                          <div className="text-[10px] text-gray-400">
                            {fix.is_home ? 'H' : 'A'} {fix.opponent.length > 10 ? fix.opponent.slice(0, 8) + '..' : fix.opponent}
                          </div>
                          {isPlayed && fix.score && (
                            <div className="text-[10px] text-gray-500">{fix.score}</div>
                          )}
                        </div>
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'hotpicks' && hotPicks && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500">
              Players ranked by form × fixture ease. Best transfer targets for {hotPicks.matchday?.name || 'next matchday'}.
            </p>
            <div className="flex rounded-lg overflow-hidden border border-ucl-accent/20">
              <button onClick={() => setPosFilter('')} className={`px-3 py-1.5 text-xs ${!posFilter ? 'bg-ucl-accent text-ucl-dark' : 'bg-ucl-dark text-gray-400'}`}>All</button>
              {['GK','DEF','MID','FWD'].map(p => (
                <button key={p} onClick={() => setPosFilter(posFilter === p ? '' : p)}
                  className={`px-3 py-1.5 text-xs ${posFilter === p ? 'bg-ucl-accent text-ucl-dark' : 'bg-ucl-dark text-gray-400'}`}>{p}</button>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            {hotPicks.picks
              .filter(p => !posFilter || p.position === posFilter)
              .map((p, i) => (
              <div key={p.player_id} className={`flex items-center gap-3 px-3 py-2.5 rounded-xl transition ${
                p.in_squad ? 'bg-ucl-accent/5 border border-ucl-accent/20' : 'bg-ucl-blue/10 hover:bg-ucl-blue/20'
              }`}>
                <span className="text-gray-600 text-xs w-5 text-right">{i + 1}</span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${posBadge[p.position]}`}>{p.position}</span>
                <ClubLogo club={p.club} size={20} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-white font-medium truncate">{p.name}</span>
                    {p.in_squad && <span className="text-[9px] px-1.5 rounded bg-ucl-accent/20 text-ucl-accent">In squad</span>}
                    {p.injury_status === 'doubt' && <span className="text-[9px] px-1.5 rounded bg-yellow-500/20 text-yellow-400">Doubt</span>}
                  </div>
                  <div className="text-[11px] text-gray-500 mt-0.5">{p.reason}</div>
                </div>
                <div className="text-right shrink-0">
                  <div className="flex items-center gap-1">
                    <span className={`w-2 h-2 rounded-sm ${diffColors[p.fixture.difficulty]}`}></span>
                    <span className="text-xs text-gray-400">
                      {p.fixture.is_home ? 'H' : 'A'} {p.fixture.opponent}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 justify-end mt-0.5">
                    <span className="text-xs text-gray-500">€{p.price}M</span>
                    <span className="text-xs text-gray-400">{p.avg_points} avg</span>
                    <span className="text-sm font-bold text-ucl-gold">{p.hot_score}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
