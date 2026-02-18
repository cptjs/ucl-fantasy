import React, { useState } from 'react'
import { useLang } from '../App'
import { Shield, Star, Crown, ChevronDown } from 'lucide-react'
import ClubLogo from '../components/ClubLogo'

const posColors = {
  GK: 'from-yellow-500 to-yellow-600',
  DEF: 'from-blue-500 to-blue-600',
  MID: 'from-green-500 to-green-600',
  FWD: 'from-red-500 to-red-600',
}
const posBg = {
  GK: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  DEF: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  MID: 'bg-green-500/20 text-green-400 border-green-500/30',
  FWD: 'bg-red-500/20 text-red-400 border-red-500/30',
}

function PitchPlayer({ p, small }) {
  const isCap = p.is_captain
  return (
    <div className={`flex flex-col items-center group ${small ? 'w-16' : 'w-20'}`}>
      <div className={`relative w-12 h-12 rounded-full bg-gradient-to-b ${posColors[p.position]} flex items-center justify-center text-white font-bold text-xs shadow-lg ${
        isCap ? 'ring-2 ring-ucl-gold ring-offset-2 ring-offset-ucl-dark' : ''
      }`}>
        {isCap && <Crown size={12} className="absolute -top-2 -right-1 text-ucl-gold fill-ucl-gold" />}
        <span className="text-[10px]">{p.position}</span>
      </div>
      <div className="mt-1 text-center">
        <div className={`text-xs font-semibold text-white leading-tight ${small ? 'max-w-14' : 'max-w-18'} truncate`}>
          {p.name.split(' ').pop()}
        </div>
        <div className="text-[10px] text-ucl-accent font-bold">{p.expected_points.toFixed(1)}</div>
      </div>
    </div>
  )
}

function PitchView({ starting, formation, captain }) {
  const [def, mid, fwd] = formation.split('-').map(Number)
  
  const gks = starting.filter(p => p.position === 'GK')
  const defs = starting.filter(p => p.position === 'DEF')
  const mids = starting.filter(p => p.position === 'MID')
  const fwds = starting.filter(p => p.position === 'FWD')

  const Row = ({ players, label }) => (
    <div className="flex justify-center gap-3 sm:gap-6">
      {players.map(p => <PitchPlayer key={p.player_id} p={p} />)}
    </div>
  )

  return (
    <div className="relative rounded-2xl overflow-hidden" style={{ background: 'linear-gradient(180deg, #1a5e1a 0%, #228B22 30%, #1a7a1a 60%, #196619 100%)' }}>
      {/* Pitch markings */}
      <div className="absolute inset-0 opacity-20">
        <div className="absolute top-1/2 left-0 right-0 h-px bg-white"></div>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-24 h-24 border border-white rounded-full"></div>
        <div className="absolute top-0 left-1/4 right-1/4 h-16 border-b border-l border-r border-white"></div>
        <div className="absolute bottom-0 left-1/4 right-1/4 h-16 border-t border-l border-r border-white"></div>
      </div>

      <div className="relative py-6 px-4 space-y-6">
        {/* FWD */}
        <Row players={fwds} label="FWD" />
        {/* MID */}
        <Row players={mids} label="MID" />
        {/* DEF */}
        <Row players={defs} label="DEF" />
        {/* GK */}
        <Row players={gks} label="GK" />
      </div>
    </div>
  )
}

export default function SquadBuilder() {
  const { t } = useLang()
  const [budget, setBudget] = useState(100)
  const [maxClub, setMaxClub] = useState(3)
  const [profile, setProfile] = useState('balanced')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showBench, setShowBench] = useState(false)

  const build = async () => {
    setLoading(true); setError(''); setResult(null)
    try {
      const r = await fetch('/api/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ budget, max_per_club: maxClub, risk_profile: profile })
      })
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Error') }
      setResult(await r.json())
    } catch (e) { setError(e.message) }
    setLoading(false)
  }

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="bg-ucl-blue/20 border border-ucl-accent/10 rounded-xl p-5">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">{t('budget')}</label>
            <input type="number" value={budget} onChange={e => setBudget(+e.target.value)}
              className="w-full bg-ucl-dark border border-ucl-accent/20 rounded-lg px-3 py-2.5 text-sm focus:border-ucl-accent focus:outline-none transition" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">{t('maxPerClub')}</label>
            <input type="number" value={maxClub} onChange={e => setMaxClub(+e.target.value)}
              className="w-full bg-ucl-dark border border-ucl-accent/20 rounded-lg px-3 py-2.5 text-sm focus:border-ucl-accent focus:outline-none transition" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">{t('riskProfile')}</label>
            <div className="flex rounded-lg overflow-hidden border border-ucl-accent/20">
              {['safe','balanced','aggressive'].map(p => (
                <button key={p} onClick={() => setProfile(p)}
                  className={`flex-1 py-2.5 text-xs font-medium transition ${
                    profile === p ? 'bg-ucl-accent text-ucl-dark' : 'bg-ucl-dark text-gray-400 hover:text-white'
                  }`}>
                  {t(p)}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-end">
            <button onClick={build} disabled={loading}
              className="w-full bg-ucl-accent hover:bg-ucl-accent/80 text-ucl-dark font-bold py-2.5 px-4 rounded-lg transition disabled:opacity-50 text-sm">
              {loading ? '⏳ Building...' : `⚡ ${t('optimize')}`}
            </button>
          </div>
        </div>
      </div>

      {error && <p className="text-ucl-red text-sm text-center bg-ucl-red/10 rounded-xl py-3">{error}</p>}

      {result && (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-ucl-blue/30 border border-ucl-accent/20 rounded-xl px-4 py-3 text-center">
              <div className="text-xs text-gray-400">{t('formation')}</div>
              <div className="text-2xl font-bold text-white">{result.formation}</div>
            </div>
            <div className="bg-ucl-blue/30 border border-ucl-accent/20 rounded-xl px-4 py-3 text-center">
              <div className="text-xs text-gray-400">{t('totalExpected')}</div>
              <div className="text-2xl font-bold text-ucl-accent">{result.total_expected}</div>
            </div>
            <div className="bg-ucl-blue/30 border border-ucl-accent/20 rounded-xl px-4 py-3 text-center">
              <div className="text-xs text-gray-400">{t('totalCost')}</div>
              <div className="text-2xl font-bold text-ucl-gold">€{result.total_cost}M</div>
            </div>
          </div>

          {/* Captain Highlight */}
          <div className="bg-gradient-to-r from-ucl-gold/20 to-ucl-gold/5 border border-ucl-gold/30 rounded-xl p-4 flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-ucl-gold/20 flex items-center justify-center">
              <Crown size={24} className="text-ucl-gold" />
            </div>
            <div className="flex-1">
              <div className="text-xs text-ucl-gold/70">{t('captain')} (×2 points)</div>
              <div className="text-lg font-bold text-white">{result.captain.name}</div>
              <div className="text-xs text-gray-400 flex items-center gap-1"><ClubLogo club={result.captain.club} size={14} /> {result.captain.club} · {result.captain.position} · €{result.captain.price}M</div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-ucl-gold">{result.captain.expected_points.toFixed(1)}</div>
              <div className="text-xs text-gray-400">exp. pts</div>
            </div>
          </div>

          {/* Pitch View */}
          <div>
            <h3 className="text-sm font-semibold text-ucl-accent mb-3 flex items-center gap-2">
              <Shield size={16} /> {t('startingXI')}
            </h3>
            <PitchView starting={result.starting_xi} formation={result.formation} captain={result.captain} />
          </div>

          {/* Bench */}
          <div>
            <button onClick={() => setShowBench(!showBench)}
              className="flex items-center gap-2 text-sm font-semibold text-gray-400 hover:text-white transition mb-3">
              <ChevronDown size={16} className={`transition ${showBench ? 'rotate-180' : ''}`} />
              {t('bench')} ({result.bench.length})
            </button>
            {showBench && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {result.bench.map(p => (
                  <div key={p.player_id} className={`border rounded-xl p-3 flex items-center gap-3 opacity-60 ${posBg[p.position]}`}>
                    <span className="text-xs font-bold w-8">{p.position}</span>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-white text-sm truncate">{p.name}</div>
                      <div className="text-xs text-gray-400">{p.club} · €{p.price}M</div>
                    </div>
                    <div className="text-sm font-bold text-ucl-accent">{p.expected_points.toFixed(1)}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {!result && !loading && (
        <div className="text-center py-16 text-gray-500">
          <div className="text-4xl mb-3">⚽</div>
          <p>Configure your squad parameters and click <strong className="text-ucl-accent">Build Squad</strong></p>
        </div>
      )}
    </div>
  )
}
