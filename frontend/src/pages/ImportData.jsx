import React, { useState, useEffect } from 'react'
import { useLang } from '../App'
import { Upload, Trash2, CheckCircle, AlertCircle, Info } from 'lucide-react'

export default function ImportData() {
  const { t } = useLang()
  const [msg, setMsg] = useState('')
  const [msgType, setMsgType] = useState('success')
  const [loading, setLoading] = useState(false)
  const [dashboard, setDashboard] = useState(null)

  useEffect(() => {
    fetch('/api/dashboard').then(r => r.json()).then(setDashboard).catch(() => {})
  }, [msg])

  const flash = (text, type = 'success') => { setMsg(text); setMsgType(type); setTimeout(() => setMsg(''), 5000) }

  const [adminKey, setAdminKey] = useState(() => localStorage.getItem('ucl-admin-key') || '')

  const saveAdminKey = (k) => { setAdminKey(k); localStorage.setItem('ucl-admin-key', k) }

  const uploadUefa = async (file) => {
    if (!adminKey) { flash('❌ Enter admin key first', 'error'); return }
    setLoading(true)
    const fd = new FormData(); fd.append('file', file)
    try {
      const r = await fetch('/api/players/import-uefa', { method: 'POST', body: fd, headers: { 'X-Admin-Key': adminKey } })
      const d = await r.json()
      if (r.ok) flash(`✅ Imported ${d.players} players, ${d.fixtures} fixtures`)
      else flash(`❌ ${d.detail || 'Error'}`, 'error')
    } catch { flash('❌ Upload failed', 'error') }
    setLoading(false)
  }

  const clearPlayers = async () => {
    if (!confirm('Delete all players and start fresh?')) return
    await fetch('/api/players', { method: 'DELETE', headers: { 'X-Admin-Key': adminKey } })
    flash('🗑️ All data cleared')
  }

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      {msg && (
        <div className={`flex items-center gap-2 text-sm px-4 py-3 rounded-xl ${
          msgType === 'success' ? 'bg-ucl-green/20 text-ucl-green border border-ucl-green/30' : 'bg-ucl-red/20 text-ucl-red border border-ucl-red/30'
        }`}>
          {msgType === 'success' ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
          {msg}
        </div>
      )}

      {/* Current Status */}
      {dashboard && (
        <div className="bg-ucl-blue/20 border border-ucl-accent/10 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-400 mb-3">📊 Current Data</h3>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-white">{dashboard.players}</div>
              <div className="text-xs text-gray-500">Players</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-ucl-gold">{dashboard.active_matchday?.name || '—'}</div>
              <div className="text-xs text-gray-500">Matchday</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-ucl-accent">{dashboard.fixtures}</div>
              <div className="text-xs text-gray-500">Fixtures</div>
            </div>
          </div>
        </div>
      )}

      {/* Admin Key */}
      <div className="bg-ucl-blue/20 border border-ucl-accent/10 rounded-xl p-4">
        <label className="text-xs text-gray-400 mb-2 block">🔑 Admin Key</label>
        <input type="password" value={adminKey} onChange={e => saveAdminKey(e.target.value)}
          placeholder="Enter admin key..."
          className="w-full bg-ucl-dark border border-ucl-accent/20 rounded-lg px-3 py-2 text-sm focus:border-ucl-accent focus:outline-none" />
      </div>

      {/* UEFA JSON Import */}
      <div className="bg-gradient-to-br from-ucl-blue/40 to-ucl-blue/20 border border-ucl-accent/20 rounded-xl p-6 space-y-4">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🏆</span>
          <h3 className="text-lg font-bold text-white">Import UEFA Fantasy Data</h3>
        </div>
        
        <div className="bg-ucl-dark/40 rounded-lg p-4 space-y-2">
          <div className="flex items-start gap-2">
            <Info size={16} className="text-ucl-accent mt-0.5 shrink-0" />
            <div className="text-sm text-gray-300">
              <p className="font-medium text-white mb-2">How to get the data file:</p>
              <ol className="list-decimal list-inside space-y-1 text-gray-400">
                <li>Go to <a href="https://gaming.uefa.com/en/uclfantasy" target="_blank" className="text-ucl-accent hover:underline">gaming.uefa.com/en/uclfantasy</a></li>
                <li>Open DevTools (<kbd className="px-1.5 py-0.5 bg-ucl-blue/50 rounded text-xs">F12</kbd>)</li>
                <li>Go to <strong className="text-gray-300">Network</strong> tab → filter <strong className="text-gray-300">XHR</strong></li>
                <li>Refresh the page (F5)</li>
                <li>Click on <code className="px-1.5 py-0.5 bg-ucl-blue/50 rounded text-xs text-ucl-accent">players_80_en_10.json</code> (131 KB)</li>
                <li>Tab <strong className="text-gray-300">Response</strong> → Right click → <strong className="text-gray-300">Copy response</strong></li>
                <li>Save as <code className="px-1.5 py-0.5 bg-ucl-blue/50 rounded text-xs">.json</code> file</li>
              </ol>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <label className={`flex items-center gap-2 px-5 py-3 rounded-xl font-bold cursor-pointer transition ${
            loading ? 'bg-gray-600 text-gray-400' : 'bg-ucl-accent hover:bg-ucl-accent/80 text-ucl-dark'
          }`}>
            <Upload size={18} />
            {loading ? 'Importing...' : 'Upload JSON'}
            <input type="file" accept=".json,.txt" className="hidden" disabled={loading}
              onChange={e => e.target.files[0] && uploadUefa(e.target.files[0])} />
          </label>
          
          <button onClick={clearPlayers}
            className="flex items-center gap-2 px-4 py-3 rounded-xl text-sm text-ucl-red/70 hover:text-ucl-red hover:bg-ucl-red/10 transition">
            <Trash2 size={16} />
            Clear All
          </button>
        </div>

        <p className="text-xs text-gray-500">
          This imports all players, prices, stats, current fixtures, and matchday automatically.
          No need to create matchdays or fixtures manually.
        </p>
      </div>
    </div>
  )
}
