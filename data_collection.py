"""
data_collection.py
==================
Collects drug adverse event reports from the openFDA FAERS API
and builds a structured dataset for binary classification:
    seriousnesshospitalization = 1  →  hospitalization reported
    seriousnesshospitalization = 0  →  hospitalization not reported

Features extracted (12 total — 7 numeric, 5 categorical):
    patient_age, nb_drugs, nb_reactions,
    worst_reaction_outcome, nb_suspect_drugs,
    patient_sex, reporter_qualification, route_of_admin,
    country, has_black_box_warning, is_concomitant_present

Target variable:
    seriousnesshospitalization  →  derived from the FDA seriousnesshospitalization flag

──────────────────────────────────────────────────────────────────
TWO-PHASE ARCHITECTURE  (fixes slowness + all-zero black-box bug)
──────────────────────────────────────────────────────────────────

  PHASE 1 — fast FAERS collection
      • Paginate the drug/event endpoint with no label queries at all.
      • Extract all features except has_black_box_warning (set to 0).
      • Build a map  drug_key → [row_indices]  while iterating.
      • Save  data/dataset_raw.csv  as a resumable checkpoint.

  PHASE 2 — targeted label enrichment
      • Collect the set of UNIQUE drug keys from the map.
      • Query the drug/label endpoint ONCE per unique drug (not once per row).
      • Detect a black-box warning by checking the presence and content of the
        dedicated  boxed_warning  field — NOT by grepping for "black box" text
        (the previous approach missed every single one).
      • Flip has_black_box_warning from 0 → 1 for every row that belongs to a
        drug confirmed to carry a boxed warning.
      • Save  data/dataset.csv  and  data/sample.csv.

Result: Phase 1 runs in minutes (same speed as before the label feature was added).
        Phase 2 fires O(unique_drugs) label calls instead of O(total_rows) calls.

Usage:
    python data_collection.py

Output:
    data/dataset_raw.csv      →  Phase-1 result (no black-box column yet)
    data/dataset.csv          →  final enriched dataset (≥ 10 000 rows)
    data/sample.csv           →  random 100-row extract for quick verification
    data/raw/                 →  raw JSON batch responses (resume support)
    data/label_cache.json     →  drug → has_black_box cache (survives restarts)
    collection.log            →  API call log (timestamp, endpoint, status)
"""

import json
import logging
import os
import re
import time
from collections import defaultdict

import pandas as pd
import requests

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

API_KEY            = "sfRaT2wpjDi8mHBPnXDhRA4qxSo3yIkkm5bXPWjv"
BASE_URL           = "https://api.fda.gov/drug/event.json"
LABEL_URL          = "https://api.fda.gov/drug/label.json"

BATCH_SIZE         = 300      # records per FAERS request (max 1 000 — keep lower)
TOTAL_TARGET       = 10_000   # minimum rows we want in the final dataset
SAVE_EVERY         = 1_000    # checkpoint: save partial CSV every N rows
SLEEP_FAERS        = 0.25     # seconds between FAERS calls  (240 req/min with key)
SLEEP_LABEL        = 0.25     # seconds between label calls  (same quota)

RAW_DATA_DIR       = "data/raw"
RAW_CSV_PATH       = "data/dataset_raw.csv"
LABEL_CACHE_PATH   = "data/label_cache.json"

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────

os.makedirs("data", exist_ok=True)
os.makedirs(RAW_DATA_DIR, exist_ok=True)

logging.basicConfig(
    filename="collection.log",
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
)

# ─────────────────────────────────────────────────────────────────────────────
# LABEL CACHE  (drug_key → 0 or 1, persisted to disk)
# ─────────────────────────────────────────────────────────────────────────────

def load_label_cache() -> dict:
    if os.path.exists(LABEL_CACHE_PATH):
        try:
            with open(LABEL_CACHE_PATH, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            pass
    return {}


def save_label_cache(cache: dict) -> None:
    try:
        with open(LABEL_CACHE_PATH, "w", encoding="utf-8") as fh:
            json.dump(cache, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def normalize_drug_name(raw: str) -> str:
    """
    Strip dosage suffixes and punctuation so 'METFORMIN HCL 500MG TABLET'
    becomes 'METFORMIN HCL' — a much better label-API search key.
    """
    name = raw.strip().upper()
    # drop anything after  -  /  (  )
    name = re.split(r"[\-\/\(\)]", name)[0].strip()
    # drop dosage patterns like  500MG  10ML  50MCG
    name = re.sub(r"\b\d+\s*(MG|ML|MCG|G|UNITS?|%)\b", "", name, flags=re.I).strip()
    # collapse whitespace
    return re.sub(r"\s+", " ", name)


def best_key_for_drug(drug: dict) -> str | None:
    """
    Return the best normalized name for a single drug entry.
    Priority: openfda.generic_name > openfda.brand_name > medicinalproduct.
    Returns None when no usable name is found.
    """
    openfda = drug.get("openfda") or {}
    for field in ("generic_name", "brand_name", "substance_name"):
        values = openfda.get(field)
        if isinstance(values, list) and values:
            return normalize_drug_name(values[0])
        if isinstance(values, str) and values.strip():
            return normalize_drug_name(values)
    raw = drug.get("medicinalproduct", "")
    if raw and raw.strip():
        return normalize_drug_name(raw)
    return None


def drug_keys_from_report(drugs: list) -> list[str]:
    """
    Return normalized name keys for ALL suspect drugs in a report
    (characterization == "1").  Falls back to all drugs when none are
    flagged as suspect.

    Returning a LIST instead of a single key means Phase 2 checks every
    suspect drug for a black-box warning, not just the first one.
    Duplicate and empty keys are removed.
    """
    suspect = [d for d in drugs if str(d.get("drugcharacterization", "")).strip() == "1"]
    candidates = suspect if suspect else drugs
    keys = []
    for d in candidates:
        k = best_key_for_drug(d)
        if k and k not in keys:
            keys.append(k)
    return keys


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1 — FAERS collection (no label calls)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_faers_batch(skip: int) -> dict:
    """GET one page of FAERS adverse-event reports."""
    params = {"api_key": API_KEY, "limit": BATCH_SIZE, "skip": skip}
    resp = requests.get(BASE_URL, params=params, timeout=15)
    logging.info(f"FAERS  skip={skip}  status={resp.status_code}")
    resp.raise_for_status()
    return resp.json()


def raw_batch_path(skip: int) -> str:
    return os.path.join(RAW_DATA_DIR, f"batch_{skip}.json")


def extract_features_phase1(report: dict) -> dict:
    """
    Extract all features from one raw FDA report.
    has_black_box_warning is set to 0 here; Phase 2 will update it.

    Returns a flat dict PLUS a special key '_drug_key' used to build the
    drug→rows map (stripped before saving to the final DataFrame).
    """
    patient   = report.get("patient", {}) or {}
    drugs     = patient.get("drug", []) or []
    reactions = patient.get("reaction", []) or []

    nb_suspect = sum(
        1 for d in drugs
        if str(d.get("drugcharacterization", "")).strip() == "1"
    )

    outcomes = []
    for r in reactions:
        v = r.get("reactionoutcome")
        if v is not None:
            try:
                outcomes.append(int(v))
            except ValueError:
                pass

    concomitant = int(
        any(str(d.get("drugcharacterization", "")).strip() == "2" for d in drugs)
    )

    suspect_drugs = [d for d in drugs if str(d.get("drugcharacterization", "")).strip() == "1"]
    primary = suspect_drugs[0] if suspect_drugs else (drugs[0] if drugs else {})

    return {
        # numeric
        "patient_age":            patient.get("patientonsetage"),
        "nb_drugs":               len(drugs),
        "nb_reactions":           len(reactions),
        "worst_reaction_outcome": max(outcomes) if outcomes else None,
        "nb_suspect_drugs":       nb_suspect,
        # categorical
        "patient_sex":            patient.get("patientsex"),
        "reporter_qualification": (report.get("primarysource") or {}).get("qualification"),
        "route_of_admin":         primary.get("drugadministrationroute"),
        "country":                report.get("occurcountry"),
        # derived binary (Phase 2 will fix this)
        "has_black_box_warning":  0,
        "is_concomitant_present": concomitant,
        # target
        "seriousnesshospitalization": (
            1 if str(report.get("seriousnesshospitalization", "")).strip() == "1" else 0
        ),
        # internal key list for Phase 2 (dropped before final save)
        # stored as a pipe-separated string so it survives CSV round-trips
        "_drug_keys": "|".join(drug_keys_from_report(drugs)),
    }


def load_saved_raw_batches() -> tuple[list[dict], int]:
    """Re-hydrate rows from previously saved JSON batches (resume support)."""
    saved = sorted(
        (int(n[6:-5]), n)
        for n in os.listdir(RAW_DATA_DIR)
        if n.startswith("batch_") and n.endswith(".json") and n[6:-5].isdigit()
    )
    rows = []
    highest_skip = -BATCH_SIZE
    for skip, name in saved:
        path = os.path.join(RAW_DATA_DIR, name)
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        for report in data.get("results", []):
            rows.append(extract_features_phase1(report))
        highest_skip = skip
    if saved:
        next_skip = highest_skip + BATCH_SIZE
        print(f"  Resumed: loaded {len(rows)} rows from {len(saved)} saved batches. Next skip={next_skip}.")
        return rows, next_skip
    return rows, 0


def run_phase1(total: int = TOTAL_TARGET) -> pd.DataFrame:
    """
    Phase 1 — pure FAERS collection.
    Returns a DataFrame that includes '_drug_key' (still present for Phase 2).
    """
    print("\n══════════════════════════════════════════════")
    print("  PHASE 1 — Collecting FAERS adverse events")
    print("══════════════════════════════════════════════")

    rows, skip = load_saved_raw_batches()

    if len(rows) >= total:
        print(f"  Already have {len(rows)} rows — skipping API calls.")
        return pd.DataFrame(rows)

    consecutive_errors = 0

    while len(rows) < total:
        try:
            data = fetch_faers_batch(skip)

            # save raw batch for resume support
            with open(raw_batch_path(skip), "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False)

            results = data.get("results", [])
            if not results:
                print("\n  API returned no more results. Stopping.")
                logging.warning(f"Empty results at skip={skip}.")
                break

            for report in results:
                rows.append(extract_features_phase1(report))

            skip += BATCH_SIZE
            consecutive_errors = 0
            print(f"  Rows collected: {len(rows):>6}  (next skip={skip})", end="\r")

            if len(rows) % SAVE_EVERY == 0:
                chk = f"data/checkpoint_{len(rows)}.csv"
                pd.DataFrame(rows).to_csv(chk, index=False)
                print(f"\n  Checkpoint → {chk}")

            time.sleep(SLEEP_FAERS)

        except requests.HTTPError as exc:
            consecutive_errors += 1
            logging.error(f"FAERS HTTP error skip={skip}: {exc}")
            print(f"\n  HTTP error: {exc} — waiting 5s…")
            if consecutive_errors >= 5:
                logging.error("Stopped after 5 consecutive HTTP errors.")
                break
            time.sleep(5)

        except requests.ConnectionError as exc:
            logging.error(f"Connection error skip={skip}: {exc}")
            print(f"\n  Connection error — waiting 10s…")
            time.sleep(10)

        except Exception as exc:
            logging.error(f"Unexpected error skip={skip}: {exc}")
            print(f"\n  Unexpected error: {exc}")
            break

    df = pd.DataFrame(rows)
    print(f"\n  Phase 1 done — shape: {df.shape}")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2 — black-box warning enrichment
# ─────────────────────────────────────────────────────────────────────────────

def fetch_label_doc(drug_key: str) -> dict:
    """
    Query the FDA drug/label endpoint for a single drug name.
    Tries openfda.generic_name first, then openfda.brand_name.
    Returns the first label document found, or {} on failure.
    """
    search_fields = ("openfda.generic_name", "openfda.brand_name", "generic_name", "brand_name")
    for field in search_fields:
        try:
            params = {
                "api_key": API_KEY,
                "search": f'{field}:"{drug_key}"',
                "limit": 1,
            }
            resp = requests.get(LABEL_URL, params=params, timeout=15)
            logging.info(f"LABEL  drug={drug_key}  field={field}  status={resp.status_code}")
            if resp.status_code == 404:
                continue          # not found with this field — try next
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if results:
                return results[0]
        except requests.HTTPError:
            continue
        except requests.RequestException as exc:
            logging.warning(f"LABEL request error drug={drug_key}: {exc}")
            break
    return {}


def label_has_boxed_warning(label_doc: dict) -> bool:
    """
    Determine whether a label document carries a black-box (boxed) warning.

    CORRECT approach: check the DEDICATED 'boxed_warning' field.
    A non-empty boxed_warning field IS the black-box warning — do not
    grep for the literal string "black box" inside generic text fields,
    which is why the previous implementation returned 0 for everything.

    Also falls back to checking openfda.has_black_box_warning if present.
    """
    if not label_doc:
        return False

    # ── Primary signal: dedicated field (present and non-empty = black box warning)
    bw = label_doc.get("boxed_warning")
    if bw:
        if isinstance(bw, list) and any(isinstance(s, str) and s.strip() for s in bw):
            return True
        if isinstance(bw, str) and bw.strip():
            return True

    # ── Secondary signal: openfda metadata flag
    openfda = label_doc.get("openfda") or {}
    hbbw = openfda.get("has_black_box_warning")
    if hbbw:
        if isinstance(hbbw, list) and any(str(v).upper() == "YES" for v in hbbw):
            return True
        if isinstance(hbbw, str) and hbbw.upper() == "YES":
            return True

    # ── Tertiary fallback: black_box_warning field (older label format)
    bb = label_doc.get("black_box_warning")
    if bb:
        if isinstance(bb, list) and any(isinstance(s, str) and s.strip() for s in bb):
            return True
        if isinstance(bb, str) and bb.strip():
            return True

    return False


def run_phase2(df: pd.DataFrame) -> pd.DataFrame:
    """
    Phase 2 — enrich has_black_box_warning by querying the label API
    once per unique drug key, then back-filling all matching rows.

    OR logic: a row gets has_black_box_warning = 1 if ANY of its suspect
    drugs carries a boxed warning.  This correctly handles multi-drug reports
    instead of only checking the first drug.

    Steps:
        1. Parse '_drug_keys' (pipe-separated) into a list per row.
        2. Build drug_key -> [row_indices] map across ALL keys in ALL rows.
        3. For each unique drug key not yet cached, query the label API.
        4. Flag every row where at least one drug resolved to 1.
        5. Return the enriched DataFrame (without the _drug_keys column).
    """
    print("\n══════════════════════════════════════════════")
    print("  PHASE 2 — Black-box warning enrichment")
    print("══════════════════════════════════════════════")

    label_cache = load_label_cache()

    # ── Build drug_key -> row indices map (one row contributes MULTIPLE keys)
    drug_to_rows: dict[str, list[int]] = defaultdict(list)
    for idx, row in df.iterrows():
        raw = row.get("_drug_keys", "")
        if not isinstance(raw, str) or not raw.strip():
            continue
        for key in raw.split("|"):
            key = key.strip()
            if key:
                drug_to_rows[key].append(idx)

    unique_drugs = list(drug_to_rows.keys())
    print(f"  Unique drug keys : {len(unique_drugs)}  (across {len(df)} rows)")

    # ── Query label API for drugs not yet in cache
    not_cached = [d for d in unique_drugs if d not in label_cache]
    print(f"  Already cached   : {len(unique_drugs) - len(not_cached)}")
    print(f"  Need label query : {len(not_cached)}")

    for i, drug_key in enumerate(not_cached, 1):
        label_doc = fetch_label_doc(drug_key)
        label_cache[drug_key] = 1 if label_has_boxed_warning(label_doc) else 0
        if i % 50 == 0:
            save_label_cache(label_cache)
            print(f"  Label queries: {i}/{len(not_cached)}  (cache saved)", end="\r")
        else:
            print(f"  Label queries: {i}/{len(not_cached)}", end="\r")
        time.sleep(SLEEP_LABEL)

    save_label_cache(label_cache)
    print(f"\n  Label cache saved -> {LABEL_CACHE_PATH}")

    # ── Back-fill: flag every row where ANY of its drugs has a black-box warning
    flagged_rows: set[int] = set()
    for drug_key, row_indices in drug_to_rows.items():
        if label_cache.get(drug_key, 0) == 1:
            flagged_rows.update(row_indices)

    df.loc[list(flagged_rows), "has_black_box_warning"] = 1

    bbw_count = int(df["has_black_box_warning"].sum())
    bbw_pct   = bbw_count / len(df) * 100
    print(f"  Rows with has_black_box_warning=1 : {bbw_count} ({bbw_pct:.1f}%)")

    # ── Drop internal helper column before returning
    df = df.drop(columns=["_drug_keys"], errors="ignore")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # ── PHASE 1: collect FAERS events (fast — no label calls)
    df_raw = run_phase1(total=TOTAL_TARGET)

    # Save the Phase-1 raw result as a resumable checkpoint
    df_raw.to_csv(RAW_CSV_PATH, index=False)
    print(f"\n  Raw dataset saved → {RAW_CSV_PATH}")

    # ── PHASE 2: enrich has_black_box_warning (targeted label queries)
    df = run_phase2(df_raw)

    # ── Save full enriched dataset
    dataset_csv_path = "data/dataset.csv"
    df.to_csv(dataset_csv_path, index=False)
    print(f"\n  Full dataset saved → {dataset_csv_path}")


    # ── Save 100-row sample
    sample_path = "data/sample.csv"
    df.sample(n=min(100, len(df)), random_state=42).to_csv(sample_path, index=False)
    print(f"  Sample saved       → {sample_path}")

    # ── Class distribution
    print("\n── Target variable distribution ─────────────────────")
    counts = df["seriousnesshospitalization"].value_counts()
    ratios = df["seriousnesshospitalization"].value_counts(normalize=True) * 100
    print(f"  hospitalized     (1): {counts.get(1, 0):>6}  ({ratios.get(1, 0):.1f}%)")
    print(f"  not hospitalized (0): {counts.get(0, 0):>6}  ({ratios.get(0, 0):.1f}%)")
    print(f"  missing              : {df['seriousnesshospitalization'].isna().sum():>6}")

    # ── Missing values
    print("\n── Missing values per feature ───────────────────────")
    for col, n in df.isna().sum().sort_values(ascending=False).items():
        print(f"  {col:<30} {n:>6}  ({n / len(df) * 100:.1f}%)")

    print("\nDone. See collection.log for full API call history.")