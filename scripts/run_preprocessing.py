import os
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
import joblib

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "dataset.csv"
CLEAN_PATH = BASE_DIR / "data" / "dataset_cleaned.csv"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
MODELS_DIR = BASE_DIR / "models"

# Ensure directories exist
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# 1. Load data
print("Chargement des données...")
df = pd.read_csv(DATA_PATH, dtype={"route_of_admin": "string"})
df["route_of_admin"] = df["route_of_admin"].apply(
    lambda x: str(int(float(x))).zfill(3) if pd.notna(x) else pd.NA
)

target_col = "seriousnesshospitalization"

# 2. Cleaning
print("Nettoyage des données...")
# Remove duplicates
df = df.drop_duplicates().copy()

# Correct age
def correct_age(value):
    if pd.isna(value): return np.nan
    if value > 120:
        converted = value / 365.25
        return round(converted, 2) if 0 <= converted <= 120 else np.nan
    if value < 0: return np.nan
    return value

df["patient_age"] = df["patient_age"].apply(correct_age)

# Impute missing values (simple strategy for initial cleaning)
df["patient_age"] = df["patient_age"].fillna(df["patient_age"].median())
df["worst_reaction_outcome"] = df["worst_reaction_outcome"].fillna(df["worst_reaction_outcome"].mode()[0])
df["route_of_admin"] = df["route_of_admin"].fillna(df["route_of_admin"].mode()[0])
df["country"] = df["country"].fillna(df["country"].mode()[0])
df["reporter_qualification"] = df["reporter_qualification"].fillna(df["reporter_qualification"].mode()[0])
df["patient_sex"] = df["patient_sex"].fillna(df["patient_sex"].mode()[0])

# Final duplicate drop post-imputation
df = df.drop_duplicates().copy()
# df.to_csv(CLEAN_PATH, index=False)

# 3. Feature Engineering
print("Feature engineering...")
def create_features(df_in):
    df_out = df_in.copy()
    bins = [0, 18, 65, 120]
    labels = ['Enfant', 'Adulte', 'Senior']
    df_out['age_group'] = pd.cut(df_out['patient_age'], bins=bins, labels=labels, include_lowest=True)
    df_out['polypharmacy'] = (df_out['nb_drugs'] > 5).astype(int)
    return df_out

df = create_features(df)

# 4. Pipeline Definition
print("Définition du pipeline...")
num_features = ["patient_age", "nb_drugs", "nb_reactions", "worst_reaction_outcome", "nb_suspect_drugs"]
cat_features = ["patient_sex", "reporter_qualification", "route_of_admin", "country", "has_black_box_warning", "is_concomitant_present", "age_group", "polypharmacy"]

numeric_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
])

categorical_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='most_frequent')),
    ('encoder', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
])

preprocessor = ColumnTransformer(
    transformers=[
        ('num', numeric_transformer, num_features),
        ('cat', categorical_transformer, cat_features)
    ]
)

# 5. Split
print("Séparation des données...")
X = df.drop(columns=[target_col])
y = df[target_col]

X_train_val, X_test, y_train_val, y_test = train_test_split(
    X, y, test_size=0.15, random_state=42, stratify=y
)

X_train, X_val, y_train, y_val = train_test_split(
    X_train_val, y_train_val, test_size=0.1765, random_state=42, stratify=y_train_val
)

# 6. Fit & Save
print("Fit du pipeline et sauvegarde...")
preprocessor.fit(X_train)
joblib.dump(preprocessor, MODELS_DIR / "preprocessor.joblib")

X_train.assign(**{target_col: y_train}).to_csv(PROCESSED_DIR / "train.csv", index=False)
X_val.assign(**{target_col: y_val}).to_csv(PROCESSED_DIR / "validation.csv", index=False)
X_test.assign(**{target_col: y_test}).to_csv(PROCESSED_DIR / "test.csv", index=False)

print("Pre-processing terminé avec succès.")
print(f"Datasets dans : {PROCESSED_DIR}")
print(f"Pipeline dans : {MODELS_DIR / 'preprocessor.joblib'}")
