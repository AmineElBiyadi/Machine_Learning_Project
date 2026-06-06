# -*- coding: utf-8 -*-
"""

Taches 3.1 a 3.6 : Transformation, Feature Engineering & Pipeline
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from pathlib import Path
import numpy as np
import pandas as pd
import joblib
import warnings
warnings.filterwarnings("ignore")

from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import (
    StandardScaler, OneHotEncoder, OrdinalEncoder, RobustScaler
)
from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.model_selection import train_test_split

try:
    from imblearn.over_sampling import SMOTE
    from imblearn.under_sampling import RandomUnderSampler
    IMBLEARN_AVAILABLE = True
except ImportError:
    IMBLEARN_AVAILABLE = False

# Chemins
ROOT = Path(__file__).resolve().parent.parent
CLEAN_PATH = ROOT / "data" / "dataset_cleaned.csv"
PROCESSED  = ROOT / "data" / "processed"
MODELS_DIR = ROOT / "models"
PROCESSED.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Chargement du dataset nettoye
print("=" * 60)
print("Chargement de dataset_cleaned.csv")
print("=" * 60)
df = pd.read_csv(CLEAN_PATH, dtype={"route_of_admin": "string"})
df["route_of_admin"] = df["route_of_admin"].apply(
    lambda x: str(int(float(x))).zfill(3) if pd.notna(x) else pd.NA
)
print(f"  Shape : {df.shape}")
print(f"  Colonnes : {list(df.columns)}")

# Definitions des colonnes
TARGET = "seriousnesshospitalization"

numerical_cols = ["patient_age", "nb_drugs", "nb_reactions", "nb_suspect_drugs"]
ordinal_cols   = ["worst_reaction_outcome"]
ordinal_order  = [[1.0, 2.0, 3.0, 4.0, 5.0, 6.0]]
nominal_cols   = ["patient_sex", "reporter_qualification",
                  "has_black_box_warning", "is_concomitant_present",
                  "route_of_admin", "country"]

# ===========================================================
# TACHE 3.3 - Feature Engineering
# ===========================================================
print("\n" + "=" * 60)
print("Tache 3.3 - Feature Engineering")
print("=" * 60)

# Feature 1 : ratio_suspect_drugs = nb_suspect_drugs / nb_drugs
# Justification : ratio eleve => presque tous les medicaments suspects => signal gravite
df["ratio_suspect_drugs"] = df["nb_suspect_drugs"] / df["nb_drugs"].replace(0, np.nan)
df["ratio_suspect_drugs"] = df["ratio_suspect_drugs"].fillna(0.0)
print("  [+] ratio_suspect_drugs = nb_suspect_drugs / nb_drugs")
print("      Justification : ratio eleve => presque tous les medicaments suspects")
print("                      => signal fort de gravite potentielle.")

# Feature 2 : age_group (binning patient_age)
# Justification : nourrissons (<2 ans) et seniors (>75 ans) sur-representes
# dans les hospitalisations liees aux effets secondaires.
bins   = [0, 2, 18, 65, 75, 120]
labels = ["nourrisson", "enfant", "adulte", "senior", "tres_age"]
df["age_group"] = pd.cut(
    df["patient_age"], bins=bins, labels=labels, right=True
).astype(str)
print("\n  [+] age_group = tranches d'age depuis patient_age")
print("      Labels : nourrisson(0-2), enfant(2-18), adulte(18-65),")
print("               senior(65-75), tres_age(75-120)")
print("      Justification : nourrissons & tres ages => risque hospitalisation accru.")

# Feature 3 : severity_polypharmacy = (7 - worst_reaction_outcome) x nb_drugs
# Justification : reaction grave (code bas) combinee a plusieurs medicaments amplifie
# le risque d'hospitalisation.
df["severity_polypharmacy"] = (7 - df["worst_reaction_outcome"]) * df["nb_drugs"]
print("\n  [+] severity_polypharmacy = (7 - worst_reaction_outcome) x nb_drugs")
print("      Justification : reaction grave + polymedication => risque hospitalisation.")

# Mise a jour des listes de colonnes
numerical_cols_fe = numerical_cols + ["ratio_suspect_drugs", "severity_polypharmacy"]
nominal_cols_fe   = nominal_cols + ["age_group"]

print(f"\n  Nouvelles features numeriques : ['ratio_suspect_drugs','severity_polypharmacy']")
print(f"  Nouvelle feature categorielle : ['age_group']")

# ===========================================================
# TACHE 3.1 - Justifications encodage categoriel
# ===========================================================
print("\n" + "=" * 60)
print("Tache 3.1 - Justifications encodage categoriel")
print("=" * 60)
print("""
  Variables nominales => OneHotEncoder (handle_unknown='ignore')
  ---------------------------------------------------------------
  patient_sex              (3 modalites) : pas d'ordre naturel M/F/inconnu
  reporter_qualification   (5 modalites) : categories sans ordre metier clair
  has_black_box_warning    (2 modalites) : flag binaire nominal
  is_concomitant_present   (2 modalites) : flag binaire nominal
  route_of_admin          (~10 modalites) : voies d'admin non ordonnees
  country                 (~20 modalites) : pays sans hierarchie
  age_group                (5 modalites) : feature derivee nominale

  Variable ordinale => OrdinalEncoder (ordre naturel 1->6)
  ---------------------------------------------------------------
  worst_reaction_outcome : 1=recovered, 2=recovering, 3=not recovered,
    4=recovered with sequelae, 5=fatal, 6=unknown
    => Il existe un ordre de gravite decroissante (1 = meilleur, 5 = pire).
       L'OrdinalEncoder preserve cette information ordinale.
""")

# ===========================================================
# TACHE 3.2 - Justification du scaler
# ===========================================================
print("=" * 60)
print("Tache 3.2 - Justification du scaler")
print("=" * 60)
print("""
  => RobustScaler retenu pour toutes les variables numeriques.

  Raison : patient_age, nb_drugs, nb_reactions, nb_suspect_drugs
  presentent tous des outliers significatifs (detectes par IQR en Phase 2).
  RobustScaler utilise la mediane et l'IQR au lieu de la moyenne et l'ecart-
  type, ce qui le rend insensible aux valeurs extremes.

  Comparatif :
    StandardScaler => sensible aux outliers (non retenu)
    MinMaxScaler   => tres sensible aux outliers (non retenu)
    RobustScaler   => robuste aux outliers (RETENU)
""")

# ===========================================================
# TACHE 3.4 - Construction du Pipeline scikit-learn
# ===========================================================
print("=" * 60)
print("Tache 3.4 - Construction du Pipeline")
print("=" * 60)

# Sous-pipeline numerique
numeric_pipeline = Pipeline([
    ("imputer", KNNImputer(n_neighbors=5)),
    ("scaler",  RobustScaler())
])

# Sous-pipeline ordinal
ordinal_pipeline = Pipeline([
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("encoder", OrdinalEncoder(
        categories=ordinal_order,
        handle_unknown="use_encoded_value",
        unknown_value=-1
    ))
])

# Sous-pipeline categoriel nominal
categorical_pipeline = Pipeline([
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
])

# Pipeline global
preprocessor = ColumnTransformer([
    ("num", numeric_pipeline,     numerical_cols_fe),
    ("ord", ordinal_pipeline,     ordinal_cols),
    ("cat", categorical_pipeline, nominal_cols_fe),
])

print("  Pipeline construit :")
print("    num => KNNImputer(k=5) + RobustScaler")
print("    ord => SimpleImputer(mode) + OrdinalEncoder")
print("    cat => SimpleImputer(mode) + OneHotEncoder")

# ===========================================================
# TACHE 3.5 - Separation train / validation / test
# ===========================================================
print("\n" + "=" * 60)
print("Tache 3.5 - Separation train / validation / test")
print("=" * 60)

X = df.drop(columns=[TARGET])
y = df[TARGET]

print(f"  Distribution cible globale :")
print(y.value_counts(normalize=True).round(4).to_string())

# Split stratifie 70 / 15 / 15
X_train, X_temp, y_train, y_temp = train_test_split(
    X, y, test_size=0.30, stratify=y, random_state=42
)
X_val, X_test, y_val, y_test = train_test_split(
    X_temp, y_temp, test_size=0.50, stratify=y_temp, random_state=42
)

print(f"\n  Tailles des splits :")
print(f"    Train      : {len(X_train):,} lignes ({len(X_train)/len(X)*100:.1f}%)")
print(f"    Validation : {len(X_val):,} lignes  ({len(X_val)/len(X)*100:.1f}%)")
print(f"    Test       : {len(X_test):,} lignes  ({len(X_test)/len(X)*100:.1f}%)")

def class_ratio(y_split, name):
    ratio = y_split.value_counts(normalize=True).round(4)
    print(f"\n  Ratio desequilibre {name} :")
    print(f"    Classe 0 (pas hospit.) : {ratio.get(0, 0)*100:.2f}%")
    print(f"    Classe 1 (hospit.)     : {ratio.get(1, 0)*100:.2f}%")

class_ratio(y_train, "Train")
class_ratio(y_val,   "Validation")
class_ratio(y_test,  "Test")

# Fit du preprocessor sur le train uniquement
print("\n  Fit du preprocessor sur X_train...")
preprocessor.fit(X_train)

# Sauvegarde des CSV (features engineered, avant transformation pipeline)
train_df = X_train.copy(); train_df[TARGET] = y_train
val_df   = X_val.copy();   val_df[TARGET]   = y_val
test_df  = X_test.copy();  test_df[TARGET]  = y_test

train_df.to_csv(PROCESSED / "train.csv",      index=False)
val_df.to_csv(  PROCESSED / "validation.csv", index=False)
test_df.to_csv( PROCESSED / "test.csv",       index=False)
print(f"  OK  data/processed/train.csv       ({len(train_df):,} lignes)")
print(f"  OK  data/processed/validation.csv  ({len(val_df):,} lignes)")
print(f"  OK  data/processed/test.csv        ({len(test_df):,} lignes)")

# Serialisation du pipeline
joblib.dump(preprocessor, MODELS_DIR / "preprocessor.joblib")
print(f"\n  OK  models/preprocessor.joblib sauvegarde")

# ===========================================================
# TACHE 3.6 - Strategies de desequilibre (code pret, pas d'entrainement)
# ===========================================================
print("\n" + "=" * 60)
print("Tache 3.6 - Strategies de desequilibre (code prepare)")
print("=" * 60)

X_train_transformed = preprocessor.transform(X_train)
print(f"\n  Shape X_train transforme : {X_train_transformed.shape}")

if IMBLEARN_AVAILABLE:
    smote = SMOTE(random_state=42)
    rus   = RandomUnderSampler(random_state=42)

    print("\n  Strategie 1 - class_weight='balanced'")
    print("    => Sera passe directement au classifier en Phase 3")
    print("       Ex: LogisticRegression(class_weight='balanced')")

    print("\n  Strategie 2 - SMOTE (Synthetic Minority Oversampling)")
    X_sm, y_sm = smote.fit_resample(X_train_transformed, y_train)
    print(f"    => Shape apres SMOTE : {X_sm.shape}")
    counts_sm = pd.Series(y_sm).value_counts().to_dict()
    print(f"    => Distribution : {counts_sm}")

    print("\n  Strategie 3 - RandomUnderSampler")
    X_rus, y_rus = rus.fit_resample(X_train_transformed, y_train)
    print(f"    => Shape apres undersampling : {X_rus.shape}")
    counts_rus = pd.Series(y_rus).value_counts().to_dict()
    print(f"    => Distribution : {counts_rus}")
else:
    print("\n  ATTENTION : imbalanced-learn non installe.")
    print("    Installer avec : pip install imbalanced-learn")
    print("  Code prepare pour utilisation future.")

print("\n" + "=" * 60)
print("Tous les livrables Membre 3 ont ete generes avec succes !")
print("=" * 60)
print("  - data/processed/train.csv")
print("  - data/processed/validation.csv")
print("  - data/processed/test.csv")
print("  - models/preprocessor.joblib")
