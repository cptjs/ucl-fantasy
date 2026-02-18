import React, { useEffect, useState } from 'react'
import { useLang } from '../App'
import { Users, Calendar, Swords, TrendingUp, Star } from 'lucide-react'
import ClubLogo from '../components/ClubLogo'

export default function Dashboard() {
  const { t } = useLang()
  const [data, setData] = useState(null)
  const [topPlayers, setTopPlayers] = useState([])
  const [fixtures, setFixtures] = useState([])

  useEffect(() => {
    fetch('/api/dashboard').then(r => r.json()).then(d => {
      setData(d)
      if (d.active_matchday) {
        fetch(`/api/fixtures?matchday_id=${d.active_matchday.id}`).then(r => r.json()).then(setFixtures)
      }
    }).catch(() => {})
    fetch('/api/predictions').then(r => r.json()).then(p => setTopPlayers(p.slice(0, 8))).catch(() => {})
  }, [])

  if (!data) return (
    <div className="text-center py-20 text-gray-500">
      <div className="text-5xl mb-4">⚽</div>
      <p className="text-lg">{t('noData')}</p>
      <p className="text-sm mt-2 text-gray-600">Go to Import Data to get started</p>
    </div>
  )

  const posColors = { GK: 'text-yellow-400', DEF: 'text-blue-400', MID: 'text-green-400', FWD: 'text-red-400' }

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: t('totalPlayers'), value: data.players, icon: Users, color: 'text-ucl-accent', bg: 'from-cyan-500/10 to-transparent' },
          { label: t('activeMatchday'), value: data.active_matchday?.name || '—', icon: Calendar, color: 'text-ucl-gold', bg: 'from-yellow-500/10 to-transparent', small: true },
          { label: t('fixtures'), value: data.fixtures, icon: Swords, color: 'text-ucl-green', bg: 'from-green-500/10 to-transparent' },
          { label: t('statsRecords'), value: data.total_stats_records, icon: TrendingUp, color: 'text-purple-400', bg: 'from-purple-500/10 to-transparent' },
        ].map((c, i) => (
          <div key={i} className={`bg-gradient-to-br ${c.bg} border border-ucl-accent/10 rounded-xl p-4 hover:border-ucl-accent/25 transition`}>
            <div className="flex items-center gap-2 mb-2">
              <c.icon size={16} className={c.color} />
              <span className="text-xs text-gray-400">{c.label}</span>
            </div>
            <div className={`${c.small ? 'text-lg' : 'text-2xl'} font-bold text-white`}>{c.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upcoming Fixtures */}
        {fixtures.length > 0 && (
          <div className="bg-ucl-blue/20 border border-ucl-accent/10 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-ucl-accent mb-4 flex items-center gap-2">
              <Swords size={16} /> Upcoming Fixtures
            </h3>
            <div className="space-y-2">
              {fixtures.map((f, i) => {
                const isPlayed = f.status === 'played'
                const isLive = f.status === 'live'
                const kickOff = f.kick_off || f.match_date
                let dateStr = ''
                if (kickOff) {
                  try {
                    const d = new Date(kickOff)
                    dateStr = d.toLocaleDateString('uk-UA', { day: '2-digit', month: '2-digit' }) + ' ' + d.toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' })
                  } catch { dateStr = kickOff }
                }
                return (
                  <div key={i} className={`flex items-center justify-between py-2 px-3 rounded-lg transition ${
                    isPlayed ? 'bg-gray-800/50 opacity-70' : isLive ? 'bg-green-900/30 border border-green-500/30' : 'bg-ucl-dark/30 hover:bg-ucl-dark/50'
                  }`}>
                    <div className="flex-1 text-right flex items-center justify-end gap-2">
                      <span className="text-sm font-medium text-white">{f.home_club}</span>
                      <ClubLogo club={f.home_club} size={20} />
                    </div>
                    <div className="px-3 text-center min-w-[80px]">
                      {isPlayed || isLive ? (
                        <div>
                          <span className="text-lg font-bold text-white">{f.home_score ?? '?'} - {f.away_score ?? '?'}</span>
                          {isLive && <span className="block text-[10px] text-green-400 font-bold animate-pulse">● LIVE</span>}
                          {isPlayed && <span className="block text-[10px] text-gray-500">FT</span>}
                        </div>
                      ) : (
                        <div>
                          <span className="text-xs text-gray-500 font-mono">vs</span>
                          {dateStr && <span className="block text-[10px] text-gray-500">{dateStr}</span>}
                        </div>
                      )}
                    </div>
                    <div className="flex-1 flex items-center gap-2">
                      <ClubLogo club={f.away_club} size={20} />
                      <span className="text-sm font-medium text-white">{f.away_club}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Top Predicted Players */}
        {topPlayers.length > 0 && (
          <div className="bg-ucl-blue/20 border border-ucl-accent/10 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-ucl-gold mb-4 flex items-center gap-2">
              <Star size={16} /> Top Predicted Players
            </h3>
            <div className="space-y-1.5">
              {topPlayers.map((p, i) => (
                <div key={p.player_id} className="flex items-center gap-3 py-1.5 px-2 rounded-lg hover:bg-ucl-dark/30 transition">
                  <span className="text-gray-500 text-xs w-4 text-right">{i + 1}</span>
                  <span className={`text-[10px] font-bold ${posColors[p.position]}`}>{p.position}</span>
                  <span className="text-sm text-white flex-1 truncate">{p.name}</span>
                  <span className="text-xs text-gray-400">{p.club}</span>
                  <span className="text-sm font-bold text-ucl-accent w-10 text-right">{p.expected_points}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
