import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import io
import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — must match Phase 2 pipeline exactly
# ---------------------------------------------------------------------------
MODEL_PATH = Path("models/final_model.joblib")

ROUTE_OF_ADMIN_TOP10 = {"001", "002", "003", "004", "005", "007", "008", "011", "055", "065"}
COUNTRY_TOP10 = {"US", "FR", "DE", "GB", "CA", "JP", "AU", "IT", "ES", "BR"}

AGE_BINS = [0, 2, 18, 65, 75, 120]
AGE_LABELS = ["nourrisson", "enfant", "adulte", "senior", "tres_age"]
DEFAULT_THRESHOLD = 0.59

# ---------------------------------------------------------------------------
# Model state (loaded once at startup)
# ---------------------------------------------------------------------------
model_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model once at startup; release on shutdown."""
    logger.info("Loading pipeline from %s ...", MODEL_PATH)
    if not MODEL_PATH.exists():
        logger.error("Model file not found at %s", MODEL_PATH)
        raise RuntimeError(f"Model file not found: {MODEL_PATH}")
    model_content = joblib.load(MODEL_PATH)
    if isinstance(model_content, dict):
        pipeline = model_content["pipeline"]
        # threshold = model_content.get("optimal_threshold", 0.5)
        threshold = 0.59
        metrics = model_content.get("metrics_test", {})
        # Convert numpy types to native python types for JSON serialization
        for k, v in metrics.items():
            if hasattr(v, "item"):
                metrics[k] = v.item()
            elif isinstance(v, dict):
                for k2, v2 in v.items():
                    if hasattr(v2, "item"):
                        v[k2] = v2.item()
        logger.info("Loaded pipeline and threshold (%.4f) from dict.", threshold)
    else:
        pipeline = model_content
        threshold = 0.59
        metrics = {}
        logger.warning("Model is not a dict; using default threshold 0.59.")

    model_state["pipeline"] = pipeline
    model_state["threshold"] = threshold
    model_state["metrics"] = metrics
    model_state["loaded_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    logger.info("Pipeline loaded successfully.")
    yield
    model_state.clear()
    logger.info("Pipeline released.")


# ---------------------------------------------------------------------------
# App definition
# ---------------------------------------------------------------------------
app = FastAPI(
    title="FAERS Hospitalization Prediction API",
    description=(
        "Binary classifier that predicts whether an FDA adverse event report "
        "will result in hospitalization (`seriousnesshospitalization = 1`).\n\n"
        "**Dataset**: openFDA FAERS  |  **Target**: `seriousnesshospitalization`\n\n"
        "Built with scikit-learn + FastAPI for S8 Machine Learning Project."
    ),
    version="1.0.0",
    lifespan=lifespan,
    contact={
        "name": "Project Team",
        "url": "https://github.com/AmineElBiyadi/Machine_Learning_Project",
    },
    openapi_tags=[
        {"name": "Prediction", "description": "Endpoints for categorical risk prediction."},
        {"name": "Model", "description": "Endpoints for model metadata and health."},
        {"name": "General", "description": "General API information."},
    ]
)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class PatientFeatures(BaseModel):
    """
    Input features for a single adverse event report.
    Engineered features (ratio_suspect_drugs, severity_polypharmacy, age_group)
    are computed automatically — do NOT include them in the request.
    """

    patient_age: float = Field(
        ..., ge=0, le=120,
        description="Patient age in years (0–120).",
        examples=[45.0],
    )
    nb_drugs: int = Field(
        ..., ge=1,
        description="Total number of drugs in the report (≥ 1).",
        examples=[3],
    )
    nb_reactions: int = Field(
        ..., ge=1,
        description="Number of adverse reactions reported (≥ 1).",
        examples=[2],
    )
    nb_suspect_drugs: int = Field(
        ..., ge=0,
        description="Number of suspect drugs (0 ≤ nb_suspect_drugs ≤ nb_drugs).",
        examples=[2],
    )
    worst_reaction_outcome: int = Field(
        ..., ge=1, le=6,
        description=(
            "Worst reaction outcome code (FDA scale): "
            "1=Recovered, 2=Recovering, 3=Not recovered, "
            "4=Recovered with sequelae, 5=Fatal, 6=Unknown."
        ),
        examples=[3],
    )
    patient_sex: int = Field(
        ...,
        description="Patient sex: 0=Unknown, 1=Male, 2=Female.",
        examples=[1],
    )
    reporter_qualification: int = Field(
        ...,
        description=(
            "Reporter type: 1=Physician, 2=Pharmacist, 3=Other health professional, "
            "4=Lawyer, 5=Consumer/non-health professional."
        ),
        examples=[1],
    )
    has_black_box_warning: int = Field(
        ...,
        description="Whether any suspect drug carries an FDA black-box warning: 0=No, 1=Yes.",
        examples=[1],
    )
    is_concomitant_present: int = Field(
        ...,
        description="Whether concomitant drugs are present in the report: 0=No, 1=Yes.",
        examples=[0],
    )
    route_of_admin: str = Field(
        ...,
        description=(
            "FDA route-of-administration code. Top-10 values are used as-is; "
            "all others are grouped as 'other'. "
            "Examples: '001' (Oral), '002' (Intravenous), '003' (Intramuscular)."
        ),
        examples=["001"],
    )
    country: str = Field(
        ...,
        description=(
            "ISO 2-letter country code of the reporter. Top-10 values are used as-is; "
            "all others are grouped as 'other'. "
            "Examples: 'US', 'FR', 'DE', 'GB'."
        ),
        examples=["US"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "patient_age": 65.0,
                "nb_drugs": 5,
                "nb_reactions": 2,
                "nb_suspect_drugs": 2,
                "worst_reaction_outcome": 3,
                "patient_sex": 1,
                "reporter_qualification": 1,
                "has_black_box_warning": 1,
                "is_concomitant_present": 0,
                "route_of_admin": "001",
                "country": "US"
            }
        }
    }

    @field_validator("patient_sex")
    @classmethod
    def validate_sex(cls, v):
        if v not in {0, 1, 2}:
            raise ValueError("patient_sex must be 0 (Unknown), 1 (Male), or 2 (Female).")
        return v

    @field_validator("reporter_qualification")
    @classmethod
    def validate_reporter(cls, v):
        if v not in {1, 2, 3, 4, 5}:
            raise ValueError("reporter_qualification must be between 1 and 5.")
        return v

    @field_validator("has_black_box_warning", "is_concomitant_present")
    @classmethod
    def validate_binary(cls, v):
        if v not in {0, 1}:
            raise ValueError("Binary fields must be 0 or 1.")
        return v

    @model_validator(mode="after")
    def validate_suspect_vs_total(self):
        if self.nb_suspect_drugs > self.nb_drugs:
            raise ValueError("nb_suspect_drugs cannot exceed nb_drugs.")
        return self


class PredictionResponse(BaseModel):
    label: int = Field(..., description="Predicted class: 1=Hospitalization likely, 0=Not likely.")
    probability: float = Field(..., description="Probability of hospitalization (0.0–1.0).")
    risk_level: str = Field(..., description="Human-readable risk: 'high risk' or 'low risk'.")


class BatchRequest(BaseModel):
    records: list[PatientFeatures] = Field(
        ..., min_length=1, max_length=1000,
        description="List of patient feature records (1–1000).",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "records": [
                    {
                        "patient_age": 45.0,
                        "nb_drugs": 3,
                        "nb_reactions": 1,
                        "nb_suspect_drugs": 1,
                        "worst_reaction_outcome": 1,
                        "patient_sex": 2,
                        "reporter_qualification": 5,
                        "has_black_box_warning": 0,
                        "is_concomitant_present": 0,
                        "route_of_admin": "001",
                        "country": "FR"
                    },
                    {
                        "patient_age": 78.0,
                        "nb_drugs": 12,
                        "nb_reactions": 4,
                        "nb_suspect_drugs": 3,
                        "worst_reaction_outcome": 4,
                        "patient_sex": 1,
                        "reporter_qualification": 1,
                        "has_black_box_warning": 1,
                        "is_concomitant_present": 1,
                        "route_of_admin": "002",
                        "country": "US"
                    }
                ]
            }
        }
    }


class BatchPredictionResponse(BaseModel):
    count: int
    predictions: list[PredictionResponse]


class ModelInfo(BaseModel):
    name: str
    version: str
    target: str
    n_features: int
    feature_names: list[str]
    threshold: float
    metrics: dict
    loaded_at: str


# ---------------------------------------------------------------------------
# Feature engineering helpers (must mirror Phase 2 logic exactly)
# ---------------------------------------------------------------------------

def engineer_features(data: dict) -> dict:
    """Compute the 3 engineered features from raw inputs."""
    nb_drugs = data["nb_drugs"]
    nb_suspect_drugs = data["nb_suspect_drugs"]
    worst_outcome = data["worst_reaction_outcome"]
    patient_age = data["patient_age"]

    # Feature 1 : ratio_suspect_drugs = nb_suspect_drugs / nb_drugs
    # Protect against division by zero
    data["ratio_suspect_drugs"] = nb_suspect_drugs / nb_drugs if nb_drugs > 0 else 0

    # Feature 2 : age_group (binning patient_age)
    data["age_group"] = pd.cut(
        [patient_age], bins=AGE_BINS, labels=AGE_LABELS, right=True
    )[0]

    # Feature 3 : severity_polypharmacy = (7 - worst_reaction_outcome) x nb_drugs
    # Note: Training used (7 - worst_outcome) * nb_drugs
    data["severity_polypharmacy"] = (7 - worst_outcome) * nb_drugs

    # Normalize route_of_admin and country to 'other' if not in top-10
    if data["route_of_admin"] not in ROUTE_OF_ADMIN_TOP10:
        data["route_of_admin"] = "other"
    if data["country"] not in COUNTRY_TOP10:
        data["country"] = "other"

    return data


FEATURE_ORDER = [
    "patient_age", "nb_drugs", "nb_reactions", "nb_suspect_drugs",
    "ratio_suspect_drugs", "severity_polypharmacy",
    "worst_reaction_outcome", "patient_sex", "reporter_qualification",
    "has_black_box_warning", "is_concomitant_present",
    "route_of_admin", "country", "age_group",
]


def to_dataframe(features: PatientFeatures) -> pd.DataFrame:
    data = engineer_features(features.model_dump())
    return pd.DataFrame([data])[FEATURE_ORDER]


# ---------------------------------------------------------------------------
# Middleware — request logging
# ---------------------------------------------------------------------------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    logger.info(
        "method=%s path=%s status=%d duration=%.1fms",
        request.method, request.url.path, response.status_code, duration_ms,
    )
    return response


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get(
    "/",
    summary="Welcome",
    tags=["General"],
    response_description="API welcome message and documentation link.",
)
def root():
    """Root endpoint — confirms the API is running and links to the docs."""
    return {
        "status": "online",
        "app_name": "FAERS Hospitalization Prediction API",
        "version": "1.0.0",
        "description": "Binary classifier for Predicting hospitalization from FDA adverse event reports.",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "model_info": "/model/info",
            "predict": "/predict",
            "predict_batch": "/predict/batch",
            "predict_csv": "/predict/csv"
        },
        "author": "Project Team",
        "repository": "https://github.com/AmineElBiyadi/Machine_Learning_Project"
    }


@app.get(
    "/health",
    summary="Health check",
    tags=["General"],
    response_description="API and model status.",
)
def health():
    """
    Returns the operational status of the API.
    - **status**: 'ok' if the model is loaded and ready.
    - **model_loaded**: boolean flag.
    """
    loaded = "pipeline" in model_state
    return {
        "status": "ok" if loaded else "degraded",
        "model_loaded": loaded,
    }


@app.get(
    "/model/info",
    summary="Model metadata",
    tags=["Model"],
    response_model=ModelInfo,
    response_description="Information about the loaded model and its features.",
)
def model_info():
    """
    Returns metadata about the loaded pipeline:
    - Feature names and count
    - Target variable
    - Model load timestamp
    """
    if "pipeline" not in model_state:
        raise HTTPException(status_code=503, detail="Model not loaded.")
    return ModelInfo(
        name="FAERS Hospitalization Classifier",
        version="1.0.0",
        target="seriousnesshospitalization",
        n_features=len(FEATURE_ORDER),
        feature_names=FEATURE_ORDER,
        threshold=model_state["threshold"],
        metrics=model_state["metrics"],
        loaded_at=model_state["loaded_at"],
    )


@app.post(
    "/predict",
    summary="Single prediction",
    tags=["Prediction"],
    response_model=PredictionResponse,
    response_description="Hospitalization risk prediction for one patient report.",
    responses={
        400: {"description": "Validation error in input data."},
        500: {"description": "Internal server error during prediction."},
    },
)
def predict(features: PatientFeatures):
    """
    Predict hospitalization risk for a **single** adverse event report.

    - Engineered features (`ratio_suspect_drugs`, `severity_polypharmacy`, `age_group`)
      are computed automatically from your raw inputs.
    - Returns a binary label, probability, and human-readable risk level.

    **Example request body:**
    ```json
    {
      "patient_age": 67,
      "nb_drugs": 4,
      "nb_reactions": 2,
      "nb_suspect_drugs": 2,
      "worst_reaction_outcome": 4,
      "patient_sex": 1,
      "reporter_qualification": 1,
      "has_black_box_warning": 1,
      "is_concomitant_present": 1,
      "route_of_admin": "001",
      "country": "US"
    }
    ```
    """
    if "pipeline" not in model_state:
        raise HTTPException(status_code=503, detail="Model not loaded.")
    try:
        df = to_dataframe(features)
        pipeline = model_state["pipeline"]
        threshold = model_state.get("threshold", DEFAULT_THRESHOLD)
        
        proba = float(pipeline.predict_proba(df)[0][1])
        label = 1 if proba >= threshold else 0
        risk = "high risk" if label == 1 else "low risk"
        logger.info("predict | label=%d proba=%.4f (threshold=%.4f)", label, proba, threshold)
        return PredictionResponse(label=label, probability=round(proba, 4), risk_level=risk)
    except Exception as exc:
        logger.error("Prediction error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}")


@app.post(
    "/predict/batch",
    summary="Batch prediction",
    tags=["Prediction"],
    response_model=BatchPredictionResponse,
    response_description="Hospitalization risk predictions for multiple reports.",
    responses={
        400: {"description": "Validation error in one or more records."},
        500: {"description": "Internal server error during batch prediction."},
    },
)
def predict_batch(batch: BatchRequest):
    """
    Predict hospitalization risk for a **batch** of adverse event reports (up to 1000).

    Send a JSON body with a `records` array, where each element has the same
    fields as the `/predict` endpoint.

    Returns predictions in the same order as the input records.
    """
    if "pipeline" not in model_state:
        raise HTTPException(status_code=503, detail="Model not loaded.")
    try:
        pipeline = model_state["pipeline"]
        threshold = model_state.get("threshold", DEFAULT_THRESHOLD)
        
        rows = [engineer_features(r.model_dump()) for r in batch.records]
        df = pd.DataFrame(rows)[FEATURE_ORDER]
        
        probas = pipeline.predict_proba(df)[:, 1].tolist()
        labels = [1 if p >= threshold else 0 for p in probas]
        
        predictions = [
            PredictionResponse(
                label=int(lbl),
                probability=round(float(prob), 4),
                risk_level="high risk" if lbl == 1 else "low risk",
            )
            for lbl, prob in zip(labels, probas)
        ]
        logger.info("predict/batch | count=%d", len(predictions))
        return BatchPredictionResponse(count=len(predictions), predictions=predictions)
    except Exception as exc:
        logger.error("Batch prediction error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Batch prediction failed: {exc}")
@app.post(
    "/predict/csv",
    summary="CSV Batch prediction",
    tags=["Prediction"],
    response_description="CSV file with an added 'prediction_hospitalization' column.",
    responses={
        400: {"description": "Upload error or invalid CSV format."},
        500: {"description": "Processing error during prediction."},
    },
)
async def predict_csv(file: UploadFile = File(...)):
    """
    Predict hospitalization risk for a batch of reports provided in a CSV file.

    - Upload a CSV file matching the schema of `PatientFeatures`.
    - Returns the same CSV with a new `prediction_hospitalization` column.
    """
    if "pipeline" not in model_state:
        raise HTTPException(status_code=503, detail="Model not loaded.")

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    try:
        # Read CSV directly from bitstream
        contents = await file.read()
        df_input = pd.read_csv(io.BytesIO(contents))

        # Validate required columns
        required_cols = [
            "patient_age", "nb_drugs", "nb_reactions", "nb_suspect_drugs",
            "worst_reaction_outcome", "patient_sex", "reporter_qualification",
            "has_black_box_warning", "is_concomitant_present",
            "route_of_admin", "country"
        ]
        missing = [c for c in required_cols if c not in df_input.columns]
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing columns in CSV: {missing}")

        # Process each row (feature engineering + inference)
        pipeline = model_state["pipeline"]
        threshold = model_state.get("threshold", DEFAULT_THRESHOLD)
        
        # Apply engineer_features to each row
        # Note: we convert to dict first to reuse the helper
        processed_rows = [engineer_features(row) for row in df_input.to_dict("records")]
        df_inference = pd.DataFrame(processed_rows)[FEATURE_ORDER]
        
        # Prediction
        probas = pipeline.predict_proba(df_inference)[:, 1]
        predictions = (probas >= threshold).astype(int)
        
        # Add predictions back to the ORIGINAL dataframe
        df_input["prediction_hospitalization"] = predictions
        
        # Convert back to bitstream for streaming response
        output = io.StringIO()
        df_input.to_csv(output, index=False)
        output.seek(0)
        
        filename = f"predictions_{int(time.time())}.csv"
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("CSV processing error: %s", exc)
        raise HTTPException(status_code=500, detail=f"CSV processing failed: {exc}")
