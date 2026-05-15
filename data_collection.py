"""
data_collection.py
==================
Collects drug adverse event reports from the openFDA FAERS API
and builds a structured dataset for binary classification:
    seriousnesshospitalization = 1  ->  hospitalization reported
    seriousnesshospitalization = 0  ->  hospitalization not reported

Features extracted (12 total — 7 numeric, 5 categorical):
    patient_age, nb_drugs, nb_reactions,
    worst_reaction_outcome, nb_suspect_drugs,
    patient_sex, reporter_qualification, route_of_admin,
    country, has_black_box_warning, is_concomitant_present

Target variable:
    seriousnesshospitalization  ->  derived from the FDA seriousnesshospitalization flag

Usage:
    python data_collection.py

Output:
    data/dataset.csv   →  full dataset (10 000+ rows)
    data/sample.csv    →  random 100-row extract for quick verification
    data/raw/         →  saved raw JSON batch responses for resume/reuse
    collection.log     →  API call log (timestamp, skip, status)
"""

import json
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
LABEL_BASE_URL = "https://api.fda.gov/drug/label.json"
BATCH_SIZE   = 300    # records per request (max allowed = 1000, keep lower for stability)
TOTAL_TARGET = 10000  # minimum rows we want in the final dataset
SAVE_EVERY   = 1000   # save a partial CSV every N rows (safety checkpoint)
SLEEP_BETWEEN_CALLS = 0.3  # seconds — respects rate limiting (240 req/min with free key)
RAW_DATA_DIR = "data/raw"  # save raw JSON batches so we can resume without re-requesting
LABEL_CACHE_PATH = "data/label_cache.json"
_label_cache: dict[str, int] = {}

# ─────────────────────────────────────────────
# LOGGING SETUP
# ─────────────────────────────────────────────

os.makedirs("data", exist_ok=True)
os.makedirs(RAW_DATA_DIR, exist_ok=True)

logging.basicConfig(
    filename="collection.log",
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s"
)


def load_label_cache() -> None:
    global _label_cache
    if os.path.exists(LABEL_CACHE_PATH):
        try:
            with open(LABEL_CACHE_PATH, "r", encoding="utf-8") as handle:
                _label_cache = json.load(handle)
        except Exception:
            _label_cache = {}
    else:
        _label_cache = {}


def save_label_cache() -> None:
    try:
        with open(LABEL_CACHE_PATH, "w", encoding="utf-8") as handle:
            json.dump(_label_cache, handle, ensure_ascii=False, indent=2)
    except Exception:
        pass


load_label_cache()

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

def raw_batch_path(skip: int) -> str:
    return os.path.join(RAW_DATA_DIR, f"batch_{skip}.json")


def save_raw_batch(skip: int, batch: dict) -> None:
    path = raw_batch_path(skip)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(batch, handle, ensure_ascii=False)


def get_label_query_candidates(primary_drug: dict) -> list[str]:
    candidates = []
    if primary_drug.get("medicinalproduct"):
        candidates.append(primary_drug["medicinalproduct"])

    openfda = primary_drug.get("openfda", {}) or {}
    for field in ("generic_name", "brand_name", "substance_name", "product_type"):
        value = openfda.get(field)
        if isinstance(value, list):
            candidates.extend(value)
        elif isinstance(value, str) and value:
            candidates.append(value)

    return [c.strip() for c in candidates if c and c.strip()]


def query_label_for_drug(drug_name: str) -> dict:
    for field in ("openfda.generic_name", "openfda.brand_name", "openfda.substance_name"):
        try:
            params = {
                "api_key": API_KEY,
                "search": f'{field}:"{drug_name}"',
                "limit": 1
            }
            response = requests.get(LABEL_BASE_URL, params=params, timeout=15)
            logging.info(f"LABEL GET drug={drug_name} field={field} | status={response.status_code} | url={response.url}")
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            if results:
                return results[0]
        except requests.HTTPError:
            continue
        except requests.RequestException:
            continue
    return {}


def has_black_box_warning(label_doc: dict) -> bool:
    if not label_doc:
        return False

    keys_to_check = [
        "black_box_warning",
        "boxed_warning",
        "warnings",
        "warnings_and_precautions",
        "precautions",
        "boxed_warning_and_additional_info"
    ]

    def text_contains_black_box(value: object) -> bool:
        if isinstance(value, str):
            return "black box" in value.lower()
        if isinstance(value, list):
            return any(isinstance(item, str) and "black box" in item.lower() for item in value)
        return False

    for key in keys_to_check:
        if key in label_doc and text_contains_black_box(label_doc[key]):
            return True

    # inspect nested values as a fallback
    for value in label_doc.values():
        if text_contains_black_box(value):
            return True

    return False


def get_drug_name_for_label_query(primary_drug: dict) -> str | None:
    candidates = get_label_query_candidates(primary_drug)
    return candidates[0] if candidates else None


def get_has_black_box_warning(primary_drug: dict) -> int:
    drug_name = get_drug_name_for_label_query(primary_drug)
    if not drug_name:
        return 0

    normalized_name = drug_name.strip().lower()
    if normalized_name in _label_cache:
        return _label_cache[normalized_name]

    label_doc = query_label_for_drug(drug_name)
    flag = 1 if has_black_box_warning(label_doc) else 0
    _label_cache[normalized_name] = flag
    save_label_cache()
    return flag


def load_saved_raw_batches() -> tuple[list[dict], int]:
    saved_batches = []
    for name in os.listdir(RAW_DATA_DIR):
        if name.startswith("batch_") and name.endswith(".json"):
            try:
                skip = int(name[len("batch_"):-5])
                saved_batches.append((skip, name))
            except ValueError:
                continue

    saved_batches.sort()
    rows = []
    highest_skip = -BATCH_SIZE

    for skip, name in saved_batches:
        path = os.path.join(RAW_DATA_DIR, name)
        with open(path, "r", encoding="utf-8") as handle:
            batch = json.load(handle)
        results = batch.get("results", [])
        for report in results:
            rows.append(extract_features(report))
        highest_skip = skip

    next_skip = highest_skip + BATCH_SIZE if highest_skip >= 0 else 0
    if saved_batches:
        print(f"Loaded {len(rows)} rows from {len(saved_batches)} saved raw batches. Resuming at skip={next_skip}.")

    return rows, next_skip


def extract_features(report: dict) -> dict:
    """
    Extract a flat dictionary of features from a single raw FDA report.

    Feature list:
        Numeric (5):
            patient_age             — age of patient at reaction onset (years)
            nb_drugs                — total number of drugs listed in the report
            nb_reactions            — total number of distinct reactions listed
            worst_reaction_outcome  — worst outcome code across all reactions
                                      (1=recovered, 2=recovering, 3=not recovered,
                                       4=recovered with sequelae, 5=fatal, 6=unknown)
            nb_suspect_drugs        — number of drugs flagged as suspected cause

        Categorical (4):
            patient_sex             — 1=male, 2=female, 0=unknown
            reporter_qualification  — who submitted the report:
                                      1=physician, 2=pharmacist,
                                      3=other health professional,
                                      4=lawyer, 5=consumer/patient
            route_of_admin          — how the primary suspect drug was administered
                                      (oral, injection, topical, etc.)
            country                 — ISO country code where the event occurred

        Derived binary features (2):
            has_black_box_warning   — 1 if the suspect drug has an FDA black box warning,
                                      0 otherwise
            is_concomitant_present  — 1 if any concomitant drug is present in the report,
                                      0 otherwise

        Target (1):
            seriousnesshospitalization  -> 1=hospitalization reported,
                                           0=hospitalization not reported
                                           Derived from the FDA seriousnesshospitalization flag.

    Args:
        report: raw dict parsed from one FDA API result entry

    Returns:
        Flat dict with all features + target
    """
    patient   = report.get("patient", {})
    drugs     = patient.get("drug", [])
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

    concomitant_present = 1 if any(
        str(d.get("drugcharacterization", "")).strip() == "2"
        for d in drugs
    ) else 0

    return {
        # ── Numeric features
        "patient_age":            patient.get("patientonsetage"),
        "nb_drugs":               len(drugs),
        "nb_reactions":           len(reactions),
        "worst_reaction_outcome": worst_outcome,
        "nb_suspect_drugs":       nb_suspect,

        # ── Categorical features
        "patient_sex":            patient.get("patientsex"),
        "reporter_qualification": report.get("primarysource", {}).get("qualification"),
        "route_of_admin":         primary_drug.get("drugadministrationroute"),
        "country":                report.get("occurcountry"),

        # ── Derived binary features
        "has_black_box_warning":  get_has_black_box_warning(primary_drug),
        "is_concomitant_present": concomitant_present,

        # ── Target variable: 1 when hospitalization is reported, otherwise 0.
        "seriousnesshospitalization": 1 if str(report.get("seriousnesshospitalization", "")).strip() == "1" else 0
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

    print(f"Starting collection - target: {total} rows")
    print(f"Batch size: {BATCH_SIZE} | Sleep: {SLEEP_BETWEEN_CALLS}s between calls\n")

    rows, skip = load_saved_raw_batches()
    consecutive_errors = 0

    if len(rows) >= total:
        print(f"Already have {len(rows)} saved rows; no API fetch needed.")
        return pd.DataFrame(rows[:total])

    while len(rows) < total:

        try:
            data = fetch_batch(skip)
            save_raw_batch(skip, data)
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
                print(f"\n  Checkpoint saved -> {partial_path}")

            time.sleep(SLEEP_BETWEEN_CALLS)

        except requests.HTTPError as e:
            consecutive_errors += 1
            logging.error(f"HTTP error at skip={skip}: {e}")
            print(f"\n  HTTP error: {e} - waiting 5s before retry...")

            if consecutive_errors >= 5:
                print("  Too many consecutive errors. Stopping.")
                logging.error("Stopped after 5 consecutive HTTP errors.")
                break

            time.sleep(5)

        except requests.ConnectionError as e:
            logging.error(f"Connection error at skip={skip}: {e}")
            print(f"\n  Connection error - waiting 10s before retry...")
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
    print(f"Full dataset saved -> {dataset_path}")

    # ── 2b. Save raw extracted dataset in parquet for faster reloads if supported.
    try:
        parquet_path = "data/dataset.parquet"
        df.to_parquet(parquet_path, index=False)
        print(f"Full dataset also saved -> {parquet_path}")
    except Exception:
        pass

    # ── 3. Save 100-row sample for quick verification (required by project.md)
    sample_path = "data/sample.csv"
    df.sample(n=min(100, len(df)), random_state=42).to_csv(sample_path, index=False)
    print(f"Sample saved        -> {sample_path}")

    # ── 4. Print class distribution (verify the imbalance)
    print("\n-- Target variable distribution --")
    counts = df["seriousnesshospitalization"].value_counts()
    ratios = df["seriousnesshospitalization"].value_counts(normalize=True) * 100
    print(f"  seriousnesshospitalization=1 (hospitalized)     : {counts.get(1, 0):>6}  ({ratios.get(1, 0):.1f}%)")
    print(f"  seriousnesshospitalization=0 (not hospitalized) : {counts.get(0, 0):>6}  ({ratios.get(0, 0):.1f}%)")
    print(f"  null / missing                                  : {df['seriousnesshospitalization'].isna().sum():>6}")

    # ── 5. Print missing value summary
    print("\n-- Missing values per feature --")
    missing = df.isna().sum().sort_values(ascending=False)
    for col, n in missing.items():
        pct = n / len(df) * 100
        print(f"  {col:<30} {n:>6} missing  ({pct:.1f}%)")

    print("\nDone. Check collection.log for the full API call history.")