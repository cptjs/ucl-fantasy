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
# З дроплета (рекомендовано):
cd /root/ucl-fantasy
git fetch origin && git reset --hard origin/main
docker compose build --no-cache && docker compose up -d

# Або одним рядком:
ssh root@134.122.70.107 "cd /root/ucl-fantasy && git fetch origin && git reset --hard origin/main && docker compose build --no-cache && docker compose up -d"
```

### GitHub push (з sandbox OpenClaw)
```bash
cd /workspace/ucl-fantasy
git add -A && git commit -m "опис змін"
git push origin main
```

---

## Стек

### Backend (`backend/`) — 2944 LOC
| Файл | LOC | Що робить |
|---|---|---|
| `main.py` | 1335 | FastAPI — всі ендпоінти (CRUD, імпорт, оптимізатор, трансфери, suggestions, archive, wizard) |
| `database.py` | 180 | SQLite init + `db_session()` context manager |
| `rules.py` | 145 | Правила по стадіях (бюджет, ліміт клубів, трансфери). **Центральне місце для всіх правил** |
| `scoring.py` | 101 | Scoring engine — повні правила UCL Fantasy (очки за голи/асисти/CS/тощо) |
| `predictor.py` | 229 | **Predictor v3**: avg_points × fixture_modifier × upside × minutes_prob |
| `optimizer.py` | 177 | ILP optimizer (PuLP): 15 гравців, 3 risk profiles (safe/balanced/aggressive) |
| `import_uefa.py` | 308 | Парсер UEFA JSON (`players_80_en_10.json` з DevTools), snapshots, squad remap |
| `fetch_results.py` | 123 | Автофетч результатів матчів через football-data.org API |
| `difficulty.py` | 86 | Fixture difficulty ratings (stub, планується розширення) |
| `update_leg1_to_leg2.py` | 260 | Міграція між легами (оновлення фікстур, snapshots) |

### Frontend (`frontend/src/`) — 1670 LOC
| Файл/Папка | LOC | Що робить |
|---|---|---|
| `App.jsx` | 90 | Роутінг, хедер з навігацією, мова UA/EN |
| `pages/MyTeam.jsx` | 582 | **Головна**: Pitch view, капітан, Build mode (без жорстких лімітів), Smart Transfer Suggestions |
| `pages/SquadBuilder.jsx` | 243 | AI оптимізатор — вибір профілю, бюджету → оптимальний склад |
| `pages/Predictions.jsx` | 195 | Прогнози + факт. очки, таби по турах |
| `pages/ImportData.jsx` | 205 | Адмін: New Matchday Wizard, UEFA JSON import, Fetch Results |
| `pages/Archive.jsx` | 146 | Архів минулих турів: фікстури, рахунки, топ-перформери, squad points |
| `pages/Dashboard.jsx` | 135 | Загальна інфо, фікстури, топ гравці |
| `pages/Players.jsx` | 74 | Таблиця гравців з пошуком/фільтром |
| `components/ClubLogo.jsx` | — | Лого клубів з UEFA CDN |
| `locales/translations.js` | — | UA/EN переклади |

### Docker
- `Dockerfile` — multi-stage: frontend build → backend serve (FastAPI + static)
- `docker-compose.yml` — один сервіс, порт 80→8000, volume для DB

---

## База даних (SQLite)

### Таблиці
| Таблиця | Опис |
|---|---|
| `players` | Гравці: ім'я, клуб, позиція, ціна, очки, форма, stats, uefa_id |
| `matchdays` | Тури: назва, stage, is_active, deadline |
| `fixtures` | Матчі: команди, рахунок, kick_off, status (scheduled/live/played) |
| `match_stats` | Статистика гравців по турах |
| `player_snapshots` | Snapshot очок (total_before/after/matchday_points) |
| `my_squad` | Моя команда: 15 гравців, капітан, стартовий/запасний |
| `transfers` | Історія трансферів по турах (is_free) |
| `boosters` | Бустери (Limitless, Wildcard) — таблиця є, логіка не реалізована |
| `settings` | Key-value настройки (бюджет тощо) |
| `squads` | Збережені оптимізовані склади |

---

## Predictor v3 (поточний)

**Формула:** `base × fixture_mod × upside × minutes_prob`

- **Base**: `avg_points * 0.8 + price_signal * 0.2` (blended)
- **Fixture modifier**: слабкий суперник (0.3) = x1.55, сильний (0.9) = x0.60
- **Upside**: x1.35 базовий + бонус для дорогих гравців (65-й перцентиль замість mean)
- **Set pieces**: +1.2-1.6 pts
- **Minutes prob**: 0.95 (starter 80+ min) → 0.30 (non-starter) → 0 (injured)
- **Результат**: розкид 1-18 pts (було 1-6 у v1)

---

## Правила UCL Fantasy (`rules.py`)

| Стадія | Бюджет | Max/клуб | Free transfers |
|---|---|---|---|
| League Phase | 100M | 3 | 2 (carry 1) |
| KO Playoffs Leg 1 | 105M | 4 | unlimited (new stage) |
| KO Playoffs Leg 2 | 105M | 4 | 2 |
| R16 Leg 1 | 105M | 4 | unlimited |
| R16 Leg 2 | 105M | 4 | 3 |
| QF | 105M | 5 | 5 |
| SF | 105M | 6 | 5 |
| Final | 105M | 8 | 5 |

---

## API ендпоінти

### Public
- `GET /api/players` — список гравців (фільтри: position, club)
- `GET /api/matchdays` — тури
- `GET /api/fixtures?matchday_id=` — матчі туру
- `GET /api/predictions` — прогнози очок (з actual якщо є)
- `GET /api/my-squad` — моя команда + бюджет + трансфери
- `GET /api/my-squad/suggestions` — **smart suggestions** з priority/reasoning/actions
- `GET /api/rules` — правила поточної стадії + all_stages
- `GET /api/settings` — настройки
- `GET /api/dashboard` — зведена інфо
- `GET /api/clubs` — список клубів
- `GET /api/archive` — **всі тури**: фікстури, рахунки, топ-перформери, squad points
- `POST /api/optimize` — запуск оптимізатора
- `POST /api/my-squad/set` — зберегти команду
- `POST /api/my-squad/transfer` — зробити трансфер
- `POST /api/my-squad/lineup` — змінити lineup (капітан, старт/лава)
- `POST /api/fetch-results` — фетч результатів з football-data.org

### Admin (потрібен `X-Admin-Key` header)
- `POST /api/players/import-uefa` — імпорт JSON від UEFA
- `POST /api/players/import-csv` — імпорт CSV
- `DELETE /api/players` — видалити всіх гравців
- `POST /api/matchdays` — створити тур
- `POST /api/matchdays/wizard?stage=` — **wizard**: створити тур + auto-fetch fixtures
- `PATCH /api/matchdays/:id` — оновити тур
- `POST /api/fixtures` — додати матч
- `POST /api/fixtures/bulk-update` — масове оновлення фікстур
- `POST /api/settings/budget` — встановити бюджет
- `POST /api/stats/import-csv` — імпорт статистики
- `POST /api/admin/fix-squad` — fix orphaned squad refs
- `POST /api/admin/fix-snapshots` — fix snapshots via lastGdPoints
- `POST /api/admin/rebuild-squad` — rebuild squad from player names

---

## Що зроблено ✅

### Phase 1: Core + My Team (DONE)
- [x] Scoring engine (повні правила UCL Fantasy)
- [x] Heuristic predictor v3 (avg × fixture × upside × minutes)
- [x] ILP optimizer (PuLP) — 3 risk profiles
- [x] UEFA JSON import з auto-remap squad + snapshots
- [x] Fixture management (status/scores/kick_off)
- [x] Club logos з UEFA CDN
- [x] Prediction + actual points display
- [x] Player snapshots (lastGdPoints для точних matchday points)
- [x] Auto-fetch results (football-data.org + cron)
- [x] **My Team page**: pitch view, squad info bar, captain/vice-captain
- [x] **Team Builder** (без жорстких лімітів — лише warnings)
- [x] **Transfer system**: 2 free/matchday, -4pts extra, validation
- [x] **Smart Transfer Suggestions**: priority (injured/low/upgrade), reasoning, quick actions
- [x] **Admin auth**: `X-Admin-Key` for import/delete endpoints
- [x] **Set as My Team** from SquadBuilder optimizer result
- [x] **Edit Team**: opens builder pre-loaded with current squad
- [x] **Dynamic budget**: reads from `rules.py` per stage
- [x] **Bilingual UI**: UA/EN with translations
- [x] **Archive page**: past matchdays, fixtures, scores, top performers, squad points
- [x] **New Matchday Wizard**: creates matchday + auto-fetches fixtures
- [x] **Fetch Results button**: on Import Data page
- [x] **Cron auto-fetch**: Tue/Wed 23:30 UTC on droplet

---

## Phase 2: Fixture Difficulty & Smart Suggestions (PLANNED)

### Fixture Difficulty Calendar
- [ ] Рейтинг складності опонентів (1-5 зірок)
- [ ] Календар на 3-5 турів вперед (knockout bracket view)
- [ ] Кольорове кодування (зелений = легкий, червоний = важкий)
- [ ] Врахування домашніх/виїзних матчів

### Enhanced Transfer Suggestions
- [x] Базові smart suggestions з priority + reasoning ✅
- [ ] Враховувати upcoming fixtures (2+ тури вперед, не тільки наступний)
- [ ] Form trends (зростає/падає по останніх N турах)
- [ ] "Hot picks" — гравці з легким календарем і хорошою формою

### Price Changes Tracking
- [ ] Зберігати історію цін при кожному імпорті
- [ ] Показувати тренд (↑↓) в UI
- [ ] Прогнозувати зміни цін

---

## Phase 3: Boosters & Knockout Strategy (PLANNED)

### Boosters
- [ ] **Limitless**: необмежені трансфери на 1 тур (команда повертається після)
- [ ] **Wildcard**: повна перебудова команди (залишається)
- [ ] UI для активації бустерів
- [ ] Логіка відкату Limitless після туру
- [ ] Таблиця `boosters` вже є, треба імплементувати logic

### Knockout Path Analysis
- [ ] Факторити ймовірних опонентів наступних раундів
- [ ] "Якщо Реал пройде далі, їхні гравці матимуть хорошу серію матчів"
- [ ] Long-term value гравців = fixture difficulty × probability of advancing

### Points History
- [ ] Накопичувальна база очок по турах (не скидати при імпорті)
- [ ] Графік перфомансу гравця по турах
- [ ] Порівняння гравців

---

## Phase 4: Polish (FUTURE)
- [ ] PWA / mobile-friendly redesign
- [ ] Push notifications (deadline reminders)
- [ ] Captain suggestions з аналітикою
- [ ] Auto-sub logic (show who would auto-sub in)
- [ ] Chip planner ("коли краще юзати Limitless/Wildcard")
- [ ] Leaderboard (якщо більше юзерів)

---

## Імпорт даних (workflow)

### Новий тур (повний workflow)
1. **Import Data → New Matchday Wizard** → обрати стадію → Create
2. Завантажити свіжий **UEFA JSON** (DevTools → Network → `players_80_en_10.json`)
3. Upload через Import Data → створить snapshots baseline
4. **Після матчів** — натиснути Fetch Results (або cron зробить автоматично)
5. **Ре-імпорт UEFA JSON** → бачиш matchday points (lastGdPoints)
6. Переглянути **Archive** для результатів

### Гравці (перед кожним новим туром)
1. Відкрити UEFA Fantasy → DevTools → Network
2. Знайти запит `players_80_en_10.json`
3. Скопіювати response JSON, зберегти файл
4. Завантажити через Import Data → Upload UEFA JSON

---

## Ключові архітектурні рішення
1. **Semi-automatic import > scraping**: UEFA не має публічного API
2. **Predictor v3**: avg_points як primary signal + fixture modifier + upside factor
3. **SQLite > Postgres**: Для MVP достатньо
4. **Single admin key > full auth**: Один юзер
5. **Rules engine (`rules.py`)**: Всі правила в одному місці
6. **Player snapshots + lastGdPoints**: Точні matchday points
7. **football-data.org**: Free tier (10 req/min), CL fixtures/results
8. **Builder без лімітів**: Юзер відтворює реальну команду, лише warnings
9. **Git-based deploy**: Push з sandbox → pull на дроплеті (без copy-paste Python)

---

## Club Logo IDs (UEFA CDN)
```
BVB=52758 ATA=52816 GAL=50067 MON=50023 QAR=60609
NEW=59324 BOD=59333 INT=50138 LEV=50109 OLY=2610
RMA=50051 PSG=52747 JUV=50139 BEN=50147 ATM=50124
BRU=50043
```
URL pattern: `https://img.uefa.com/imgml/TP/teams/logos/100x100/{id}.png`

---

## Environment
```
DB_PATH=/app/data/fantasy.db
ADMIN_KEY=ucl-admin-2026
```

---
_Останнє оновлення: лютий 2026_
