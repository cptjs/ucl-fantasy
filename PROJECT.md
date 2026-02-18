# UCL Fantasy Football Assistant — Project Guide

## Що це

AI-асистент для UEFA Champions League Fantasy Football. Прогнозує оптимальний склад, відстежує команду, трансфери, бустери. Веб-додаток: FastAPI бекенд + React фронтенд.

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

### Деплой

```bash
ssh root@134.122.70.107
cd /root/ucl-fantasy
git fetch origin && git reset --hard origin/main
docker compose build --no-cache && docker compose up -d
```

Або одним рядком:
```bash
ssh root@134.122.70.107 "cd /root/ucl-fantasy && git fetch origin && git reset --hard origin/main && docker compose build --no-cache && docker compose up -d"
```

### GitHub push

```bash
cd /workspace/ucl-fantasy
git add -A && git commit -m "опис змін"
git push origin main
```

> ⚠️ GitHub token може бути expired. Якщо push не працює — згенерувати новий PAT на GitHub → Settings → Developer settings → Personal access tokens.

---

## Стек

### Backend (`backend/`)

| Файл | Що робить |
|---|---|
| `main.py` | FastAPI — всі ендпоінти (CRUD, імпорт, оптимізатор, трансфери, suggestions) |
| `database.py` | SQLite init + `db_session()` context manager |
| `rules.py` | Правила по стадіях (бюджет, ліміт клубів, трансфери). **Центральне місце для всіх правил** |
| `scoring.py` | Scoring engine — повні правила UCL Fantasy (очки за голи/асисти/CS/тощо) |
| `predictor.py` | Heuristic predictor: `base × fixture × form × minutes_probability` |
| `optimizer.py` | ILP optimizer (PuLP): 15 гравців, 3 risk profiles (safe/balanced/aggressive) |
| `import_uefa.py` | Парсер UEFA JSON (`players_80_en_10.json` з DevTools) |
| `fetch_results.py` | Автофетч результатів матчів через football-data.org API |
| `requirements.txt` | Python deps |

### Frontend (`frontend/`)

| Файл/Папка | Що робить |
|---|---|
| `src/App.jsx` | Роутінг, хедер з навігацією, мова UA/EN |
| `src/pages/MyTeam.jsx` | **Головна сторінка** — Pitch view, капітан, squad info, Edit Team (build mode), трансфери |
| `src/pages/SquadBuilder.jsx` | AI оптимізатор — вибір профілю, бюджету → оптимальний склад |
| `src/pages/Players.jsx` | Таблиця гравців з пошуком/фільтром |
| `src/pages/Predictions.jsx` | Прогнози очок по гравцях + фактичні результати |
| `src/pages/Dashboard.jsx` | Загальна інфо, фікстури, статистика |
| `src/pages/ImportData.jsx` | Адмін: імпорт JSON, управління matchday'ями |
| `src/components/ClubLogo.jsx` | Лого клубів з UEFA CDN |
| `src/locales/translations.js` | UA/EN переклади |

### Docker

- `Dockerfile` — multi-stage: frontend build → backend serve (FastAPI + static)
- `docker-compose.yml` — один сервіс, порт 80→8000, volume для DB

---

## База даних (SQLite)

### Таблиці

| Таблиця | Опис |
|---|---|
| `players` | Гравці: ім'я, клуб, позиція, ціна, очки, форма, stats |
| `matchdays` | Тури: назва, stage (league_phase/ko_playoffs/...), is_active |
| `fixtures` | Матчі: команди, рахунок, kick_off, status (scheduled/live/played) |
| `match_stats` | Статистика гравців по турах |
| `player_snapshots` | Snapshot очок на момент імпорту (для розрахунку matchday points) |
| `my_squad` | Моя команда: 15 гравців, капітан, стартовий/запасний |
| `transfers` | Історія трансферів по турах |
| `boosters` | Бустери (Limitless, Wildcard) — поки не реалізовано |
| `settings` | Key-value настройки (бюджет тощо) |
| `squads` | Збережені оптимізовані склади |

---

## Правила UCL Fantasy (`rules.py`)

Бюджет і ліміти залежать від стадії:

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

**Важливо**: 1 тур = 1 leg = 8 матчів (не обидва леги!).

---

## API ендпоінти

### Public (без ключа)
- `GET /api/players` — список гравців (фільтри: position, club)
- `GET /api/matchdays` — тури
- `GET /api/fixtures?matchday_id=` — матчі туру
- `GET /api/predictions` — прогнози очок
- `GET /api/my-squad` — моя команда + бюджет + трансфери
- `GET /api/rules` — правила поточної стадії
- `GET /api/settings` — настройки
- `GET /api/my-squad/suggestions` — рекомендації трансферів
- `GET /api/dashboard` — зведена інфо
- `GET /api/clubs` — список клубів
- `POST /api/optimize` — запуск оптимізатора
- `POST /api/my-squad/set` — зберегти команду
- `POST /api/my-squad/transfer` — зробити трансфер
- `POST /api/my-squad/lineup` — змінити lineup (капітан, старт/лава)

### Admin (потрібен `X-Admin-Key` header)
- `POST /api/players/import-uefa` — імпорт JSON від UEFA
- `POST /api/players/import-csv` — імпорт CSV
- `DELETE /api/players` — видалити всіх гравців
- `POST /api/matchdays` — створити тур
- `PATCH /api/matchdays/:id` — оновити тур
- `POST /api/fixtures` — додати матч
- `POST /api/fixtures/bulk-update` — масове оновлення фікстур
- `POST /api/settings/budget` — встановити бюджет
- `POST /api/fetch-results` — фетч результатів з football-data.org
- `POST /api/stats/import-csv` — імпорт статистики

---

## Що зроблено ✅

### Phase 1: Core + My Team (DONE)

- [x] Scoring engine (повні правила UCL Fantasy)
- [x] Heuristic predictor (base × fixture × form × minutes)
- [x] ILP optimizer (PuLP) — 3 risk profiles
- [x] UEFA JSON import (`import_uefa.py`)
- [x] Fixture management (status/scores/kick_off)
- [x] Club logos з UEFA CDN
- [x] Prediction + actual points display (grey pred, green/red actual)
- [x] Player snapshots (baseline + diff = matchday points)
- [x] Auto-fetch results (football-data.org free API)
- [x] Rounded points to integers
- [x] Fixture sorting (played → scheduled, by kick_off)
- [x] **My Team page**: pitch view, squad info bar, captain/vice-captain
- [x] **Team Builder** (build mode in MyTeam): pick 15 players, search/filter, position counters, budget tracker, club limit
- [x] **Transfer system**: tap to replace, 2 free/matchday, -4pts penalty per extra, position/budget/club validation
- [x] **Transfer suggestions**: top-10 upgrades per position by expected points gain
- [x] **Admin auth**: `X-Admin-Key` for import/delete endpoints
- [x] **Set as My Team** from SquadBuilder optimizer result
- [x] **Edit Team**: opens builder pre-loaded with current squad
- [x] **Dynamic budget**: reads from `rules.py` per stage (not hardcoded 100M)
- [x] **Bilingual UI**: UA/EN with translations

---

## Відомі баги / TODO 🐛

### Budget при Edit Team
- **Проблема**: коли гравці подорожчали і реальна команда коштує > 105M, Edit Team показує занизький бюджет. Гравець який вже в реальній команді може не поміститись у білдері.
- **Рішення**: endpoint `POST /api/settings/budget` дозволяє встановити кастомний бюджет. Треба або:
  - a) Додати UI для ручного введення бюджету ("Set my real budget")
  - b) Або при Edit Team автоматично ставити бюджет = total_value поточної команди + remaining від реального Fantasy

### Cron для auto-fetch results
- Потрібно налаштувати на дроплеті:
  ```
  0 1 * * * docker exec ucl-fantasy python fetch_results.py
  ```
- Або через OpenClaw cron

---

## Phase 2: Fixture Difficulty & Smart Suggestions (PLANNED)

### Fixture Difficulty Calendar
- [ ] Рейтинг складності опонентів (1-5 зірок)
- [ ] Календар на 3-5 турів вперед
- [ ] Кольорове кодування (зелений = легкий, червоний = важкий)
- [ ] Врахування домашніх/виїзних матчів

### Enhanced Transfer Suggestions
- [ ] Враховувати upcoming fixtures (не тільки наступний матч)
- [ ] Form trends (зростає/падає)
- [ ] Поточний склад + fixture difficulty = "ось кого міняти"
- [ ] "Hot picks" — гравці з легким календарем і хорошою формою

### Price Changes Tracking
- [ ] Зберігати історію цін
- [ ] Показувати тренд (↑↓)
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

### Гравці (перед кожним новим туром)
1. Відкрити UEFA Fantasy → DevTools → Network
2. Знайти запит `players_80_en_10.json` (або схожий)
3. Скопіювати response JSON
4. Зберегти як файл
5. Завантажити через Import Data → Upload UEFA JSON
6. Backend парсить, оновлює ціни, створює snapshots

### Результати (після матчів)
- Автоматично: `POST /api/fetch-results` (football-data.org)
- Або ручний fetch: Import Data → Fetch Results

### Статистика гравців (для matchday points)
- Ре-імпорт UEFA JSON після матчів оновлює `total_points`
- `player_snapshots` рахує diff = matchday points

---

## Ключові архітектурні рішення

1. **Semi-automatic import > scraping**: UEFA не має публічного API, JSON з DevTools надійніший
2. **Heuristic predictor > ML**: Занадто мало UCL матчів на сезон для ML
3. **SQLite > Postgres**: Для MVP достатньо, легко мігрувати
4. **Single admin key > full auth**: Один юзер, простий API key
5. **Rules engine (`rules.py`)**: Всі правила в одному місці, залежать від стадії
6. **Player snapshots**: `total_points_before` при першому імпорті → diff при ре-імпорті = matchday points
7. **football-data.org**: Free tier (10 req/min), достатньо для результатів CL

---

## Club Logo IDs (UEFA CDN)

```
BVB=52758  ATA=52816  GAL=50067  MON=50023
QAR=60609  NEW=59324  BOD=59333  INT=50138
LEV=50109  OLY=2610   RMA=50051  PSG=52747
JUV=50139  BEN=50147  ATM=50124  BRU=50043
```

URL pattern: `https://img.uefa.com/imgml/TP/teams/logos/100x100/{id}.png`

---

## Environment

```
DB_PATH=/app/data/fantasy.db
ADMIN_KEY=ucl-admin-2026
```

---

_Останнє оновлення: 18 лютого 2026_
