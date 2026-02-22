import React, { useState, useEffect, createContext, useContext } from 'react'
import { Trophy, Users, TrendingUp, Layers, Upload, Globe, UserCircle, BookOpen, Calendar } from 'lucide-react'
import translations from './locales/translations'
import Dashboard from './pages/Dashboard'
import Players from './pages/Players'
import Predictions from './pages/Predictions'
import SquadBuilder from './pages/SquadBuilder'
import ImportData from './pages/ImportData'
import MyTeam from './pages/MyTeam'
import Archive from './pages/Archive'
import FixtureCalendar from './pages/FixtureCalendar'

const LangContext = createContext()
export const useLang = () => useContext(LangContext)

const tabs = [
  { id: 'dashboard', icon: Trophy },
  { id: 'myTeam', icon: UserCircle },
  { id: 'players', icon: Users },
  { id: 'predictions', icon: TrendingUp },
  { id: 'fixtureCalendar', icon: Calendar },
  { id: 'squadBuilder', icon: Layers },
  { id: 'archive', icon: BookOpen },
  { id: 'importData', icon: Upload },
]

export default function App() {
  const [lang, setLang] = useState(() => localStorage.getItem('ucl-lang') || 'en')
  const [tab, setTab] = useState('dashboard')
  const t = (key) => translations[lang]?.[key] || key

  useEffect(() => { localStorage.setItem('ucl-lang', lang) }, [lang])

  const pages = {
    dashboard: <Dashboard />,
    myTeam: <MyTeam />,
    players: <Players />,
    predictions: <Predictions />,
    fixtureCalendar: <FixtureCalendar />,
    squadBuilder: <SquadBuilder />,
    archive: <Archive />,
    importData: <ImportData />,
  }

  return (
    <LangContext.Provider value={{ lang, setLang, t }}>
      <div className="min-h-screen flex flex-col">
        {/* Header */}
        <header className="bg-ucl-blue/80 backdrop-blur border-b border-ucl-accent/20 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-3xl">⚽</span>
            <h1 className="text-xl font-bold text-white">{t('title')}</h1>
          </div>
          <button
            onClick={() => setLang(lang === 'en' ? 'ua' : 'en')}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-ucl-dark/50 hover:bg-ucl-accent/20 transition text-sm"
          >
            <Globe size={16} />
            {lang === 'en' ? '🇺🇦 UA' : '🇬🇧 EN'}
          </button>
        </header>

        {/* Nav */}
        <nav className="bg-ucl-blue/40 border-b border-ucl-accent/10 px-4 flex gap-1 overflow-x-auto">
          {tabs.map(({ id, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition whitespace-nowrap border-b-2 ${
                tab === id
                  ? 'border-ucl-accent text-ucl-accent'
                  : 'border-transparent text-gray-400 hover:text-white hover:border-gray-500'
              }`}
            >
              <Icon size={16} />
              {t(id)}
            </button>
          ))}
        </nav>

        {/* Content */}
        <main className="flex-1 p-4 max-w-7xl mx-auto w-full">
          {pages[tab]}
        </main>

        {/* Footer */}
        <footer className="text-center text-xs text-gray-600 py-2 border-t border-ucl-accent/10">
          UCL Fantasy Assistant v1.0 — Not affiliated with UEFA
        </footer>
      </div>
    </LangContext.Provider>
  )
}
