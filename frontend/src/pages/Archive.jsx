import React, { useEffect, useState } from 'react'
import { useLang } from '../App'
import { Trophy, ChevronDown, ChevronUp, Swords, Star } from 'lucide-react'
import ClubLogo from '../components/ClubLogo'

const posColors = { GK: 'text-yellow-400', DEF: 'text-blue-400', MID: 'text-green-400', FWD: 'text-red-400' }

export default function Archive() {
  const { t } = useLang()
  const [archive, setArchive] = useState([])
  const [expanded, setExpanded] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/archive').then(r => r.json()).then(d => {
      setArchive(d)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-center py-20 text-gray-500">Loading...</div>
  if (!archive.length) return (
    <div className="text-center py-20 text-gray-500">
      <div className="text-5xl mb-4">📋</div>
      <p className="text-lg">{t('noArchiveData') || 'No matchday data yet'}</p>
    </div>
  )

  const toggle = (id) => setExpanded(expanded === id ? null : id)

  return (
    <div className="space-y-4 max-w-3xl mx-auto">
      <h2 className="text-lg font-bold text-white flex items-center gap-2">
        <Trophy size={20} className="text-ucl-gold" />
        {t('archive') || 'Matchday Archive'}
      </h2>

      {archive.map((md) => {
        const isOpen = expanded === md.id
        const played = md.fixtures.filter(f => f.status === 'played').length
        const total = md.fixtures.length
        const hasPoints = md.my_points !== null && md.my_points !== undefined
        const netPoints = hasPoints ? md.my_points - (md.penalty_points || 0) : null

        return (
          <div key={md.id} className="bg-ucl-blue/20 border border-ucl-accent/10 rounded-xl overflow-hidden">
            <button
              onClick={() => toggle(md.id)}
              className="w-full flex items-center justify-between px-5 py-4 hover:bg-ucl-blue/30 transition"
            >
              <div className="flex items-center gap-3">
                {md.is_active ? (
                  <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                ) : (
                  <span className="w-2 h-2 rounded-full bg-gray-600" />
                )}
                <div className="text-left">
                  <div className="font-bold text-white">{md.name}</div>
                  <div className="text-xs text-gray-500">{md.stage.replace(/_/g, ' ')}</div>
                </div>
              </div>
              <div className="flex items-center gap-4">
                {hasPoints && (
                  <div className="text-right">
                    <div className="text-lg font-bold text-ucl-accent">{netPoints} pts</div>
                    {md.penalty_points > 0 && (
                      <div className="text-[10px] text-ucl-red">-{md.penalty_points} penalty</div>
                    )}
                  </div>
                )}
                <div className="text-xs text-gray-500">{played}/{total} played</div>
                {isOpen ? <ChevronUp size={18} className="text-gray-500" /> : <ChevronDown size={18} className="text-gray-500" />}
              </div>
            </button>

            {isOpen && (
              <div className="border-t border-ucl-accent/10 px-5 py-4 space-y-4">
                {md.fixtures.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-gray-400 mb-2 flex items-center gap-1">
                      <Swords size={14} /> {t('fixtures') || 'Fixtures'}
                    </h4>
                    <div className="space-y-1.5">
                      {md.fixtures.map((f, i) => {
                        const isPlayed = f.status === 'played'
                        const kickOff = f.kick_off || f.match_date
                        let dateStr = ''
                        if (kickOff) {
                          try {
                            const d = new Date(kickOff)
                            dateStr = d.toLocaleDateString('uk-UA', { day: '2-digit', month: '2-digit' }) +
                              ' ' + d.toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' })
                          } catch { dateStr = kickOff }
                        }
                        return (
                          <div key={i} className={`flex items-center justify-between py-2 px-3 rounded-lg ${
                            isPlayed ? 'bg-gray-800/40' : 'bg-ucl-dark/20'
                          }`}>
                            <div className="flex-1 text-right flex items-center justify-end gap-2">
                              <span className="text-sm text-white">{f.home_club}</span>
                              <ClubLogo club={f.home_club} size={18} />
                            </div>
                            <div className="px-3 text-center min-w-[70px]">
                              {isPlayed ? (
                                <span className="text-sm font-bold text-white">{f.home_score} - {f.away_score}</span>
                              ) : (
                                <span className="text-xs text-gray-500">{dateStr || 'vs'}</span>
                              )}
                            </div>
                            <div className="flex-1 flex items-center gap-2">
                              <ClubLogo club={f.away_club} size={18} />
                              <span className="text-sm text-white">{f.away_club}</span>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}

                {md.top_performers.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-ucl-gold mb-2 flex items-center gap-1">
                      <Star size={14} /> Top Performers
                    </h4>
                    <div className="space-y-1">
                      {md.top_performers.map((p, i) => (
                        <div key={i} className="flex items-center gap-2 py-1 px-2 rounded hover:bg-ucl-dark/30 transition">
                          <span className="text-gray-600 text-xs w-4 text-right">{i + 1}</span>
                          <span className={`text-[10px] font-bold ${posColors[p.position]}`}>{p.position}</span>
                          <span className="text-sm text-white flex-1 truncate">{p.name}</span>
                          <span className="text-xs text-gray-500">{p.club}</span>
                          <span className="text-sm font-bold text-ucl-accent w-10 text-right">{p.matchday_points}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
