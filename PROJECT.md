# UCL Fantasy Football Assistant — Project Guide

## Що це
AI-асистент для UEFA Champions League Fantasy Football. Прогнозує оптимальний склад, відстежує команду, трансфери, бустери.
Веб-додаток: FastAPI бекенд + React фронтенд.
**Мова інтерфейсу:** UA / EN (перемикач у хедері)

---

## Інфраструктура

| Що | Де |
|---|---|
| **GitHub** | https://github.com/cptjs/ucl-fantasy (гілка `main`) |
| **Дроплет** | `134.122.70.107` (DigitalOcean, Ubuntu 24.04, FRA1, $6/mo) |
| **SSH** | `ssh root@134.122.70.107` (ключ, без пароля) |
| **Порт** | 80 (проксі → 8000 всередині контейнера) |
| **Docker** | `docker-compose.yml`, один сервіс `ucl-fantasy` |
| **Volume** | `fantasy-data` → `/app/data/` (SQLite DB + імпортовані файли) |
| **Admin key** | `ucl-admin-2026` (env `ADMIN_KEY` в docker-compose) |
| **Cron** | `30 23 * * 2,3` — auto-fetch результатів (вівторок/середа 23:30 UTC) |

### Деплой
```bash
# З дроплета:
cd /root/ucl-fantasy
git fetch origin && git reset --hard origin/main
docker compose build --no-cache && docker compose up -d
```

### GitHub push (з sandbox OpenClaw)
```bash
cd /workspace/ucl-fantasy
git add -A && git commit -m "опис змін"
git push origin main
```

---

## Стек

### Backend (`backend/`) — 3617 LOC
| Файл | LOC | Що робить |
|---|---|---|
| `main.py` | 1982 | FastAPI — всі ендпоінти |
| `database.py` | 190 | SQLite init + `db_session()`, price_history table |
| `rules.py` | 145 | Правила по стадіях (бюджет, ліміт клубів, трансфери) |
| `scoring.py` | 101 | Scoring engine — повні правила UCL Fantasy |
| `predictor.py` | 229 | Predictor v3: avg × fixture × upside × minutes |
| `optimizer.py` | 177 | ILP optimizer (PuLP): 3 risk profiles |
| `import_uefa.py` | 332 | Парсер UEFA JSON + snapshots + price history |
| `fetch_results.py` | 123 | Auto-fetch результатів (football-data.org) |
| `difficulty.py` | 78 | Fixture difficulty ratings (1-5 зірок) |
| `update_leg1_to_leg2.py` | 260 | Міграція між легами |

### Frontend (`frontend/src/`) — 2389 LOC
| Файл | LOC | Що робить |
|---|---|---|
| `App.jsx` | 96 | Роутінг, навігація, мова UA/EN, кастомне лого |
| `pages/MyTeam.jsx` | 641 | Pitch view, Build mode, Smart Suggestions, Long-term, Boosters |
| `pages/FixtureCalendar.jsx` | 333 | Calendar + Hot Picks + Prices + Knockout Path (4 таби) |
| `pages/SquadBuilder.jsx` | 243 | AI оптимізатор — 3 risk profiles |
| `pages/ImportData.jsx` | 205 | Matchday Wizard, UEFA import, Fetch Results |
| `pages/Predictions.jsx` | 195 | Прогнози + факт. очки, таби по турах |
| `pages/Archive.jsx` | 146 | Архів: фікстури, рахунки, топ-перформери |
| `pages/Compare.jsx` | 139 | Порівняння гравців: bar chart по турах |
| `pages/Dashboard.jsx` | 135 | Загальна інфо, фікстури, топ гравці |
| `pages/Players.jsx` | 74 | Таблиця гравців з пошуком/фільтром |
| `locales/translations.js` | 182 | UA/EN переклади |

### Branding
- **Logo**: `frontend/public/logo.png` (blue football with analytics graph)
- **Favicon**: `frontend/public/favicon.png`

---

## База даних (SQLite)

| Таблиця | Опис |
|---|---|
| `players` | Гравці: ім'я, клуб, позиція, ціна, очки, форма, stats, uefa_id |
| `matchdays` | Тури: назва, stage, is_active, deadline |
| `fixtures` | Матчі: команди, рахунок, kick_off, status |
| `match_stats` | Статистика гравців по турах |
| `player_snapshots` | Snapshot очок (total_before/after/matchday_points) |
| `price_history` | Історія цін гравців по турах |
| `my_squad` | Моя команда: 15 гравців, капітан, стартовий/запасний |
| `transfers` | Історія трансферів (is_free) |
| `boosters` | Limitless, Wildcard — статус, used_matchday_id |
| `settings` | Key-value (limitless_backup etc) |
| `squads` | Збережені оптимізовані склади |

---

## Predictor v3

**Формула:** `base × fixture_mod × upside × minutes_prob`

- **Base**: `avg_points * 0.8 + price_signal * 0.2`
- **Fixture modifier**: weak (0.3) = x1.55, strong (0.9) = x0.60
- **Upside**: x1.35 + price bonus (65th percentile)
- **Set pieces**: +1.2-1.6 pts
- **Minutes prob**: 0.95 (nailed starter) → 0 (injured)
- **Result range**: 1-18 pts

---

## API ендпоінти

### Public
| Method | Path | Опис |
|---|---|---|
| GET | `/api/players` | Список гравців (фільтри: position, club) |
| GET | `/api/players/{id}/form` | **Form trend**: points history + bar chart data |
| GET | `/api/players/compare?ids=1,2,3` | **Compare**: points by matchday for 1-6 players |
| GET | `/api/players/search-for-compare?q=` | Пошук для compare tool |
| GET | `/api/matchdays` | Тури |
| GET | `/api/fixtures?matchday_id=` | Матчі туру |
| GET | `/api/predictions` | Прогнози (з actual якщо є) |
| GET | `/api/dashboard` | Зведена інфо |
| GET | `/api/clubs` | Список клубів |
| GET | `/api/rules` | Правила поточної стадії |
| GET | `/api/archive` | Всі тури: фікстури, рахунки, top performers |
| GET | `/api/fixture-calendar` | **Fixture calendar**: clubs × matchdays grid |
| GET | `/api/hot-picks` | **Hot picks**: form × fixture ease ranking |
| GET | `/api/price-changes` | **Price risers/fallers** between imports |
| GET | `/api/knockout-path` | **Knockout bracket** with advance probabilities |
| GET | `/api/boosters` | Booster status |
| GET | `/api/my-squad` | Моя команда + бюджет + трансфери |
| GET | `/api/my-squad/suggestions` | **Smart suggestions**: priority + reasoning |
| GET | `/api/my-squad/suggestions-multi` | **Long-term suggestions**: 2-3 matchdays + club strength |
| POST | `/api/optimize` | Запуск ILP оптимізатора |
| POST | `/api/my-squad/set` | Зберегти команду |
| POST | `/api/my-squad/transfer` | Зробити трансфер |
| POST | `/api/my-squad/lineup` | Змінити lineup/капітан |
| POST | `/api/fetch-results` | Fetch результатів (football-data.org) |
| POST | `/api/boosters/activate` | **Activate booster** (admin) |
| POST | `/api/boosters/rollback-limitless` | **Rollback Limitless** (admin) |

### Admin (потрібен `X-Admin-Key`)
| Method | Path | Опис |
|---|---|---|
| POST | `/api/players/import-uefa` | Імпорт UEFA JSON |
| POST | `/api/players/import-csv` | Імпорт CSV |
| DELETE | `/api/players` | Видалити всіх |
| POST | `/api/matchdays` | Створити тур |
| POST | `/api/matchdays/wizard?stage=` | **Wizard**: тур + auto-fetch fixtures |
| PATCH | `/api/matchdays/:id` | Оновити тур |
| POST | `/api/fixtures` | Додати матч |
| POST | `/api/fixtures/bulk-update` | Масове оновлення |
| POST | `/api/settings/budget` | Встановити бюджет |
| POST | `/api/admin/fix-squad` | Fix orphaned squad |
| POST | `/api/admin/fix-snapshots` | Fix snapshots |
| POST | `/api/admin/rebuild-squad` | Rebuild squad |

---

## Що зроблено

### Phase 1: Core + My Team ✅
- [x] Scoring engine, Predictor v3, ILP optimizer
- [x] UEFA JSON import + snapshots + auto squad remap
- [x] My Team: pitch view, captain, build mode (no hard limits)
- [x] Transfers: 2 free/matchday, -4pts extra
- [x] Smart suggestions with priority + reasoning
- [x] Archive, Matchday Wizard, Fetch Results, Cron
- [x] Admin auth, dynamic budget, bilingual UA/EN

### Phase 2: Fixture Difficulty & Intelligence ✅
- [x] Fixture Difficulty Calendar (clubs × matchdays, color-coded 1-5)
- [x] Hot Picks (form × fixture ease ranking)
- [x] Form Trends (player modal with bar chart, rising/falling/stable)
- [x] Price Tracking (history on import, risers/fallers tab)
- [x] Multi-matchday suggestions (2-3 tours + club strength factor)

### Phase 3: Boosters & Strategy ✅
- [x] Limitless (unlimited transfers, squad backup + rollback)
- [x] Wildcard (full rebuild)
- [x] Knockout Path (visual bracket, advance %, squad players per club)
- [x] Compare Players (search, up to 6, bar chart by matchday)

### Phase 4: Polish (FUTURE)
- [ ] PWA / mobile-friendly redesign
- [ ] Push notifications (deadline reminders)
- [ ] Captain suggestions з аналітикою
- [ ] Auto-sub logic
- [ ] Chip planner ("коли юзати Limitless/Wildcard")
- [ ] Leaderboard

---

## Workflow нового туру
1. **Import Data → New Matchday Wizard** → обрати стадію → Create
2. Завантажити **UEFA JSON** (DevTools → Network → `players_80_en_10.json`)
3. Upload → створить snapshots + price history
4. **Після матчів** → Fetch Results (або cron автоматично)
5. **Ре-імпорт UEFA JSON** → matchday points (lastGdPoints)
6. Переглянути **Archive** для результатів

---

## Архітектурні рішення
1. Semi-automatic import (UEFA не має публічного API)
2. Predictor v3: avg_points primary + fixture + upside factor
3. SQLite для MVP
4. Single admin key (один юзер)
5. `rules.py` — всі правила в одному місці
6. Player snapshots + lastGdPoints для точних matchday points
7. Builder без жорстких лімітів (warnings only)
8. **Git-based deploy** (ніколи не copy-paste Python)
9. Long-term suggestions: club strength → advance probability

---

## Environment
```
DB_PATH=/app/data/fantasy.db
ADMIN_KEY=ucl-admin-2026
```

_Останнє оновлення: лютий 2026 | ~6000 LOC | Phase 1-3 complete_
