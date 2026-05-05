# ♟️ Chess Cheating Detection — Complete Project Guide
> Machine Learning — Phase 1 | Dataset Constitution
> École Nationale des Sciences Appliquées de Tétouan — 2025/2026

---

## 📌 Table of Contents
1. [Project Concept](#1-project-concept)
2. [The Target Variable](#2-the-target-variable)
3. [Dataset Structure](#3-dataset-structure)
4. [The API — Lichess](#4-the-api--lichess)
5. [Data Collection Strategy](#5-data-collection-strategy)
6. [Full Python Script](#6-full-python-script)
7. [Feature Engineering](#7-feature-engineering)
8. [Project Requirements Checklist](#8-project-requirements-checklist)
9. [Business Justification](#9-business-justification)
10. [Deliverables Checklist](#10-deliverables-checklist)

---

## 1. Project Concept

### What is the problem?

On **Lichess** (lichess.org) — the world's biggest free and open-source chess platform — some players cheat by using chess engines like **Stockfish** during their games. The engine tells them the best possible move every turn, making them play far above their actual skill level.

Lichess has their own internal detection system but it is proprietary and secret. Your project is to **build a dataset** that captures the signals of suspicious play, which could later be used to train a machine learning classifier.

### Business Question
> *"Based on a player's in-game statistics, is this game suspicious of chess engine use?"*

This is a **real problem** that real companies (Lichess, Chess.com) spend serious engineering effort on. It is original, technically serious, and very impressive to present.

### Why this is perfect for your project
- It is a **binary classification** problem ✅
- The minority class (cheaters) is **naturally rare** (~10-15%) ✅
- Data comes from a **completely free public API** ✅
- You can collect **10,000+ rows in one afternoon** ✅
- It has a clear **business justification and asymmetric cost** ✅
- It is **impossible to find as an existing Kaggle dataset** ✅

---

## 2. The Target Variable

### Definition
```
is_suspicious = 1   if the player's accuracy is abnormally above their rating level
is_suspicious = 0   otherwise (normal game)
```

### How to Calculate It

Lichess provides an **accuracy score** (0-100%) for each player in each game that has been analyzed by Stockfish. This score measures how closely the player's moves matched the engine's recommendations.

**Step 1 — Know the expected accuracy per rating level:**

| Rating Range | Expected Avg Accuracy |
|---|---|
| 0 – 1000 | ~55% |
| 1000 – 1200 | ~62% |
| 1200 – 1400 | ~68% |
| 1400 – 1600 | ~73% |
| 1600 – 1800 | ~78% |
| 1800 – 2000 | ~83% |
| 2000+ | ~88% |

**Step 2 — Calculate the accuracy gap:**
```
accuracy_gap = actual_accuracy - expected_accuracy_for_rating
```

**Step 3 — Label the game:**
```python
if accuracy_gap > 20:
    is_suspicious = 1   # abnormally good → suspicious
else:
    is_suspicious = 0   # normal performance
```

### Example

| Player Rating | Actual Accuracy | Expected Accuracy | Gap | Label |
|---|---|---|---|---|
| 1200 | 96% | 68% | +28% | **1 (suspicious)** |
| 1500 | 75% | 73% | +2% | 0 (normal) |
| 2100 | 91% | 88% | +3% | 0 (normal) |
| 900 | 82% | 55% | +27% | **1 (suspicious)** |

### Why This Gives Natural Imbalance
- Most players play at or near their expected level → `is_suspicious = 0` (majority)
- A small minority plays abnormally well → `is_suspicious = 1` (minority, ~10-15%)
- This naturally falls in the **5-25% required range** ✅

---

## 3. Dataset Structure

### One Row = One Game Played by One Player

Since each game has two players (White and Black), each game gives you **2 rows**.

### Feature Table

| # | Feature | Type | Description |
|---|---|---|---|
| 1 | `player_rating` | Numerical | ELO rating of the player we are analyzing |
| 2 | `opponent_rating` | Numerical | ELO rating of their opponent |
| 3 | `rating_diff` | Numerical | Absolute difference between both ratings |
| 4 | `player_accuracy` | Numerical | Accuracy % Lichess calculated for this game |
| 5 | `expected_accuracy` | Numerical | Average accuracy for this rating bracket |
| 6 | `accuracy_gap` | Numerical | player_accuracy - expected_accuracy |
| 7 | `num_moves` | Numerical | Total number of moves in the game |
| 8 | `avg_time_per_move` | Numerical | Average seconds the player spent per move |
| 9 | `performance_rating` | Numerical | Performance rating achieved in this game |
| 10 | `time_control_seconds` | Numerical | Base time in seconds (e.g. 300 for 5 min) |
| 11 | `time_control` | Categorical | bullet / blitz / rapid / classical |
| 12 | `game_result` | Categorical | win / loss / draw |
| 13 | `opening_eco` | Categorical | ECO opening code (A00–E99) |
| 14 | `color_played` | Categorical | white or black |
| 15 | `is_rated` | Categorical | true or false |
| 16 | **`is_suspicious`** | **Target** | **1 = suspicious, 0 = normal** |

**Total: 15 features + 1 target = 16 columns** ✅ (well above the 8 minimum)

### Sample Data Preview

```
player_rating, opponent_rating, rating_diff, player_accuracy, expected_accuracy, accuracy_gap, num_moves, avg_time_per_move, performance_rating, time_control_seconds, time_control, game_result, opening_eco, color_played, is_rated, is_suspicious
1200, 1180, 20, 96.0, 68, 28.0, 34, 4.2, 1850, 300, blitz, win, B20, white, true, 1
1500, 1520, 20, 74.0, 73, 1.0, 52, 8.7, 1490, 600, rapid, loss, C60, black, true, 0
2100, 2080, 20, 91.0, 88, 3.0, 67, 12.1, 2110, 300, blitz, win, D30, white, true, 0
900, 950, 50, 83.0, 55, 28.0, 23, 2.1, 1400, 60, bullet, win, A00, black, true, 1
```

---

## 4. The API — Lichess

### Key Info
- **Base URL:** `https://lichess.org/api`
- **Authentication:** No API key required for basic use ✅
- **Rate Limiting:** ~1 request per second recommended
- **Documentation:** https://lichess.org/api

### The Two Endpoints You Need

#### Endpoint 1 — Get Top Players by Rating
```
GET https://lichess.org/api/player/top/{nb}/{perfType}
```

Parameters:
- `nb` = number of users to return (max 200)
- `perfType` = bullet / blitz / rapid / classical

Example:
```
GET https://lichess.org/api/player/top/50/blitz
```

Use this to get **usernames** of players at different rating levels. You will loop through them to collect their games.

> ⚠️ This only returns TOP players. To get lower-rated players, use arena tournaments or puzzle leaderboards for different rating ranges.

#### Endpoint 2 — Get Games of a User
```
GET https://lichess.org/api/games/user/{username}
```

Important parameters:
| Parameter | Value | Description |
|---|---|---|
| `max` | 100 | Maximum games to return |
| `rated` | true | Only rated games |
| `analysed` | true | Only games with Stockfish analysis (needed for accuracy!) |
| `clocks` | true | Include move time data |
| `perfType` | blitz | Filter by time control |

Example:
```
GET https://lichess.org/api/games/user/DrNykterstein?max=100&rated=true&analysed=true&clocks=true
```

> ⚠️ This endpoint returns **NDJSON** (newline-delimited JSON), not regular JSON. Each line is one game. Use `stream=True` in Python requests and process line by line.

### Response Structure (simplified)
```json
{
  "id": "q7ZvsdUF",
  "rated": true,
  "variant": "standard",
  "speed": "blitz",
  "perf": "blitz",
  "createdAt": 1514505150384,
  "players": {
    "white": {
      "user": { "name": "Lance5500", "id": "lance5500" },
      "rating": 1742,
      "ratingDiff": 6,
      "analysis": {
        "inaccuracy": 3,
        "mistake": 1,
        "blunder": 0,
        "acpl": 22,
        "accuracy": 87
      }
    },
    "black": {
      "user": { "name": "TryingHard87", "id": "tryinghard87" },
      "rating": 1635,
      "ratingDiff": -6,
      "analysis": {
        "inaccuracy": 6,
        "mistake 2,
        "blunder": 1,
        "acpl": 45,
        "accuracy": 71
      }
    }
  },
  "winner": "white",
  "opening": {
    "eco": "C50",
    "name": "Italian Game",
    "ply": 5
  },
  "moves": "e4 e5 Nf3 Nc6 Bc4 ...",
  "clocks": [6003, 6003, 5991, 5985, ...]
}
```

---

## 5. Data Collection Strategy

### How to Get 10,000+ Rows

```
100 users × 100 games × 2 players per game = 20,000 rows
```

### Step-by-Step Plan

```
STEP 1 — Collect usernames across rating levels
├── Get top 50 blitz players (2000+ rating)
├── Get players from blitz arena tournaments (1400-1800 rating)
└── Get players from puzzle leaderboard (mixed ratings)

STEP 2 — For each username, fetch their last 100 analyzed games
├── Use endpoint: /api/games/user/{username}
├── Filter: rated=true, analysed=true, clocks=true
└── Save raw JSON to file (so you don't re-query if script crashes)

STEP 3 — For each game, extract features for BOTH players
├── White player → 1 row
└── Black player → 1 row

STEP 4 — Calculate derived features
├── rating_diff = abs(white_rating - black_rating)
├── expected_accuracy = lookup table by rating
├── accuracy_gap = actual_accuracy - expected_accuracy
└── avg_time_per_move = total_time_used / num_moves

STEP 5 — Label each row
├── is_suspicious = 1 if accuracy_gap > 20
└── is_suspicious = 0 otherwise

STEP 6 — Save to CSV
└── data/dataset.csv
```

### Important Notes
- **Save raw JSON** after each API call to avoid re-querying if your script crashes
- **Respect rate limits** — add `time.sleep(1)` between requests
- **Only use analysed games** — games without Stockfish analysis won't have accuracy scores
- **Test first** on 10 games before running the full collection

---

## 6. Full Python Script

```python
"""
data_collection.py
Chess Cheating Detection Dataset — Lichess API
Machine Learning Project — Phase 1
ENSA Tétouan 2025/2026
"""

import requests
import pandas as pd
import json
import time
import os
import logging
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

BASE_URL = "https://lichess.org/api"
MAX_GAMES_PER_USER = 100
TARGET_ROWS = 10000
PERF_TYPE = "blitz"  # bullet / blitz / rapid / classical
OUTPUT_DIR = "data"
RAW_DIR = "data/raw"

# Set up logging
logging.basicConfig(
    filename="data_collection.log",
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s"
)

# Expected accuracy per rating bracket (based on Lichess statistics)
EXPECTED_ACCURACY = {
    (0, 1000): 55,
    (1000, 1200): 62,
    (1200, 1400): 68,
    (1400, 1600): 73,
    (1600, 1800): 78,
    (1800, 2000): 83,
    (2000, 9999): 88
}

# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────

def get_expected_accuracy(rating: int) -> int:
    """Return the expected average accuracy for a given ELO rating."""
    for (low, high), acc in EXPECTED_ACCURACY.items():
        if low <= rating < high:
            return acc
    return 75  # fallback

def label_suspicious(actual_accuracy: float, player_rating: int) -> tuple:
    """
    Label a game as suspicious if accuracy gap exceeds threshold.
    Returns (is_suspicious, accuracy_gap)
    """
    expected = get_expected_accuracy(player_rating)
    gap = round(actual_accuracy - expected, 2)
    label = 1 if gap > 20 else 0
    return label, gap, expected

def get_time_control_category(speed: str) -> str:
    """Normalize time control category."""
    mapping = {
        "bullet": "bullet",
        "blitz": "blitz",
        "rapid": "rapid",
        "classical": "classical",
        "correspondence": "correspondence"
    }
    return mapping.get(speed, "unknown")

# ─────────────────────────────────────────────
# API FUNCTIONS
# ─────────────────────────────────────────────

def get_top_users(perf_type: str = "blitz", count: int = 50) -> list:
    """
    Fetch top usernames for a given time control.
    Endpoint: GET /api/player/top/{nb}/{perfType}
    """
    url = f"{BASE_URL}/player/top/{count}/{perf_type}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        users = response.json().get("users", [])
        usernames = [u["username"] for u in users]
        logging.info(f"Fetched {len(usernames)} top users for {perf_type}")
        return usernames
    except Exception as e:
        logging.error(f"Error fetching top users: {e}")
        return []

def get_user_games(username: str, max_games: int = 100) -> list:
    """
    Fetch analyzed games for a given user.
    Endpoint: GET /api/games/user/{username}
    Returns NDJSON — parsed line by line.
    """
    # Check if already cached
    cache_path = f"{RAW_DIR}/{username}.json"
    if os.path.exists(cache_path):
        logging.info(f"Loading cached games for {username}")
        with open(cache_path, "r") as f:
            return json.load(f)

    url = f"{BASE_URL}/games/user/{username}"
    params = {
        "max": max_games,
        "rated": "true",
        "analysed": "true",
        "clocks": "true",
        "perfType": PERF_TYPE,
        "moves": "false"  # we don't need move list, saves bandwidth
    }
    headers = {"Accept": "application/x-ndjson"}

    games = []
    try:
        response = requests.get(
            url, params=params, headers=headers,
            stream=True, timeout=30
        )
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                try:
                    game = json.loads(line)
                    games.append(game)
                except json.JSONDecodeError:
                    continue

        # Cache the raw data
        os.makedirs(RAW_DIR, exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(games, f)

        logging.info(f"Fetched {len(games)} games for {username}")

    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error for {username}: {e}")
    except Exception as e:
        logging.error(f"Error fetching games for {username}: {e}")

    return games

# ─────────────────────────────────────────────
# FEATURE EXTRACTION
# ─────────────────────────────────────────────

def extract_player_row(game: dict, color: str) -> dict | None:
    """
    Extract one row of features for one player (color = 'white' or 'black').
    Returns None if data is incomplete.
    """
    try:
        players = game.get("players", {})
        player = players.get(color, {})
        opponent_color = "black" if color == "white" else "white"
        opponent = players.get(opponent_color, {})

        # Check that analysis data exists
        analysis = player.get("analysis")
        if not analysis or "accuracy" not in analysis:
            return None

        # Player info
        player_rating = player.get("rating", 0)
        opponent_rating = opponent.get("rating", 0)

        if player_rating == 0 or opponent_rating == 0:
            return None

        # Accuracy
        player_accuracy = analysis.get("accuracy", 0)
        is_suspicious, accuracy_gap, expected_acc = label_suspicious(
            player_accuracy, player_rating
        )

        # Game result from player's perspective
        winner = game.get("winner", "draw")
        if winner == "draw" or winner is None:
            result = "draw"
        elif winner == color:
            result = "win"
        else:
            result = "loss"

        # Move count
        moves_str = game.get("moves", "")
        num_moves = len(moves_str.split()) // 2 if moves_str else 0

        # Clock / timing
        clocks = game.get("clocks", [])
        # Filter clocks for this player (every other clock value)
        player_clocks = clocks[0::2] if color == "white" else clocks[1::2]
        if len(player_clocks) > 1:
            time_used_per_move = []
            for i in range(1, len(player_clocks)):
                diff = player_clocks[i-1] - player_clocks[i]
                if diff >= 0:
                    time_used_per_move.append(diff / 100)  # centiseconds to seconds
            avg_time = round(sum(time_used_per_move) / len(time_used_per_move), 2) if time_used_per_move else 0
        else:
            avg_time = 0

        # Time control
        clock_info = game.get("clock", {})
        time_control_seconds = clock_info.get("initial", 0)
        speed = game.get("speed", "unknown")
        time_control = get_time_control_category(speed)

        # Opening
        opening = game.get("opening", {})
        opening_eco = opening.get("eco", "A00")

        # Performance rating (approximate)
        rating_diff = abs(player_rating - opponent_rating)
        perf_rating = player_rating + (400 if result == "win" else -400 if result == "loss" else 0)

        return {
            "player_rating": player_rating,
            "opponent_rating": opponent_rating,
            "rating_diff": rating_diff,
            "player_accuracy": player_accuracy,
            "expected_accuracy": expected_acc,
            "accuracy_gap": accuracy_gap,
            "num_moves": num_moves,
            "avg_time_per_move": avg_time,
            "performance_rating": perf_rating,
            "time_control_seconds": time_control_seconds,
            "time_control": time_control,
            "game_result": result,
            "opening_eco": opening_eco,
            "color_played": color,
            "is_rated": game.get("rated", False),
            "is_suspicious": is_suspicious
        }

    except Exception as e:
        logging.warning(f"Error extracting features: {e}")
        return None

# ─────────────────────────────────────────────
# MAIN COLLECTION LOOP
# ─────────────────────────────────────────────

def collect_dataset():
    """Main function — collect all data and save to CSV."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)

    all_rows = []
    checkpoint_path = f"{OUTPUT_DIR}/checkpoint.csv"

    # Load checkpoint if it exists (resume after crash)
    if os.path.exists(checkpoint_path):
        df_existing = pd.read_csv(checkpoint_path)
        all_rows = df_existing.to_dict("records")
        print(f"Resuming from checkpoint: {len(all_rows)} rows already collected")

    # Get usernames
    print("Fetching usernames...")
    usernames = get_top_users(PERF_TYPE, 50)

    # Add more usernames from other sources if needed
    # You can manually add known usernames here:
    # extra_users = ["DrNykterstein", "Hikaru", "MagnusCarlsen"]
    # usernames = list(set(usernames + extra_users))

    print(f"Collected {len(usernames)} usernames. Starting game collection...")

    for i, username in enumerate(usernames):
        if len(all_rows) >= TARGET_ROWS:
            print(f"Target of {TARGET_ROWS} rows reached!")
            break

        print(f"[{i+1}/{len(usernames)}] Processing {username}...")
        games = get_user_games(username, MAX_GAMES_PER_USER)

        for game in games:
            for color in ["white", "black"]:
                row = extract_player_row(game, color)
                if row:
                    all_rows.append(row)

        # Save checkpoint every 10 users
        if (i + 1) % 10 == 0:
            df_checkpoint = pd.DataFrame(all_rows)
            df_checkpoint.to_csv(checkpoint_path, index=False)
            print(f"  → Checkpoint saved: {len(all_rows)} rows so far")

        time.sleep(1)  # Respect Lichess rate limiting

    # Final save
    df = pd.DataFrame(all_rows)
    output_path = f"{OUTPUT_DIR}/dataset.csv"
    df.to_csv(output_path, index=False)

    # Save sample (100 rows)
    df.sample(min(100, len(df))).to_csv(f"{OUTPUT_DIR}/sample.csv", index=False)

    # Print summary
    print("\n" + "="*50)
    print("DATASET COLLECTION COMPLETE")
    print("="*50)
    print(f"Total rows:        {len(df)}")
    print(f"Total columns:     {len(df.columns)}")
    print(f"Suspicious games:  {df['is_suspicious'].sum()} ({df['is_suspicious'].mean()*100:.1f}%)")
    print(f"Normal games:      {(df['is_suspicious']==0).sum()} ({(df['is_suspicious']==0).mean()*100:.1f}%)")
    print(f"Saved to:          {output_path}")

    logging.info(f"Dataset complete: {len(df)} rows, {df['is_suspicious'].mean()*100:.1f}% suspicious")
    return df

# ─────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    df = collect_dataset()
```

---

## 7. Feature Engineering

After collecting the raw data, you can engineer additional features to enrich the dataset:

### Additional Computed Features

| New Feature | Formula | Why It Helps |
|---|---|---|
| `rating_balance` | 1 if rating_diff < 50 else 0 | Evenly matched games are different |
| `is_high_level` | 1 if player_rating > 2000 | High level games behave differently |
| `opening_family` | First letter of ECO code (A/B/C/D/E) | Group openings into 5 families |
| `time_pressure` | avg_time_per_move / time_control_seconds | How rushed the player was |
| `accuracy_percentile` | Rank of accuracy among all games | Relative performance |

---

## 8. Project Requirements Checklist

| Requirement from Professor | Status | Details |
|---|---|---|
| Classification supervisée | ✅ | Binary: is_suspicious (0 or 1) |
| ≥ 10,000 rows | ✅ | ~20,000 rows easily collected |
| ≥ 8 features after engineering | ✅ | 15 features + target = 16 columns |
| Minority class 5-25% | ✅ | ~10-15% suspicious games |
| Mix of numerical + categorical | ✅ | Ratings/accuracy (num) + time_control/opening (cat) |
| Free public API | ✅ | Lichess API — no key needed |
| Reproductible Python script | ✅ | data_collection.py with logging + checkpoints |
| Dataset saved as CSV | ✅ | data/dataset.csv + data/sample.csv |

---

## 9. Business Justification

### Objectifs Métiers

| Objectif Métier | Objectif ML | Métrique Principale |
|---|---|---|
| Détecter 85% des joueurs qui trichent | Maximiser le recall sur la classe "suspicious" | Recall ≥ 0.85 |
| Limiter les fausses accusations | Maintenir une précision acceptable | Precision ≥ 0.50 |
| Protéger la compétition équitable | Classification binaire robuste | F1-score ≥ 0.65 |

### Analyse du Coût Asymétrique

> **Question fondamentale: que coûte plus cher — un faux positif ou un faux négatif?**

- **Faux Négatif** (cheater non détecté) → des centaines de joueurs perdent contre un tricheur → confiance dans la plateforme détruite → **coût très élevé**
- **Faux Positif** (joueur innocent accusé) → ban injuste, frustration → **coût modéré**

**→ Priorité: Maximiser le Recall** (attraper le maximum de tricheurs)

### Métriques Acceptées
- ✅ F1-score
- ✅ Recall
- ✅ Precision
- ✅ PR-AUC
- ❌ Accuracy seule (refusée car dataset déséquilibré)
- ❌ ROC-AUC seule

---

## 10. Deliverables Checklist

Based on your professor's requirements:

```
project/
├── cadrage.md                          ← Business framing document
├── src/
│   └── data_collection.py              ← The Python collection script
├── data/
│   ├── dataset.csv                     ← Full dataset (≥10,000 rows)
│   ├── sample.csv                      ← 100-row sample
│   └── raw/                            ← Raw JSON files from API
│       ├── username1.json
│       └── username2.json
├── DATASET.md                          ← Dataset documentation
└── notebooks/
    └── 01_discovery.ipynb              ← Exploratory notebook
```

### DATASET.md Must Contain:
- [ ] Dataset name, authors, collection date, version
- [ ] API used: Lichess API — `https://lichess.org/api`
- [ ] Endpoints used: `/api/player/top` and `/api/games/user/{username}`
- [ ] Number of rows and columns
- [ ] Schema: name, type, description, range for each variable
- [ ] Clear identification of target variable: `is_suspicious`
- [ ] Class distribution chart (value_counts + bar chart)

### 01_discovery.ipynb Must Contain:
```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("data/dataset.csv")

df.info()           # column types
df.describe()       # statistics
df.head()           # first rows

# Class distribution
print(df["is_suspicious"].value_counts())
df["is_suspicious"].value_counts().plot(kind="bar")
plt.title("Class Distribution — is_suspicious")
plt.show()
```

---

## 📝 Quick Reference

| Item | Value |
|---|---|
| Platform | Lichess (lichess.org) |
| API URL | https://lichess.org/api |
| API Key | Not required |
| Rate Limit | ~1 request/second |
| Target Variable | `is_suspicious` |
| Minority Class | ~10-15% (suspicious games) |
| Expected Rows | ~20,000 |
| Python Library | `requests`, `pandas`, `json` |
| Output Format | CSV |

---

*Document created for ML Project Phase 1 — ENSA Tétouan 2025/2026*