import React, { useEffect, useState } from 'react'
import { useLang } from '../App'
import { Calendar, Flame, TrendingUp, TrendingDown, GitBranch, ChevronDown } from 'lucide-react'
import ClubLogo from '../components/ClubLogo'

const diffColors = {1:'bg-green-500',2:'bg-green-400',3:'bg-yellow-500',4:'bg-orange-500',5:'bg-red-500'}
const diffText = {1:'text-green-400',2:'text-green-300',3:'text-yellow-400',4:'text-orange-400',5:'text-red-400'}
const posBadge = {GK:'bg-yellow-500/20 text-yellow-400',DEF:'bg-blue-500/20 text-blue-400',MID:'bg-green-500/20 text-green-400',FWD:'bg-red-500/20 text-red-400'}

export default function FixtureCalendar() {
  const { t } = useLang()
  const [tab, setTab] = useState('calendar')
  const [calendar, setCalendar] = useState(null)
  const [hotPicks, setHotPicks] = useState(null)
  const [priceChanges, setPriceChanges] = useState(null)
  const [knockoutPath, setKnockoutPath] = useState(null)
  const [posFilter, setPosFilter] = useState('')
  const [playerForm, setPlayerForm] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch('/api/fixture-calendar').then(r => r.json()),
      fetch('/api/hot-picks').then(r => r.json()),
      fetch('/api/price-changes').then(r => r.json()),
      fetch('/api/knockout-path').then(r => r.json()),
    ]).then(([cal, picks, prices, ko]) => {
      setCalendar(cal)
      setHotPicks(picks)
      setPriceChanges(prices)
      setKnockoutPath(ko)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const loadPlayerForm = (pid) => {
    fetch(`/api/players/${pid}/form`).then(r => r.json()).then(setPlayerForm)
  }

  if (loading) return <div className="text-center py-20 text-gray-500">Loading...</div>

  const tabs = [
    { id: 'calendar', icon: Calendar, label: t('fixtureCalendar') || 'Calendar' },
    { id: 'hotpicks', icon: Flame, label: t('hotPicks') || 'Hot Picks' },
    { id: 'prices', icon: TrendingUp, label: 'Prices' },
    { id: 'knockout', icon: GitBranch, label: 'Knockout' },
  ]

  return (
    <div className="space-y-4">
      {/* Tabs */}
      <div className="flex gap-1.5 overflow-x-auto">
        {tabs.map(({ id, icon: Icon, label }) => (
          <button key={id} onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium transition whitespace-nowrap ${
              tab === id ? 'bg-ucl-accent text-ucl-dark' : 'bg-ucl-blue/30 text-gray-400 hover:text-white'
            }`}>
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      {/* ───── CALENDAR TAB ───── */}
      {tab === 'calendar' && calendar && (
        <div>
          <div className="flex items-center gap-3 text-xs text-gray-500 mb-3">
            <span>Difficulty:</span>
            {[1,2,3,4,5].map(d => (
              <span key={d} className="flex items-center gap-1">
                <span className={`w-2.5 h-2.5 rounded ${diffColors[d]}`}></span>{d}
              </span>
            ))}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-ucl-accent/10">
                  <th className="text-left py-2 px-3 text-gray-400 text-xs sticky left-0 bg-ucl-dark z-10 min-w-[130px]">Club</th>
                  {calendar.matchdays.map(md => (
                    <th key={md.id} className={`py-2 px-1 text-center text-[10px] min-w-[85px] ${md.is_active ? 'text-ucl-accent' : 'text-gray-600'}`}>
                      {md.name.replace('Knockout Play-offs','KO').replace('Round of 16','R16')}
                      {md.is_active && <span className="block text-ucl-accent text-[9px]">● now</span>}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {calendar.clubs.map(club => (
                  <tr key={club} className="border-b border-ucl-accent/5 hover:bg-ucl-blue/10">
                    <td className="py-1.5 px-3 sticky left-0 bg-ucl-dark z-10">
                      <div className="flex items-center gap-2">
                        <ClubLogo club={club} size={16} />
                        <span className="text-white text-xs truncate">{club}</span>
                      </div>
                    </td>
                    {calendar.matchdays.map(md => {
                      const fix = (calendar.calendar[club] || []).find(f => f.matchday_id === md.id)
                      if (!fix) return <td key={md.id} className="text-center text-gray-800 text-xs">—</td>
                      return (
                        <td key={md.id} className="py-1 px-1 text-center">
                          <div className={fix.status === 'played' ? 'opacity-50' : ''}>
                            <div className="flex items-center justify-center gap-1">
                              <span className={`w-2 h-2 rounded-sm ${diffColors[fix.difficulty]}`}></span>
                              <span className={`text-[10px] font-bold ${diffText[fix.difficulty]}`}>{fix.difficulty}</span>
                            </div>
                            <div className="text-[9px] text-gray-500">{fix.is_home?'H':'A'} {fix.opponent.length>9?fix.opponent.slice(0,7)+'..':fix.opponent}</div>
                            {fix.status === 'played' && fix.score && <div className="text-[9px] text-gray-600">{fix.score}</div>}
                          </div>
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ───── HOT PICKS TAB ───── */}
      {tab === 'hotpicks' && hotPicks && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500">Ranked by form × fixture ease</p>
            <div className="flex rounded-lg overflow-hidden border border-ucl-accent/20">
              <button onClick={() => setPosFilter('')} className={`px-2.5 py-1 text-xs ${!posFilter ? 'bg-ucl-accent text-ucl-dark' : 'bg-ucl-dark text-gray-400'}`}>All</button>
              {['GK','DEF','MID','FWD'].map(p => (
                <button key={p} onClick={() => setPosFilter(posFilter===p?'':p)}
                  className={`px-2.5 py-1 text-xs ${posFilter===p ? 'bg-ucl-accent text-ucl-dark' : 'bg-ucl-dark text-gray-400'}`}>{p}</button>
              ))}
            </div>
          </div>
          {hotPicks.picks.filter(p => !posFilter || p.position === posFilter).map((p, i) => (
            <div key={p.player_id} onClick={() => loadPlayerForm(p.player_id)}
              className={`flex items-center gap-2 px-3 py-2 rounded-xl cursor-pointer transition ${
                p.in_squad ? 'bg-ucl-accent/5 border border-ucl-accent/20' : 'bg-ucl-blue/10 hover:bg-ucl-blue/20'
              }`}>
              <span className="text-gray-600 text-xs w-4 text-right">{i+1}</span>
              <span className={`px-1 py-0.5 rounded text-[9px] font-bold ${posBadge[p.position]}`}>{p.position}</span>
              <ClubLogo club={p.club} size={18} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-sm text-white font-medium truncate">{p.name}</span>
                  {p.in_squad && <span className="text-[8px] px-1 rounded bg-ucl-accent/20 text-ucl-accent">squad</span>}
                </div>
                <div className="text-[10px] text-gray-500">{p.reason}</div>
              </div>
              <div className="text-right shrink-0">
                <div className="flex items-center gap-1">
                  <span className={`w-2 h-2 rounded-sm ${diffColors[p.fixture.difficulty]}`}></span>
                  <span className="text-[10px] text-gray-500">{p.fixture.is_home?'H':'A'} {p.fixture.opponent}</span>
                </div>
                <div className="text-xs text-gray-400">€{p.price}M · {p.avg_points}avg · <span className="text-ucl-gold font-bold">{p.hot_score}</span></div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ───── PLAYER FORM MODAL ───── */}
      {playerForm && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={() => setPlayerForm(null)}>
          <div className="bg-ucl-blue border border-ucl-accent/20 rounded-2xl max-w-md w-full p-5" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <ClubLogo club={playerForm.player.club} size={28} />
                <div>
                  <div className="text-white font-bold">{playerForm.player.name}</div>
                  <div className="text-xs text-gray-400">{playerForm.player.position} · €{playerForm.player.price}M · {playerForm.player.club}</div>
                </div>
              </div>
              <button onClick={() => setPlayerForm(null)} className="text-gray-400 hover:text-white">✕</button>
            </div>
            
            <div className="grid grid-cols-3 gap-3 mb-4">
              <div className="bg-ucl-dark/40 rounded-lg p-2 text-center">
                <div className="text-xs text-gray-500">Avg Pts</div>
                <div className="text-lg font-bold text-white">{playerForm.avg_points}</div>
              </div>
              <div className="bg-ucl-dark/40 rounded-lg p-2 text-center">
                <div className="text-xs text-gray-500">Form</div>
                <div className={`text-lg font-bold ${playerForm.form_trend === 'rising' ? 'text-ucl-green' : playerForm.form_trend === 'falling' ? 'text-ucl-red' : 'text-gray-400'}`}>
                  {playerForm.form_trend === 'rising' ? '📈' : playerForm.form_trend === 'falling' ? '📉' : '➡️'} {playerForm.form_trend}
                </div>
              </div>
              <div className="bg-ucl-dark/40 rounded-lg p-2 text-center">
                <div className="text-xs text-gray-500">Price</div>
                <div className={`text-lg font-bold ${playerForm.price_trend === 'rising' ? 'text-ucl-green' : playerForm.price_trend === 'falling' ? 'text-ucl-red' : 'text-gray-400'}`}>
                  {playerForm.price_trend === 'rising' ? '↑' : playerForm.price_trend === 'falling' ? '↓' : '='} €{playerForm.player.price}M
                </div>
              </div>
            </div>

            {playerForm.points_history.length > 0 && (
              <div>
                <div className="text-xs text-gray-500 mb-2">Points per matchday</div>
                <div className="flex items-end gap-1 h-24">
                  {playerForm.points_history.map((ph, i) => {
                    const maxPts = Math.max(...playerForm.points_history.map(p => p.matchday_points), 1)
                    const height = Math.max(8, (ph.matchday_points / maxPts) * 100)
                    return (
                      <div key={i} className="flex-1 flex flex-col items-center gap-0.5">
                        <span className="text-[9px] text-gray-400">{ph.matchday_points}</span>
                        <div className={`w-full rounded-t ${ph.matchday_points >= 8 ? 'bg-ucl-green' : ph.matchday_points >= 4 ? 'bg-ucl-accent' : 'bg-gray-600'}`}
                          style={{ height: `${height}%` }}></div>
                        <span className="text-[8px] text-gray-600 truncate w-full text-center">{ph.matchday_name.replace('Knockout Play-offs','KO').slice(0,6)}</span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
            {playerForm.points_history.length === 0 && (
              <div className="text-center text-gray-600 text-sm py-4">No matchday data yet</div>
            )}
          </div>
        </div>
      )}

      {/* ───── PRICE CHANGES TAB ───── */}
      {tab === 'prices' && priceChanges && (
        <div className="space-y-4">
          {priceChanges.message && <div className="text-sm text-gray-500 text-center py-4">{priceChanges.message}</div>}
          
          {priceChanges.risers?.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-ucl-green mb-2 flex items-center gap-1"><TrendingUp size={14} /> Price Risers</h3>
              <div className="space-y-1">
                {priceChanges.risers.map((p, i) => (
                  <div key={i} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-green-500/5 border border-green-500/10">
                    <span className={`px-1 py-0.5 rounded text-[9px] font-bold ${posBadge[p.position]}`}>{p.position}</span>
                    <span className="text-sm text-white flex-1">{p.name}</span>
                    <span className="text-xs text-gray-500">{p.club}</span>
                    <span className="text-xs text-gray-400">€{p.old_price}M</span>
                    <span className="text-xs text-ucl-green font-bold">→ €{p.new_price}M (+{p.price_diff.toFixed(1)})</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {priceChanges.fallers?.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-ucl-red mb-2 flex items-center gap-1"><TrendingDown size={14} /> Price Fallers</h3>
              <div className="space-y-1">
                {priceChanges.fallers.map((p, i) => (
                  <div key={i} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-500/5 border border-red-500/10">
                    <span className={`px-1 py-0.5 rounded text-[9px] font-bold ${posBadge[p.position]}`}>{p.position}</span>
                    <span className="text-sm text-white flex-1">{p.name}</span>
                    <span className="text-xs text-gray-500">{p.club}</span>
                    <span className="text-xs text-gray-400">€{p.old_price}M</span>
                    <span className="text-xs text-ucl-red font-bold">→ €{p.new_price}M ({p.price_diff.toFixed(1)})</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {!priceChanges.risers?.length && !priceChanges.fallers?.length && !priceChanges.message && (
            <div className="text-center text-gray-500 py-8">No price changes detected. Import UEFA JSON at least twice to track.</div>
          )}
        </div>
      )}

      {/* ───── KNOCKOUT PATH TAB ───── */}
      {tab === 'knockout' && knockoutPath && (
        <div className="space-y-4">
          {knockoutPath.rounds.map((round, ri) => (
            <div key={ri}>
              <h3 className={`text-sm font-semibold mb-2 ${round.matchday.is_active ? 'text-ucl-accent' : 'text-gray-400'}`}>
                {round.matchday.name} {round.matchday.is_active && '● active'}
              </h3>
              <div className="space-y-2">
                {round.ties.map((tie, ti) => {
                  const homeWinning = (tie.home_score ?? 0) > (tie.away_score ?? 0)
                  const awayWinning = (tie.away_score ?? 0) > (tie.home_score ?? 0)
                  return (
                    <div key={ti} className="bg-ucl-blue/20 border border-ucl-accent/10 rounded-xl p-3">
                      <div className="flex items-center gap-3">
                        {/* Home */}
                        <div className={`flex-1 flex items-center gap-2 ${homeWinning && tie.status === 'played' ? '' : 'opacity-80'}`}>
                          <ClubLogo club={tie.home_club} size={22} />
                          <div className="flex-1">
                            <div className="text-sm text-white font-medium">{tie.home_club}</div>
                            <div className="text-[10px] text-gray-500">
                              {Math.round(tie.home_advance_prob * 100)}% advance
                              {tie.home_squad_players > 0 && <span className="text-ucl-accent ml-1">({tie.home_squad_players} in squad)</span>}
                            </div>
                          </div>
                        </div>
                        
                        {/* Score */}
                        <div className="text-center min-w-[60px]">
                          {tie.status === 'played' ? (
                            <div className="text-lg font-bold text-white">{tie.home_score} - {tie.away_score}</div>
                          ) : (
                            <div className="text-xs text-gray-500">vs</div>
                          )}
                          <div className="text-[9px] text-gray-600">{tie.status === 'played' ? 'FT' : ''}</div>
                        </div>
                        
                        {/* Away */}
                        <div className={`flex-1 flex items-center gap-2 flex-row-reverse ${awayWinning && tie.status === 'played' ? '' : 'opacity-80'}`}>
                          <ClubLogo club={tie.away_club} size={22} />
                          <div className="flex-1 text-right">
                            <div className="text-sm text-white font-medium">{tie.away_club}</div>
                            <div className="text-[10px] text-gray-500">
                              {tie.away_squad_players > 0 && <span className="text-ucl-accent mr-1">({tie.away_squad_players} in squad)</span>}
                              {Math.round(tie.away_advance_prob * 100)}% advance
                            </div>
                          </div>
                        </div>
                      </div>
                      
                      {/* Advance bar */}
                      <div className="mt-2 flex h-1.5 rounded-full overflow-hidden bg-gray-800">
                        <div className="bg-ucl-accent/60 transition-all" style={{ width: `${tie.home_advance_prob * 100}%` }}></div>
                        <div className="bg-orange-500/60 transition-all" style={{ width: `${tie.away_advance_prob * 100}%` }}></div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
          {knockoutPath.rounds.length === 0 && (
            <div className="text-center text-gray-500 py-8">No knockout fixtures yet</div>
          )}
        </div>
      )}
    </div>
  )
}
