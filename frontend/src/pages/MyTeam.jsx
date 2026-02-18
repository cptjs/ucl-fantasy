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
        <div className="text-[10px] text-gray-400">{p.avg_points || 0} avg</div>
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
      <div className="bg-ucl-blue border border-ucl-accent/20 rounded-2xl max-w-lg w-full max-h-[80vh] overflow-hidden" onClick={e => e.stopPropagation()}>
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
                <div className="text-[10px] text-gray-500">{c.avg_points || 0} avg</div>
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

  const loadSquad = () => {
    fetch('/api/my-squad').then(r => r.json()).then(d => { setData(d); setLoading(false) }).catch(() => setLoading(false))
  }

  useEffect(() => { loadSquad() }, [])

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
      setSuggestions(d.suggestions || [])
      setShowSuggestions(true)
    })
  }

  if (loading) return <div className="text-center py-20 text-gray-500">Loading...</div>

  if (!data || data.squad.length === 0) {
    return (
      <div className="text-center py-16 space-y-4">
        <div className="text-5xl">👤</div>
        <p className="text-gray-400 text-lg">{t('noSquad')}</p>
        <p className="text-gray-500 text-sm">{t('noSquadHint')}</p>
        <p className="text-gray-600 text-xs mt-4">
          Use Squad Builder to find your optimal squad, then set it via API:<br/>
          <code className="bg-ucl-dark px-2 py-1 rounded text-ucl-accent">POST /api/my-squad/set</code>
        </p>
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
      <div className="relative rounded-2xl overflow-hidden" style={{ background: 'linear-gradient(180deg, #1a5e1a 0%, #228B22 30%, #1a7a1a 60%, #196619 100%)' }}>
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
        <div className="absolute bottom-2 left-0 right-0 text-center text-[10px] text-white/30">
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
      <div className="flex gap-3">
        <button onClick={loadSuggestions}
          className="flex items-center gap-2 px-4 py-2.5 bg-ucl-accent/20 hover:bg-ucl-accent/30 text-ucl-accent rounded-xl text-sm font-medium transition">
          <Zap size={16} /> {t('transferSuggestions')}
        </button>
      </div>

      {/* Transfer Suggestions */}
      {showSuggestions && suggestions.length > 0 && (
        <div className="bg-ucl-blue/20 border border-ucl-accent/10 rounded-xl p-5 space-y-3">
          <h3 className="text-sm font-semibold text-ucl-accent flex items-center gap-2">
            <Zap size={16} /> {t('transferSuggestions')}
          </h3>
          {suggestions.map((s, i) => (
            <div key={i} className="flex items-center gap-3 py-2 px-3 rounded-lg bg-ucl-dark/30 hover:bg-ucl-dark/50 transition">
              <div className="flex-1 flex items-center gap-2">
                <span className="text-ucl-red text-sm">OUT</span>
                <ClubLogo club={s.player_out.club} size={16} />
                <span className="text-sm text-gray-400">{s.player_out.name}</span>
              </div>
              <ArrowLeftRight size={14} className="text-gray-500" />
              <div className="flex-1 flex items-center gap-2">
                <span className="text-ucl-green text-sm">IN</span>
                <ClubLogo club={s.player_in.club} size={16} />
                <span className="text-sm text-white font-medium">{s.player_in.name}</span>
              </div>
              <div className="text-right">
                <div className="text-sm font-bold text-ucl-green">+{s.points_gain} pts</div>
                <div className="text-[10px] text-gray-500">{s.cost_diff > 0 ? '+' : ''}{s.cost_diff}€M</div>
              </div>
              <button onClick={() => doTransfer(s.player_out.player_id, s.player_in.player_id)}
                className="px-3 py-1 bg-ucl-accent/20 hover:bg-ucl-accent/30 text-ucl-accent rounded-lg text-xs font-medium transition">
                Transfer
              </button>
            </div>
          ))}
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
