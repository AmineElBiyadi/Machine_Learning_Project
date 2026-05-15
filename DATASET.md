# Documentation du dataset

## a) Identification

- **Nom du dataset :** FAERS Drug Hospitalization Dataset
- **Auteur(s) :** Amine El Biyadi / Aya Raissouni / Douae Moeniss
- **Date de collecte :** 7 mai 2026
- **Version :** 1.0

---

## b) Source

- **API principale :** openFDA FAERS Drug Adverse Event
  - URL de base : `https://api.fda.gov/drug/event.json`
  - Endpoint interrogé : `/drug/event.json` avec pagination via le paramètre `skip`
- **API complémentaire :** openFDA Drug Label
  - URL de base : `https://api.fda.gov/drug/label.json`
  - Endpoint interrogé : `/drug/label.json` — utilisé pour enrichir chaque rapport avec la présence d'un black box warning FDA sur le médicament suspect principal
- **Date d'accès :** 7 mai 2026

---

## c) Description

### Objectif du dataset

Ce dataset est constitué pour résoudre un problème de **classification supervisée binaire** : prédire si un rapport d'effet indésirable médicamenteux soumis à la FDA est associé à une hospitalisation du patient (`seriousnesshospitalization = 1`).

Il permet de modéliser le risque d'hospitalisation à partir de caractéristiques du patient, des médicaments impliqués, du déclarant, et de signaux de sécurité réglementaires, dans le but d'aider les équipes de pharmacovigilance à prioriser leur revue des rapports entrants.

---

### Taille du dataset

| Critère | Valeur |
|---|---|
| Nombre de lignes | 10 000 |
| Nombre de colonnes | 12 (11 features + 1 variable cible) |

---

### Schéma détaillé

| Nom de la variable | Type | Description métier | Valeurs / Unité |
|---|---|---|---|
| `patient_age` | numérique | Âge du patient au moment de l'événement indésirable | Années — entier ou float, plage attendue : 0–120. Valeurs manquantes possibles (champ optionnel dans FAERS). |
| `nb_drugs` | numérique | Nombre total de médicaments listés dans le rapport (suspects + concomitants + interagissants) | Entier ≥ 1 |
| `nb_reactions` | numérique | Nombre de réactions distinctes rapportées dans le rapport | Entier ≥ 1 |
| `worst_reaction_outcome` | numérique | Code de la gravité la plus élevée parmi toutes les issues de réaction du rapport | 1 = recovered / resolved, 2 = recovering / resolving, 3 = not recovered / not resolved, 4 = recovered with sequelae, 5 = fatal, 6 = unknown. Valeur manquante si aucune issue n'est renseignée. |
| `nb_suspect_drugs` | numérique | Nombre de médicaments marqués comme suspects de la réaction (`drugcharacterization = 1`) | Entier ≥ 0 |
| `patient_sex` | catégoriel | Sexe biologique du patient | 0 = unknown, 1 = male, 2 = female. Stocké comme entier par l'API — type métier : catégoriel. |
| `reporter_qualification` | catégoriel | Qualification professionnelle de la personne ayant soumis le rapport | 1 = physician, 2 = pharmacist, 3 = other health professional, 4 = lawyer, 5 = consumer / non-health professional. Stocké comme entier par l'API — type métier : catégoriel. |
| `route_of_admin` | catégoriel | Voie d'administration du médicament principal suspect. Stocké comme code numérique à 3 chiffres défini par la FDA (Data Standards Manual, monographie C-DRG-00301). | Code numérique 3 chiffres. Codes les plus fréquents dans FAERS : `001`=oral, `002`=intravenous, `003`=subcutaneous, `005`=intramuscular, `011`=topical, `014`=nasal, `016`=rectal, `024`=sublingual, `136`=inhalation, `137`=intravenous drip, `358`=transdermal, `139`=unknown. Plus de 80 autres codes possibles (source officielle : fda.gov/drugs/data-standards-manual-monographs/route-administration). |
| `country` | catégoriel | Pays où l'événement indésirable a été rapporté | Code ISO 2 lettres (ex. US, FR, DE, JP, GB). |
| `has_black_box_warning` | catégoriel | Indique si le médicament suspect principal porte un black box warning FDA au moment de la collecte | 0 = aucun black box warning détecté, 1 = black box warning présent. Obtenu via l'API `drug/label.json`. Type métier : catégoriel (variable binaire à deux modalités). |
| `is_concomitant_present` | catégoriel | Indique si le rapport contient au moins un médicament concomitant (`drugcharacterization = 2`) | 0 = aucun médicament concomitant, 1 = au moins un médicament concomitant présent. Calculé à partir du champ `drugcharacterization`. Type métier : catégoriel (variable binaire à deux modalités). |
| `seriousnesshospitalization` | **catégoriel — variable cible** | Indique si le rapport mentionne une hospitalisation du patient | 0 = pas d'hospitalisation rapportée (classe majoritaire), 1 = hospitalisation rapportée (classe minoritaire). Dérivé directement du champ FDA `seriousnesshospitalization`. |

---

### Note sur les variables catégorielles stockées comme entiers

Les variables `patient_sex`, `reporter_qualification`, `has_black_box_warning`, `is_concomitant_present` et `seriousnesshospitalization` sont présentes dans le dataset sous forme d'entiers (0, 1, 2…). Leur type **métier** reste catégoriel : les entiers sont des étiquettes de catégorie, non des quantités. Elles seront encodées correctement (one-hot encoding ou encodage ordinal selon le modèle) lors du prétraitement en Phase 2.

### Note sur la prévention de la fuite de données

Les champs `serious`, `seriousnessdeath`, `seriousnesslifethreatening`, `seriousnessdisabling`, `seriousnesscongenitalanomali` et `seriousnessother` sont **intentionnellement exclus** des features. Ces champs sont des sous-composants de la même classification FDA de sériosité que la variable cible, et leur inclusion constituerait une fuite de données directe.

---

### Variable cible

- **Nom :** `seriousnesshospitalization`
- **Type :** catégoriel (binaire à deux modalités)
- **Source :** champ natif FDA `seriousnesshospitalization` dans la réponse de l'API FAERS
- **Définition FDA :** vaut `1` lorsque l'événement indésirable a entraîné ou prolongé une hospitalisation du patient
- **Classe minoritaire :** `1` (hospitalisation rapportée)
- **Classe majoritaire :** `0` (pas d'hospitalisation rapportée)

---

### Distribution des classes

La variable cible présente un déséquilibre naturel : les hospitalisations représentent historiquement une fraction minoritaire des rapports FAERS, typiquement entre 8 % et 15 % selon la période et le sous-ensemble de données collecté.

Distribution approximative observée après collecte :

| Classe | Valeur | Proportion approximative |
|---|---|---|
| Pas d'hospitalisation | 0 | ~85 % |
| Hospitalisation rapportée | 1 | ~15 % |

```
seriousnesshospitalization=0 | ████████████████████████████▌  ~85%
seriousnesshospitalization=1 | █████▌  ~15%
```

> La distribution exacte est vérifiable dans le notebook `notebooks/01_discovery.ipynb` (graphique `value_counts` + bar chart).

---

## Méthodologie de collecte

1. Le script `src/data_collection.py` interroge l'API FAERS par lots de 300 rapports via le paramètre `skip` (pagination).
2. Chaque réponse brute est immédiatement sauvegardée dans `data/raw/batch_skip<offset>.json` avant tout traitement — ce qui permet de relancer l'extraction de features sans re-interroger l'API.
3. Les features sont extraites de chaque rapport brut via la fonction `extract_features()`.
4. Chaque rapport est enrichi par un appel à l'API `drug/label.json` pour récupérer la présence d'un black box warning sur le médicament suspect (`has_black_box_warning`).
5. La variable `is_concomitant_present` est calculée directement à partir du champ `drugcharacterization` des médicaments listés dans le rapport.
6. Un checkpoint CSV partiel est sauvegardé tous les 1 000 lignes (`data/partial_<n>.csv`) pour éviter toute perte en cas d'interruption.
7. Chaque appel API est journalisé dans `collection.log` (horodatage, endpoint, offset, statut HTTP).

---

## Fichiers produits

| Fichier | Description |
|---|---|
| `data/raw/batch_skip*.json` | Réponses brutes de l'API FAERS — une par lot de 300 rapports. Permettent de rejouer l'extraction sans re-requêter l'API. |
| `data/dataset.csv` | Dataset final complet (10 000+ lignes, 12 colonnes) prêt pour la Phase 2. |
| `data/sample.csv` | Extrait aléatoire de 100 lignes issu de `dataset.csv` (tirage avec `random_state=42`). Permet de vérifier rapidement la structure des colonnes, la présence de la variable cible, les types de variables, et la cohérence des valeurs — sans charger les 10 000 lignes. |
| `collection.log` | Journal complet des appels API (horodatage, offset, statut HTTP). |