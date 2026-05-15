"""
data_collection.py
==================
Collects drug adverse event reports from the openFDA FAERS API
and builds a structured dataset for binary classification:
    seriousnessdeath = 1  ->  death reported
    seriousnessdeath = 0  ->  death not reported

Features extracted (11 total — 6 numeric, 5 categorical):
    patient_age, patient_weight, nb_drugs, nb_reactions,
    worst_reaction_outcome, nb_suspect_drugs,
    patient_sex, reporter_qualification, route_of_admin,
    drug_characterization, country

Target variable:
    seriousnessdeath  ->  derived from the FDA seriousnessdeath flag

Usage:
    python data_collection.py

Output:
    data/dataset.csv   →  full dataset (10 000+ rows)
    data/sample.csv    →  random 100-row extract for quick verification
    collection.log     →  API call log (timestamp, skip, status)
"""

import requests
import time
import logging
import os
import pandas as pd

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

API_KEY      = "sfRaT2wpjDi8mHBPnXDhRA4qxSo3yIkkm5bXPWjv"   # get free key at https://open.fda.gov/apis/authentication/
BASE_URL     = "https://api.fda.gov/drug/event.json"
BATCH_SIZE   = 300    # records per request (max allowed = 1000, keep lower for stability)
TOTAL_TARGET = 10000  # minimum rows we want in the final dataset
SAVE_EVERY   = 1000   # save a partial CSV every N rows (safety checkpoint)
SLEEP_BETWEEN_CALLS = 0.3  # seconds — respects rate limiting (240 req/min with free key)

# ─────────────────────────────────────────────
# LOGGING SETUP
# ─────────────────────────────────────────────

os.makedirs("data", exist_ok=True)

logging.basicConfig(
    filename="collection.log",
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s"
)

# ─────────────────────────────────────────────
# API CALL — fetch one batch of reports
# ─────────────────────────────────────────────

def fetch_batch(skip: int) -> dict:
    """
    Call the openFDA API and return a batch of raw adverse event reports.

    Args:
        skip: offset — how many records to skip (used for pagination)

    Returns:
        Parsed JSON dict from the API response

    Raises:
        requests.HTTPError if the server returns a non-200 status
    """
    params = {
        "api_key": API_KEY,
        # "search": "receivedate:[20200101 TO 20221231]",  # only 2020-2022 reports
        "limit":   BATCH_SIZE,
        "skip":    skip
    }

    response = requests.get(BASE_URL, params=params, timeout=15)

    logging.info(
        f"GET skip={skip} | status={response.status_code} | url={response.url}"
    )

    response.raise_for_status()
    return response.json()


# ─────────────────────────────────────────────
# FEATURE EXTRACTION — one report → one flat row
# ─────────────────────────────────────────────

def extract_features(report: dict) -> dict:
    """
    Extract a flat dictionary of features from a single raw FDA report.

    Feature list:
        Numeric (6):
            patient_age             — age of patient at reaction onset (years)
            patient_weight          — patient weight in kg (often null — impute in Phase 2)
            nb_drugs                — total number of drugs listed in the report
            nb_reactions            — total number of distinct reactions listed
            worst_reaction_outcome  — worst outcome code across all reactions
                                      (1=recovered, 2=recovering, 3=not recovered,
                                       4=recovered with sequelae, 5=fatal, 6=unknown)
            nb_suspect_drugs        — number of drugs flagged as suspected cause

        Categorical (5):
            patient_sex             — 1=male, 2=female, 0=unknown
            reporter_qualification  — who submitted the report:
                                      1=physician, 2=pharmacist,
                                      3=other health professional,
                                      4=lawyer, 5=consumer/patient
            route_of_admin          — how the primary suspect drug was administered
                                      (oral, injection, topical, etc.)
            drug_characterization   — role of the primary drug:
                                      1=suspect, 2=concomitant, 3=interacting
            country                 — ISO country code where the event occurred

        Target (1):
            seriousnessdeath        -> 1=death reported,
                                      0=death not reported
                                      Derived from the FDA seriousnessdeath flag.

    Args:
        report: raw dict parsed from one FDA API result entry

    Returns:
        Flat dict with all features + target
    """
    patient  = report.get("patient", {})
    drugs    = patient.get("drug", [])
    reactions = patient.get("reaction", [])

    # ── Number of suspect drugs (characterization = "1")
    nb_suspect = sum(
        1 for d in drugs
        if str(d.get("drugcharacterization", "")).strip() == "1"
    )

    # ── Worst reaction outcome across all reactions in the report
    outcome_values = []
    for r in reactions:
        val = r.get("reactionoutcome")
        if val is not None:
            try:
                outcome_values.append(int(val))
            except ValueError:
                pass
    worst_outcome = max(outcome_values) if outcome_values else None

    # ── Primary drug info (first suspect drug, or first drug if none flagged)
    suspect_drugs = [d for d in drugs if str(d.get("drugcharacterization", "")).strip() == "1"]
    primary_drug  = suspect_drugs[0] if suspect_drugs else (drugs[0] if drugs else {})

    return {
        # ── Numeric features
        "patient_age":            patient.get("patientonsetage"),
        "patient_weight":         patient.get("patientweight"),
        "nb_drugs":               len(drugs),
        "nb_reactions":           len(reactions),
        "worst_reaction_outcome": worst_outcome,
        "nb_suspect_drugs":       nb_suspect,

        # ── Categorical features
        "patient_sex":            patient.get("patientsex"),
        "reporter_qualification": report.get("primarysource", {}).get("qualification"),
        "route_of_admin":         primary_drug.get("drugadministrationroute"),
        "drug_characterization":  primary_drug.get("drugcharacterization"),
        "country":                report.get("occurcountry"),

        # Target variable: 1 when death is reported, otherwise 0.
        "seriousnessdeath":       1 if str(report.get("seriousnessdeath", "")).strip() == "1" else 0
    }


# ─────────────────────────────────────────────
# MAIN COLLECTION LOOP
# ─────────────────────────────────────────────

def collect(total: int = TOTAL_TARGET) -> pd.DataFrame:
    """
    Paginate through the openFDA API and collect `total` adverse event records.

    Handles:
        - Pagination via `skip` parameter
        - Rate limiting via sleep between calls
        - HTTP errors with retry after 5 seconds
        - Partial saves every SAVE_EVERY rows

    Args:
        total: number of rows to collect

    Returns:
        DataFrame with all extracted features
    """
    rows = []
    skip = 0
    consecutive_errors = 0

    print(f"Starting collection — target: {total} rows")
    print(f"Batch size: {BATCH_SIZE} | Sleep: {SLEEP_BETWEEN_CALLS}s between calls\n")

    while len(rows) < total:

        try:
            data = fetch_batch(skip)
            results = data.get("results", [])

            if not results:
                print("No more results returned by the API. Stopping.")
                logging.warning(f"Empty results at skip={skip}. Stopping.")
                break

            for report in results:
                rows.append(extract_features(report))

            skip += BATCH_SIZE
            consecutive_errors = 0  # reset error counter on success

            # ── Progress print
            print(f"  Collected: {len(rows)} rows (skip={skip})", end="\r")

            # ── Partial save checkpoint
            if len(rows) % SAVE_EVERY == 0:
                partial_path = f"data/partial_{len(rows)}.csv"
                pd.DataFrame(rows).to_csv(partial_path, index=False)
                print(f"\n  Checkpoint saved → {partial_path}")

            time.sleep(SLEEP_BETWEEN_CALLS)

        except requests.HTTPError as e:
            consecutive_errors += 1
            logging.error(f"HTTP error at skip={skip}: {e}")
            print(f"\n  HTTP error: {e} — waiting 5s before retry...")

            if consecutive_errors >= 5:
                print("  Too many consecutive errors. Stopping.")
                logging.error("Stopped after 5 consecutive HTTP errors.")
                break

            time.sleep(5)

        except requests.ConnectionError as e:
            logging.error(f"Connection error at skip={skip}: {e}")
            print(f"\n  Connection error — waiting 10s before retry...")
            time.sleep(10)

        except Exception as e:
            logging.error(f"Unexpected error at skip={skip}: {e}")
            print(f"\n  Unexpected error: {e}")
            break

    df = pd.DataFrame(rows)
    print(f"\n\nCollection complete. Shape: {df.shape}")
    return df


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":

    # ── 1. Collect data
    df = collect(total=TOTAL_TARGET)

    # ── 2. Save full dataset
    dataset_path = "data/dataset.csv"
    df.to_csv(dataset_path, index=False)
    print(f"Full dataset saved → {dataset_path}")

    # ── 3. Save 100-row sample for quick verification (required by project.md)
    sample_path = "data/sample.csv"
    df.sample(n=min(100, len(df)), random_state=42).to_csv(sample_path, index=False)
    print(f"Sample saved        → {sample_path}")

    # ── 4. Print class distribution (verify the imbalance)
    print("\n── Target variable distribution ──")
    counts = df["seriousnessdeath"].value_counts()
    ratios = df["seriousnessdeath"].value_counts(normalize=True) * 100
    print(f"  seriousnessdeath=1 (death reported)     : {counts.get(1, 0):>6}  ({ratios.get(1, 0):.1f}%)")
    print(f"  seriousnessdeath=0 (death not reported) : {counts.get(0, 0):>6}  ({ratios.get(0, 0):.1f}%)")
    print(f"  null / missing                          : {df['seriousnessdeath'].isna().sum():>6}")

    # ── 5. Print missing value summary
    print("\n── Missing values per feature ──")
    missing = df.isna().sum().sort_values(ascending=False)
    for col, n in missing.items():
        pct = n / len(df) * 100
        print(f"  {col:<30} {n:>6} missing  ({pct:.1f}%)")

    print("\nDone. Check collection.log for the full API call history.")
