# UCL Fantasy Assistant — Deployment Guide

## DigitalOcean Droplet Setup

### Requirements
- **Plan:** Basic $6/mo (1 GB RAM / 1 vCPU / 25 GB SSD)
- **Region:** FRA1 (or closest to you)
- **OS:** Ubuntu 24.04 LTS x64

### Step 1: Connect to droplet
```bash
ssh root@YOUR_DROPLET_IP
```

### Step 2: Install Docker
```bash
curl -fsSL https://get.docker.com | sh
```

### Step 3: Upload project files
From your local machine (where you have the ucl-fantasy folder):
```bash
scp -r ucl-fantasy root@YOUR_DROPLET_IP:/root/
```

Or use VS Code Remote SSH extension to open the droplet and paste files there.

### Step 4: Build and run
```bash
cd /root/ucl-fantasy
docker compose up -d --build
```

### Step 5: Open in browser
```
http://YOUR_DROPLET_IP
```

That's it! The app is running.

---

## How to Use

### 1. Import Players
- Go to **Import Data** tab
- Upload a CSV file with player data (see `data/sample_players.csv` for format)
- Columns: `name, club, position, price, is_starter, is_set_piece_taker, injury_status`

### 2. Create Matchday
- Give it a name (e.g. "Playoff R1 Leg 2")
- Select stage (Knockout / League Phase — affects some rules)
- Set deadline (optional)

### 3. Add Fixtures
- Select the matchday
- Add each match: home club, away club
- Set **strength** (0-1 scale):
  - `0.9-1.0` = Elite (Real Madrid, Man City, Bayern)
  - `0.7-0.8` = Strong (Arsenal, Barcelona, Inter)
  - `0.5-0.6` = Mid-tier (PSV, Benfica, Atalanta)
  - `0.3-0.4` = Weaker (Celtic, Salzburg)
- **IMPORTANT:** Club names must match EXACTLY between players CSV and fixtures

### 4. View Predictions
- Go to **Predictions** tab
- See expected points for all players playing this matchday
- Filter by position
- Click any player to see reasoning

### 5. Build Squad
- Go to **Squad Builder** tab
- Set budget (default €100M), max per club, risk profile
- Click **Build Squad**
- Get starting XI + bench + captain recommendation

### 6. Import Past Stats (improves predictions)
- After a matchday is played, upload stats CSV
- This feeds the form/history for better future predictions
- Columns: `player_name, minutes, goals, goals_outside_box, assists, balls_recovered, player_of_match, penalty_won, penalty_conceded, penalty_missed, penalty_saved, yellow_card, red_card, own_goal, saves, goals_conceded, clean_sheet`

---

## Updating
```bash
cd /root/ucl-fantasy
docker compose down
docker compose up -d --build
```

## Viewing logs
```bash
docker compose logs -f
```

## Backup data
```bash
docker cp ucl-fantasy:/app/data/fantasy.db ./backup_fantasy.db
```
