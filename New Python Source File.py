"""
data_collection.py
Chess Cheating Detection Dataset — Lichess API
Machine Learning Project — Phase 1
ENSA Tétouan 2025/2026

FEATURES:
- Collects blitz + rapid + classical games (not just blitz)
- Proper opening ECO codes (added opening=true to API)
- ACPL-based suspicious labeling with auto-adjust
- Diverse player pool from arena tournaments + top players
"""

import requests
import pandas as pd
import json
import time
import os
import logging
import math

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

BASE_URL = "https://lichess.org/api"
MAX_GAMES_PER_USER = 30          # per speed type
TARGET_ROWS = 12000
SPEED_TYPES = ["blitz", "rapid", "classical"]  # ← collect ALL game types
OUTPUT_DIR = "data"
RAW_DIR = "data/raw"

logging.basicConfig(
    filename="data_collection.log",
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s"
)

# Expected ACPL per rating bracket (lower = better play)
EXPECTED_ACPL = {
    (0, 1000):    105,
    (1000, 1200): 100,
    (1200, 1400):  90,
    (1400, 1600):  84,
    (1600, 1800):  75,
    (1800, 2000):  70,
    (2000, 9999):  39
}

SUSPICIOUS_THRESHOLD = -40

# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────

def get_expected_acpl(rating: int) -> int:
    for (low, high), acpl in EXPECTED_ACPL.items():
        if low <= rating < high:
            return acpl
    return 70


def label_suspicious(player_acpl: float, player_rating: int) -> tuple:
    """
    Suspicious = ACPL much lower than expected for this rating.
    A 1000-rated player with ACPL=15 (expected 105) → gap=-90 → suspicious
    A 2700-rated player with ACPL=15 (expected 39)  → gap=-24 → normal
    """
    expected = get_expected_acpl(player_rating)
    gap = round(player_acpl - expected, 1)
    label = 1 if gap < SUSPICIOUS_THRESHOLD else 0
    return label, gap, expected


def get_time_control_category(speed: str) -> str:
    mapping = {
        "ultraBullet": "bullet",
        "bullet": "bullet",
        "blitz": "blitz",
        "rapid": "rapid",
        "classical": "classical",
        "correspondence": "correspondence"
    }
    return mapping.get(speed, "unknown")

# ─────────────────────────────────────────────
# USERNAME COLLECTION (DIVERSE RATINGS)
# ─────────────────────────────────────────────

def get_top_users(perf_type="blitz", count=50):
    """Get top-rated players for a given speed."""
    url = f"{BASE_URL}/player/top/{count}/{perf_type}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        users = resp.json().get("users", [])
        names = [u["username"] for u in users]
        logging.info(f"Top {perf_type} users: {len(names)}")
        return names
    except Exception as e:
        logging.error(f"Error fetching top users ({perf_type}): {e}")
        return []


def get_arena_players(nb_tournaments=8):
    """Get players from recent arena tournaments (ALL rating levels)."""
    usernames = set()
    url = f"{BASE_URL}/tournament"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        tournament_ids = [t["id"] for t in data.get("finished", [])[:nb_tournaments]]
        time.sleep(1)

        for tid in tournament_ids:
            try:
                results_url = f"{BASE_URL}/tournament/{tid}/results"
                resp = requests.get(
                    results_url,
                    headers={"Accept": "application/x-ndjson"},
                    stream=True, timeout=30,
                    params={"nb": 100}
                )
                resp.raise_for_status()

                count = 0
                for line in resp.iter_lines():
                    if line and count < 100:
                        try:
                            player = json.loads(line)
                            username = player.get("username", "")
                            if username:
                                usernames.add(username)
                            count += 1
                        except json.JSONDecodeError:
                            continue
                resp.close()
                logging.info(f"Arena {tid}: total unique = {len(usernames)}")
                time.sleep(1)
            except Exception as e:
                logging.warning(f"Error arena {tid}: {e}")
                continue
    except Exception as e:
        logging.error(f"Error fetching tournaments: {e}")

    print(f"  Arena tournaments: {len(usernames)} unique players")
    return list(usernames)


def collect_diverse_usernames():
    """Combine sources for players across ALL rating levels."""
    print("Collecting usernames from multiple sources...")
    all_usernames = set()

    # Top players from each speed type
    for speed in SPEED_TYPES:
        top = get_top_users(speed, 50)
        all_usernames.update(top)
        print(f"  Top {speed} players: {len(top)}")
        time.sleep(1)

    # Arena tournament players (all ratings)
    arena = get_arena_players(nb_tournaments=8)
    all_usernames.update(arena)

    print(f"\n  TOTAL unique usernames: {len(all_usernames)}")
    return list(all_usernames)

# ─────────────────────────────────────────────
# GAME FETCHING
# ─────────────────────────────────────────────

def get_user_games(username: str, speed: str, max_games: int = 30) -> list:
    """Fetch games for a user for a specific speed."""
    cache_path = f"{RAW_DIR}/{username}_{speed}.json"
    if os.path.exists(cache_path):
        with open(cache_path, "r") as f:
            return json.load(f)

    url = f"{BASE_URL}/games/user/{username}"
    params = {
        "max": max_games,
        "rated": "true",
        "evals": "true",
        "clocks": "true",
        "opening": "true",       # ← FIXED: get opening data
        "perfType": speed,
        "moves": "true"
    }
    headers = {"Accept": "application/x-ndjson"}

    games = []
    try:
        resp = requests.get(
            url, params=params, headers=headers,
            stream=True, timeout=30
        )
        resp.raise_for_status()

        for line in resp.iter_lines():
            if line:
                try:
                    games.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        resp.close()
        os.makedirs(RAW_DIR, exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(games, f)
        logging.info(f"Fetched {len(games)} {speed} games for {username}")

    except Exception as e:
        logging.error(f"Error for {username} ({speed}): {e}")

    return games

# ─────────────────────────────────────────────
# FEATURE EXTRACTION
# ─────────────────────────────────────────────

def extract_player_row(game: dict, color: str) -> dict | None:
    """Extract one row per player per game."""
    try:
        players = game.get("players", {})
        player = players.get(color, {})
        opponent_color = "black" if color == "white" else "white"
        opponent = players.get(opponent_color, {})

        player_rating = player.get("rating", 0)
        opponent_rating = opponent.get("rating", 0)
        if player_rating == 0 or opponent_rating == 0:
            return None

        # ── ACPL ──
        analysis = player.get("analysis", {})
        if not analysis or "acpl" not in analysis:
            return None

        player_acpl = analysis["acpl"]
        is_suspicious, acpl_gap, expected_acpl = label_suspicious(
            player_acpl, player_rating
        )

        # ── Game result ──
        winner = game.get("winner", None)
        if winner is None:
            result = "draw"
        elif winner == color:
            result = "win"
        else:
            result = "loss"

        # ── Move count ──
        ply = game.get("ply", 0)
        if ply > 0:
            num_moves = ply // 2
        else:
            moves_str = game.get("moves", "")
            num_moves = len(moves_str.split()) // 2 if moves_str else 0

        # ── Clock / timing ──
        clocks = game.get("clocks", [])
        player_clocks = clocks[0::2] if color == "white" else clocks[1::2]
        if len(player_clocks) > 1:
            diffs = []
            for i in range(1, len(player_clocks)):
                d = player_clocks[i - 1] - player_clocks[i]
                if d >= 0:
                    diffs.append(d / 100)
            avg_time = round(sum(diffs) / len(diffs), 2) if diffs else 0
        else:
            avg_time = 0

        # ── Time control ──
        clock_info = game.get("clock", {})
        time_control_seconds = clock_info.get("initial", 0)
        speed = game.get("speed", "unknown")
        time_control = get_time_control_category(speed)

        # ── Opening (FIXED) ──
        opening = game.get("opening", {})
        opening_eco = opening.get("eco", "unknown")
        opening_name = opening.get("name", "Unknown")
        # Opening family = first letter (A, B, C, D, E)
        opening_family = opening_eco[0] if opening_eco and opening_eco != "unknown" else "unknown"

        # ── Performance rating ──
        rating_diff = abs(player_rating - opponent_rating)
        perf_rating = player_rating + (
            400 if result == "win" else -400 if result == "loss" else 0
        )

        return {
            "player_rating":        player_rating,
            "opponent_rating":      opponent_rating,
            "rating_diff":          rating_diff,
            "player_acpl":          player_acpl,
            "expected_acpl":        expected_acpl,
            "acpl_gap":             acpl_gap,
            "num_moves":            num_moves,
            "avg_time_per_move":    avg_time,
            "performance_rating":   perf_rating,
            "time_control_seconds": time_control_seconds,
            "time_control":         time_control,
            "game_result":          result,
            "opening_eco":          opening_eco,
            "opening_family":       opening_family,
            "color_played":         color,
            "is_suspicious":        is_suspicious
        }

    except Exception as e:
        logging.warning(f"Extraction error: {e}")
        return None

# ─────────────────────────────────────────────
# MAIN COLLECTION LOOP
# ─────────────────────────────────────────────

def collect_dataset():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)

    all_rows = []
    checkpoint_path = f"{OUTPUT_DIR}/checkpoint.csv"

    if os.path.exists(checkpoint_path):
        df_existing = pd.read_csv(checkpoint_path)
        all_rows = df_existing.to_dict("records")
        print(f"Resuming from checkpoint: {len(all_rows)} rows already collected")

    usernames = collect_diverse_usernames()

    print(f"\nStarting game collection for {len(usernames)} users...")
    print(f"Speed types: {SPEED_TYPES}")
    print(f"Target: {TARGET_ROWS} rows\n")

    for i, username in enumerate(usernames):
        if len(all_rows) >= TARGET_ROWS:
            print(f"\n✅ Target of {TARGET_ROWS} rows reached!")
            break

        print(f"[{i+1}/{len(usernames)}] {username}...", end=" ")

        rows_before = len(all_rows)

        # Fetch games for EACH speed type
        for speed in SPEED_TYPES:
            games = get_user_games(username, speed, MAX_GAMES_PER_USER)

            for game in games:
                for color in ["white", "black"]:
                    row = extract_player_row(game, color)
                    if row:
                        all_rows.append(row)

            time.sleep(0.5)  # small delay between speed types

        added = len(all_rows) - rows_before
        print(f"+{added} rows (Total: {len(all_rows)})")

        if (i + 1) % 20 == 0:
            df_checkpoint = pd.DataFrame(all_rows)
            df_checkpoint.to_csv(checkpoint_path, index=False)
            print(f"  → Checkpoint saved: {len(all_rows)} rows")

        time.sleep(0.5)

    # ── Final save ──
    df = pd.DataFrame(all_rows)

    # Auto-adjust labels if outside 5-25% range
    if len(df) > 0:
        pct = df["is_suspicious"].mean() * 100
        if pct < 5 or pct > 25:
            print(f"\n⚠️  Suspicious rate ({pct:.1f}%) outside 5-25%. Auto-adjusting...")
            threshold = df["acpl_gap"].quantile(0.12)
            df["is_suspicious"] = (df["acpl_gap"] < threshold).astype(int)

    output_path = f"{OUTPUT_DIR}/dataset.csv"
    df.to_csv(output_path, index=False)

    if len(df) > 0:
        df.sample(min(100, len(df))).to_csv(f"{OUTPUT_DIR}/sample.csv", index=False)

    # ── Summary ──
    print("\n" + "=" * 50)
    print("DATASET COLLECTION COMPLETE")
    print("=" * 50)
    print(f"Total rows:        {len(df)}")
    print(f"Total columns:     {len(df.columns)}")

    if len(df) > 0 and "is_suspicious" in df.columns:
        n_sus = df["is_suspicious"].sum()
        pct_sus = n_sus / len(df) * 100
        print(f"Suspicious games:  {n_sus} ({pct_sus:.1f}%)")
        print(f"Normal games:      {len(df) - n_sus} ({100 - pct_sus:.1f}%)")

        print(f"\n--- Speed Distribution ---")
        print(df["time_control"].value_counts().to_string())

        print(f"\n--- Opening Families ---")
        print(df["opening_family"].value_counts().to_string())

        print(f"\n--- Top 10 Opening ECOs ---")
        print(df["opening_eco"].value_counts().head(10).to_string())

        bins = [0, 1000, 1200, 1400, 1600, 1800, 2000, 4000]
        labels = ["<1000", "1000-1200", "1200-1400", "1400-1600",
                  "1600-1800", "1800-2000", "2000+"]
        df["rating_bin"] = pd.cut(df["player_rating"], bins=bins,
                                   labels=labels, right=False)
        print(f"\n--- Rating Distribution ---")
        print(df["rating_bin"].value_counts().sort_index().to_string())

        print(f"\n--- Suspicious % per Rating ---")
        sus_by = df.groupby("rating_bin", observed=True)["is_suspicious"].mean() * 100
        print(sus_by.round(1).to_string())

        df.drop(columns=["rating_bin"], inplace=True)
    else:
        print("⚠️  No rows collected!")

    print(f"\nSaved to: {output_path}")
    return df

if __name__ == "__main__":
    df = collect_dataset()