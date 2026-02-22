import React, { useEffect, useState } from 'react'
import { useLang } from '../App'
import { Crown, ArrowLeftRight, Shield, AlertTriangle, ChevronDown, Zap, Search } from 'lucide-react'
import ClubLogo from '../components/ClubLogo'

const posColors = {
  GK: 'from-yellow-500 to-yellow-600',
  DEF: 'from-blue-500 to-blue-600',
  MID: 'from-green-500 to-green-600',
  FWD: 'from-red-500 to-red-600',
}
const posBadge = {
  GK: 'bg-yellow-500/20 text-yellow-400',
  DEF: 'bg-blue-500/20 text-blue-400',
  MID: 'bg-green-500/20 text-green-400',
  FWD: 'bg-red-500/20 text-red-400',
}

function PitchPlayer({ p, onSelect, selected }) {
  const isCap = p.is_captain
  return (
    <div 
      className={`flex flex-col items-center cursor-pointer group w-20 ${selected ? 'scale-110' : ''}`}
      onClick={() => onSelect?.(p)}
    >
      <div className={`relative w-12 h-12 rounded-full bg-gradient-to-b ${posColors[p.position]} flex items-center justify-center shadow-lg transition group-hover:scale-110 ${
        isCap ? 'ring-2 ring-ucl-gold ring-offset-2 ring-offset-ucl-dark' : ''
      } ${selected ? 'ring-2 ring-white' : ''}`}>
        {isCap && <Crown size={12} className="absolute -top-2 -right-1 text-ucl-gold fill-ucl-gold" />}
        <ClubLogo club={p.club} size={24} />
      </div>
      <div className="mt-1 text-center">
        <div className="text-xs font-semibold text-white leading-tight max-w-18 truncate">
          {p.name.split(' ').pop()}
        </div>
        <div className="text-xs text-gray-400">{p.avg_points || 0} avg</div>
      </div>
    </div>
  )
}

function TransferModal({ player, onClose, onTransfer }) {
  const [search, setSearch] = useState('')
  const [candidates, setCandidates] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!player) return
    setLoading(true)
    fetch(`/api/players?position=${player.position}`)
      .then(r => r.json())
      .then(data => {
        setCandidates(data.filter(p => p.id !== player.player_id))
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [player])

  if (!player) return null

  const filtered = candidates.filter(c => 
    !search || c.name.toLowerCase().includes(search.toLowerCase()) || c.club.toLowerCase().includes(search.toLowerCase())
  ).slice(0, 20)

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-ucl-blue border border-ucl-accent/20 rounded-2xl shadow-2xl shadow-black/50 max-w-lg w-full max-h-[80vh] overflow-hidden" onClick={e => e.stopPropagation()}>
        <div className="p-4 border-b border-ucl-accent/10">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-white font-bold">Replace {player.name}</h3>
            <button onClick={onClose} className="text-gray-400 hover:text-white">✕</button>
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-400 mb-3">
            <span className={`px-2 py-0.5 rounded text-xs font-bold ${posBadge[player.position]}`}>{player.position}</span>
            <span>€{player.price}M</span>
            <ArrowLeftRight size={14} />
            <span>Select replacement</span>
          </div>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search..."
              className="w-full bg-ucl-dark border border-ucl-accent/20 rounded-lg pl-9 pr-3 py-2 text-sm focus:border-ucl-accent focus:outline-none" />
          </div>
        </div>
        <div className="overflow-y-auto max-h-[50vh] p-2 space-y-1">
          {loading && <p className="text-center text-gray-500 py-4">Loading...</p>}
          {filtered.map(c => (
            <button key={c.id} onClick={() => onTransfer(player.player_id, c.id)}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-ucl-accent/10 transition text-left">
              <ClubLogo club={c.club} size={20} />
              <div className="flex-1 min-w-0">
                <div className="text-sm text-white font-medium truncate">{c.name}</div>
                <div className="text-xs text-gray-500">{c.club}</div>
              </div>
              <div className="text-right">
                <div className="text-sm font-bold text-ucl-gold">€{c.price}M</div>
                <div className="text-xs text-gray-500">{c.avg_points || 0} avg</div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function MyTeam() {
  const { t } = useLang()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [transferPlayer, setTransferPlayer] = useState(null)
  const [suggestions, setSuggestions] = useState([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [msg, setMsg] = useState('')
  const [boosters, setBoosters] = useState(null)
  
  // Build mode state — must be before any conditional returns (React hooks rule)
  const [buildMode, setBuildMode] = useState(false)
  const [buildSquad, setBuildSquad] = useState([])
  const [buildSearch, setBuildSearch] = useState('')
  const [buildPos, setBuildPos] = useState('')
  const [buildResults, setBuildResults] = useState([])
  const [buildCaptain, setBuildCaptain] = useState(null)

  const loadSquad = () => {
    fetch('/api/my-squad').then(r => r.json()).then(d => { setData(d); setLoading(false) }).catch(() => setLoading(false))
  }

  useEffect(() => { 
    loadSquad()
    fetch('/api/boosters').then(r => r.json()).then(setBoosters).catch(() => {})
  }, [])

  const doTransfer = async (outId, inId) => {
    const r = await fetch('/api/my-squad/transfer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ player_out_id: outId, player_in_id: inId })
    })
    const d = await r.json()
    if (r.ok) {
      setMsg(`✅ ${d.player_out} → ${d.player_in}${d.is_free ? '' : ' (-4 pts)'}`)
      setTransferPlayer(null)
      loadSquad()
    } else {
      setMsg(`❌ ${d.detail}`)
    }
    setTimeout(() => setMsg(''), 5000)
  }

  const setCaptain = async (pid) => {
    const starting = data.squad.filter(s => s.is_starting).map(s => s.player_id)
    await fetch('/api/my-squad/lineup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ starting_ids: starting, captain_id: pid })
    })
    loadSquad()
  }

  const loadSuggestions = () => {
    fetch('/api/my-squad/suggestions').then(r => r.json()).then(d => {
      setSuggestions(d)
      setShowSuggestions(true)
    })
  }

  const REQUIRED = { GK: 2, DEF: 5, MID: 5, FWD: 3 }

  const buildCounts = () => {
    const c = { GK: 0, DEF: 0, MID: 0, FWD: 0 }
    buildSquad.forEach(p => c[p.position]++)
    return c
  }

  const maxBudget = data?.budget || 105
  const maxPerClub = data?.max_per_club || 4
  const buildBudget = () => maxBudget - buildSquad.reduce((s, p) => s + p.price, 0)

  const searchPlayers = (query, pos) => {
    let url = '/api/players?'
    if (pos) url += `position=${pos}&`
    fetch(url).then(r => r.json()).then(players => {
      const ids = new Set(buildSquad.map(p => p.id || p.player_id))
      let filtered = players.filter(p => !ids.has(p.id))
      if (query) filtered = filtered.filter(p => 
        p.name.toLowerCase().includes(query.toLowerCase()) || p.club.toLowerCase().includes(query.toLowerCase())
      )
      setBuildResults(filtered.slice(0, 30))
    })
  }

  useEffect(() => {
    if (buildMode) searchPlayers(buildSearch, buildPos)
  }, [buildSearch, buildPos, buildSquad.length, buildMode])

  if (loading) return <div className="text-center py-20 text-gray-500">Loading...</div>

  const addToBuild = (player) => {
    const counts = buildCounts()
    if (counts[player.position] >= REQUIRED[player.position]) return
    if (buildSquad.length >= 15) return
    // No hard budget/club blocks — user is replicating their real team
    setBuildSquad([...buildSquad, { ...player, player_id: player.id }])
  }

  const removeFromBuild = (playerId) => {
    setBuildSquad(buildSquad.filter(p => (p.id || p.player_id) !== playerId))
    if (buildCaptain === playerId) setBuildCaptain(null)
  }

  const saveBuildSquad = async () => {
    if (buildSquad.length !== 15) { setMsg('❌ Need exactly 15 players'); return }
    if (!buildCaptain) { setMsg('❌ Select a captain'); return }
    
    // Auto-pick starting XI: best 11 (1GK, 3+DEF, 2+MID, 1+FWD)
    const byPos = { GK: [], DEF: [], MID: [], FWD: [] }
    buildSquad.forEach(p => byPos[p.position].push(p))
    
    const starting = []
    starting.push(byPos.GK[0])
    starting.push(...byPos.DEF.slice(0, 3))
    starting.push(...byPos.MID.slice(0, 2))
    starting.push(...byPos.FWD.slice(0, 1))
    // Fill remaining 4
    const remaining = buildSquad.filter(p => !starting.includes(p))
    remaining.sort((a, b) => (b.avg_points || 0) - (a.avg_points || 0))
    for (const p of remaining) {
      if (starting.length >= 11) break
      if (p.position === 'GK') continue
      starting.push(p)
    }

    const r = await fetch('/api/my-squad/set', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        player_ids: buildSquad.map(p => p.id || p.player_id),
        captain_id: buildCaptain,
        vice_captain_id: starting.find(p => (p.id || p.player_id) !== buildCaptain)?.id || starting.find(p => (p.id || p.player_id) !== buildCaptain)?.player_id,
        starting_ids: starting.map(p => p.id || p.player_id),
      })
    })
    if (r.ok) {
      setMsg('✅ Team saved!')
      setBuildMode(false)
      loadSquad()
    } else {
      const e = await r.json()
      setMsg(`❌ ${e.detail}`)
    }
    setTimeout(() => setMsg(''), 5000)
  }

  // ─── Build Mode UI ───
  if (buildMode) {
    const counts = buildCounts()
    return (
      <div className="space-y-4">
        {msg && <div className={`text-sm px-4 py-3 rounded-xl ${msg.startsWith('✅') ? 'bg-ucl-green/20 text-ucl-green' : 'bg-ucl-red/20 text-ucl-red'}`}>{msg}</div>}
        
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">🏗️ {t('buildTeam')}</h2>
          <button onClick={() => setBuildMode(false)} className="text-sm text-gray-400 hover:text-white">✕ Cancel</button>
        </div>

        {/* Progress */}
        <div className="grid grid-cols-6 gap-2">
          {Object.entries(REQUIRED).map(([pos, need]) => (
            <div key={pos} className={`rounded-lg px-3 py-2 text-center text-sm font-bold ${
              counts[pos] === need ? 'bg-ucl-green/20 text-ucl-green' : 'bg-ucl-blue/30 text-gray-400'
            }`}>
              {pos} {counts[pos]}/{need}
            </div>
          ))}
          <div className={`rounded-lg px-3 py-2 text-center text-sm font-bold ${
            buildSquad.length === 15 ? 'bg-ucl-green/20 text-ucl-green' : 'bg-ucl-blue/30 text-white'
          }`}>
            {buildSquad.length}/15
          </div>
          <div className={`rounded-lg px-3 py-2 text-center text-sm font-bold ${
            buildBudget() < 0 ? 'bg-ucl-red/20 text-ucl-red' : buildBudget() < 3 ? 'bg-yellow-500/20 text-yellow-400' : 'bg-ucl-gold/20 text-ucl-gold'
          }`}>
            €{buildBudget().toFixed(1)}M
            {buildBudget() < 0 && <div className="text-xs font-normal">over budget</div>}
          </div>
        </div>

        {/* Selected players */}
        {buildSquad.length > 0 && (
          <div className="space-y-1">
            {['GK','DEF','MID','FWD'].map(pos => {
              const players = buildSquad.filter(p => p.position === pos)
              if (!players.length) return null
              return (
                <div key={pos} className="flex flex-wrap gap-1">
                  {players.map(p => (
                    <div key={p.id || p.player_id} 
                      className={`flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs ${posBadge[pos]} border border-current/20 ${
                        buildCaptain === (p.id || p.player_id) ? 'ring-2 ring-ucl-gold' : ''
                      }`}>
                      <ClubLogo club={p.club} size={14} />
                      <span className="font-medium text-white">{p.name.split(' ').pop()}</span>
                      <span className="text-gray-500">€{p.price}M</span>
                      <button onClick={() => { 
                        const pid = p.id || p.player_id;
                        buildCaptain === pid ? setBuildCaptain(null) : setBuildCaptain(pid)
                      }} className={`text-xs px-1 rounded ${buildCaptain === (p.id || p.player_id) ? 'bg-ucl-gold text-black font-bold' : 'text-gray-500 hover:text-ucl-gold'}`}>
                        C
                      </button>
                      <button onClick={() => removeFromBuild(p.id || p.player_id)} className="text-gray-500 hover:text-ucl-red">✕</button>
                    </div>
                  ))}
                </div>
              )
            })}
          </div>
        )}

        {/* Search */}
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input value={buildSearch} onChange={e => setBuildSearch(e.target.value)} placeholder="Search player or club..."
              className="w-full bg-ucl-dark border border-ucl-accent/20 rounded-lg pl-9 pr-3 py-2 text-sm focus:border-ucl-accent focus:outline-none" />
          </div>
          <div className="flex rounded-lg overflow-hidden border border-ucl-accent/20">
            <button onClick={() => setBuildPos('')} className={`px-3 py-2 text-xs font-medium ${!buildPos ? 'bg-ucl-accent text-ucl-dark' : 'bg-ucl-dark text-gray-400'}`}>All</button>
            {['GK','DEF','MID','FWD'].map(p => (
              <button key={p} onClick={() => setBuildPos(buildPos === p ? '' : p)}
                className={`px-3 py-2 text-xs font-medium ${buildPos === p ? 'bg-ucl-accent text-ucl-dark' : 'bg-ucl-dark text-gray-400'}`}>{p}</button>
            ))}
          </div>
        </div>

        {/* Player list */}
        <div className="space-y-1 max-h-[40vh] overflow-y-auto">
          {buildResults.map(p => {
            const counts2 = buildCounts()
            const canAdd = buildSquad.length < 15 && counts2[p.position] < REQUIRED[p.position]
            return (
              <button key={p.id} onClick={() => canAdd && addToBuild(p)} disabled={!canAdd}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left transition ${canAdd ? 'hover:bg-ucl-accent/10' : 'opacity-30'}`}>
                <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${posBadge[p.position]}`}>{p.position}</span>
                <ClubLogo club={p.club} size={18} />
                <div className="flex-1 min-w-0">
                  <span className="text-sm text-white font-medium truncate block">{p.name}</span>
                  <span className="text-xs text-gray-500">{p.club}</span>
                </div>
                <span className="text-sm font-bold text-ucl-gold">€{p.price}M</span>
                <span className="text-xs text-gray-500">{p.avg_points || 0} avg</span>
                {buildSquad.filter(s => s.club === p.club).length >= maxPerClub && <span className="text-xs px-1 rounded bg-ucl-red/20 text-ucl-red">club limit</span>}
              </button>
            )
          })}
        </div>

        {/* Save */}
        <button onClick={saveBuildSquad} disabled={buildSquad.length !== 15 || !buildCaptain}
          className={`w-full font-bold py-3 rounded-xl transition border ${
            buildSquad.length === 15 && buildCaptain 
              ? 'bg-ucl-green/20 hover:bg-ucl-green/30 text-ucl-green border-ucl-green/30' 
              : 'bg-gray-800 text-gray-500 border-gray-700 cursor-not-allowed'
          }`}>
          {buildSquad.length !== 15 
            ? `${t('saveTeam')} (${buildSquad.length}/15 players)` 
            : !buildCaptain 
              ? `${t('saveTeam')} (select captain — tap C)` 
              : `✅ ${t('saveTeam')}`}
        </button>
      </div>
    )
  }

  if (!data || data.squad.length === 0) {
    return (
      <div className="text-center py-16 space-y-4">
        <div className="text-5xl">👤</div>
        <p className="text-gray-400 text-lg">{t('noSquad')}</p>
        <p className="text-gray-500 text-sm">{t('noSquadHint')}</p>
        <button onClick={() => setBuildMode(true)}
          className="mt-4 bg-ucl-accent hover:bg-ucl-accent/80 text-ucl-dark font-bold py-3 px-6 rounded-xl transition">
          🏗️ {t('buildTeam')}
        </button>
      </div>
    )
  }

  const starting = data.squad.filter(s => s.is_starting)
  const bench = data.squad.filter(s => !s.is_starting)
  const captain = data.squad.find(s => s.is_captain)

  // Group starting by position
  const gks = starting.filter(p => p.position === 'GK')
  const defs = starting.filter(p => p.position === 'DEF')
  const mids = starting.filter(p => p.position === 'MID')
  const fwds = starting.filter(p => p.position === 'FWD')
  const formation = `${defs.length}-${mids.length}-${fwds.length}`

  const Row = ({ players }) => (
    <div className="flex justify-center gap-3 sm:gap-6">
      {players.map(p => <PitchPlayer key={p.player_id} p={p} onSelect={setTransferPlayer} />)}
    </div>
  )

  return (
    <div className="space-y-6">
      {msg && (
        <div className={`text-sm px-4 py-3 rounded-xl ${msg.startsWith('✅') ? 'bg-ucl-green/20 text-ucl-green' : 'bg-ucl-red/20 text-ucl-red'}`}>
          {msg}
        </div>
      )}

      {/* Squad Info Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <div className="bg-ucl-blue/30 border border-ucl-accent/20 rounded-xl px-4 py-3 text-center">
          <div className="text-xs text-gray-400">{t('formation')}</div>
          <div className="text-xl font-bold text-white">{formation}</div>
        </div>
        <div className="bg-ucl-blue/30 border border-ucl-accent/20 rounded-xl px-4 py-3 text-center">
          <div className="text-xs text-gray-400">{t('totalCost')}</div>
          <div className="text-xl font-bold text-ucl-gold">€{data.total_value}M</div>
        </div>
        <div className="bg-ucl-blue/30 border border-ucl-accent/20 rounded-xl px-4 py-3 text-center">
          <div className="text-xs text-gray-400">{t('budgetLeft')}</div>
          <div className="text-xl font-bold text-ucl-green">€{data.budget_remaining}M</div>
        </div>
        <div className="bg-ucl-blue/30 border border-ucl-accent/20 rounded-xl px-4 py-3 text-center">
          <div className="text-xs text-gray-400">{t('transfers')}</div>
          <div className={`text-xl font-bold ${data.transfers_made >= 2 ? 'text-ucl-red' : 'text-white'}`}>
            {data.transfers_made}/2 {t('free')}
          </div>
        </div>
        <div className="bg-ucl-blue/30 border border-ucl-accent/20 rounded-xl px-4 py-3 text-center">
          <div className="text-xs text-gray-400">{t('penalty')}</div>
          <div className={`text-xl font-bold ${data.points_penalty > 0 ? 'text-ucl-red' : 'text-ucl-green'}`}>
            {data.points_penalty > 0 ? `-${data.points_penalty}` : '0'}
          </div>
        </div>
      </div>

      {/* Captain */}
      {captain && (
        <div className="bg-gradient-to-r from-ucl-gold/20 to-ucl-gold/5 border border-ucl-gold/30 rounded-xl p-4 flex items-center gap-4">
          <Crown size={24} className="text-ucl-gold" />
          <div className="flex-1">
            <div className="text-xs text-ucl-gold/70">{t('captain')} (×2)</div>
            <div className="text-lg font-bold text-white flex items-center gap-2">
              <ClubLogo club={captain.club} size={18} />
              {captain.name}
            </div>
          </div>
        </div>
      )}

      {/* Pitch */}
      <div className="relative rounded-2xl overflow-hidden shadow-xl shadow-green-900/30" style={{ background: 'linear-gradient(180deg, #1a5e1a 0%, #228B22 30%, #1a7a1a 60%, #196619 100%)' }}>
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-1/2 left-0 right-0 h-px bg-white"></div>
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-24 h-24 border border-white rounded-full"></div>
        </div>
        <div className="relative py-6 px-4 space-y-6">
          <Row players={fwds} />
          <Row players={mids} />
          <Row players={defs} />
          <Row players={gks} />
        </div>
        <div className="absolute bottom-2 left-0 right-0 text-center text-xs text-white/40 font-medium">
          Tap a player to make a transfer
        </div>
      </div>

      {/* Bench */}
      <div>
        <h3 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
          <Shield size={16} /> {t('bench')} ({bench.length})
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {bench.map(p => (
            <div key={p.player_id} 
              onClick={() => setTransferPlayer(p)}
              className={`border rounded-xl p-3 flex items-center gap-3 cursor-pointer hover:border-ucl-accent/30 transition ${posBadge[p.position]} border-current/20`}>
              <ClubLogo club={p.club} size={20} />
              <span className="text-xs font-bold w-8">{p.position}</span>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-white text-sm truncate">{p.name}</div>
                <div className="text-xs text-gray-400">€{p.price}M</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3 flex-wrap">
        <button onClick={() => { setBuildSquad(data.squad.map(s => ({...s, id: s.player_id}))); setBuildCaptain(captain?.player_id); setBuildMode(true) }}
          className="flex items-center gap-2 px-4 py-2.5 bg-ucl-blue/30 hover:bg-ucl-blue/50 text-white rounded-xl text-sm font-medium transition border border-ucl-accent/20">
          ✏️ {t('editTeam')}
        </button>
        <button onClick={loadSuggestions}
          className="flex items-center gap-2 px-4 py-2.5 bg-ucl-accent/20 hover:bg-ucl-accent/30 text-ucl-accent rounded-xl text-sm font-medium transition">
          <Zap size={16} /> {t('transferSuggestions')}
        </button>
        <button onClick={() => {
          fetch('/api/my-squad/suggestions-multi').then(r=>r.json()).then(d=>{setSuggestions(d);setShowSuggestions(true)})
        }}
          className="flex items-center gap-2 px-4 py-2.5 bg-purple-500/20 hover:bg-purple-500/30 text-purple-400 rounded-xl text-sm font-medium transition">
          <Zap size={16} /> Long-term
        </button>
      </div>

      {/* Boosters */}
      {boosters && (
        <div className="bg-ucl-blue/20 border border-ucl-accent/10 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-gray-400 mb-3">🚀 Boosters</h3>
          <div className="flex gap-3">
            {boosters.boosters?.map(b => {
              const isActive = boosters.active_booster === b.name
              const used = !b.is_available && !isActive
              return (
                <div key={b.name} className={`flex-1 rounded-xl p-3 border transition ${
                  isActive ? 'bg-purple-500/20 border-purple-500/40' :
                  used ? 'bg-gray-800/50 border-gray-700 opacity-50' :
                  'bg-ucl-dark/30 border-ucl-accent/10 hover:border-ucl-accent/30'
                }`}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-lg">{b.name === 'limitless' ? '♾️' : '🃏'}</span>
                    <span className="text-sm font-bold text-white capitalize">{b.name}</span>
                    {isActive && <span className="text-xs px-1.5 rounded bg-purple-500/30 text-purple-300">ACTIVE</span>}
                    {used && <span className="text-xs px-1.5 rounded bg-gray-600 text-gray-400">USED</span>}
                  </div>
                  <p className="text-xs text-gray-500 mb-2">
                    {b.name === 'limitless' ? 'Unlimited transfers for 1 matchday (squad reverts after)' : 'Full squad rebuild without penalty'}
                  </p>
                  {b.is_available && !isActive && (
                    <button onClick={async () => {
                      if (!confirm('Activate ' + b.name + '?')) return
                      const adminKey = localStorage.getItem('ucl-admin-key')
                      const r = await fetch('/api/boosters/activate', {
                        method: 'POST', headers: {'Content-Type':'application/json','X-Admin-Key':adminKey},
                        body: JSON.stringify({booster: b.name})
                      })
                      const d = await r.json()
                      if (r.ok) { setMsg('✅ ' + d.message); fetch('/api/boosters').then(r=>r.json()).then(setBoosters) }
                      else setMsg('❌ ' + (d.detail || 'Error'))
                      setTimeout(() => setMsg(''), 5000)
                    }} className="text-xs px-3 py-1 rounded-lg bg-purple-600/30 hover:bg-purple-600/50 text-purple-300 transition">
                      Activate
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Transfer Suggestions */}
      {showSuggestions && (
        <div className="bg-ucl-blue/20 border border-ucl-accent/10 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-ucl-accent flex items-center gap-2">
              <Zap size={16} /> {t('transferSuggestions')}
            </h3>
            <button onClick={() => setShowSuggestions(false)} className="text-gray-500 hover:text-white text-xs">✕</button>
          </div>
          
          {/* Summary bar */}
          {suggestions.summary && (
            <div className="text-xs text-gray-400 bg-ucl-dark/40 rounded-lg px-3 py-2">
              {suggestions.summary}
            </div>
          )}
          
          {/* Quick actions */}
          {suggestions.actions?.length > 0 && (
            <div className="space-y-1">
              <div className="text-xs text-gray-500 uppercase tracking-wide">Recommended actions</div>
              {suggestions.actions.map((a, i) => (
                <div key={i} className="text-sm text-white px-3 py-2 bg-ucl-dark/30 rounded-lg">{a}</div>
              ))}
            </div>
          )}
          
          {/* Detailed suggestions */}
          {suggestions.suggestions?.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs text-gray-500 uppercase tracking-wide">Details</div>
              {suggestions.suggestions.map((s, i) => (
                <div key={i} className={`py-3 px-3 rounded-lg transition ${
                  s.priority === 'high' ? 'bg-ucl-red/10 border border-ucl-red/20' : 
                  s.priority === 'medium' ? 'bg-yellow-500/10 border border-yellow-500/20' : 
                  'bg-ucl-dark/30 border border-ucl-accent/10'
                }`}>
                  <div className="flex items-center gap-3">
                    <div className="flex-1 flex items-center gap-2">
                      <span className="text-ucl-red text-xs font-bold">OUT</span>
                      <ClubLogo club={s.player_out.club} size={16} />
                      <span className="text-sm text-gray-400">{s.player_out.name}</span>
                      <span className="text-xs text-gray-600">€{s.player_out.price}M</span>
                    </div>
                    <ArrowLeftRight size={14} className="text-gray-500 shrink-0" />
                    <div className="flex-1 flex items-center gap-2">
                      <span className="text-ucl-green text-xs font-bold">IN</span>
                      <ClubLogo club={s.player_in.club} size={16} />
                      <span className="text-sm text-white font-medium">{s.player_in.name}</span>
                      <span className="text-xs text-gray-600">€{s.player_in.price}M</span>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-sm font-bold text-ucl-green">+{s.points_gain}</div>
                    </div>
                    <button onClick={() => doTransfer(s.player_out.player_id, s.player_in.player_id)}
                      className="px-3 py-1.5 bg-ucl-accent/20 hover:bg-ucl-accent/30 text-ucl-accent rounded-lg text-xs font-medium transition shrink-0">
                      Do it
                    </button>
                  </div>
                  {s.reason && <div className="text-xs text-gray-500 mt-1.5">{s.reason}</div>}
                  {s.warning && <div className="text-xs text-yellow-400 mt-1">⚠️ {s.warning}</div>}
                </div>
              ))}
            </div>
          )}
          
          {(!suggestions.suggestions || suggestions.suggestions.length === 0) && (
            <div className="text-center text-gray-500 text-sm py-4">Your squad looks good! No significant upgrades found.</div>
          )}
        </div>
      )}

      {/* Transfer Modal */}
      <TransferModal 
        player={transferPlayer} 
        onClose={() => setTransferPlayer(null)}
        onTransfer={doTransfer}
      />
    </div>
  )
}
