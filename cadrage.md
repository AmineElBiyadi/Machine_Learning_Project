# Fiche de Cadrage — Projet Machine Learning
**Auteur(s) :** Amine El Biyadi / Aya Raissouni / Douae Moeniss
**Date :** 7 mai 2026
**Version :** 1.0

---

## 1. Exploration et choix du sujet

### 1.1. Domaine métier retenu

Nous avons choisi le domaine de la **santé**, et plus précisément la **sécurité des médicaments**, car il présente des enjeux métier réels et mesurables, des données publiques riches, et un déséquilibre naturel des classes (les événements graves sont minoritaires par nature).

---

### 1.2. APIs candidates explorées

#### API 1 — openFDA FAERS (`/drug/event.json`)
**Description :** Base de données des rapports d'effets indésirables médicamenteux soumis à la FDA (Food and Drug Administration) par des professionnels de santé, patients et industriels.
**Quotas :** 1 000 requêtes/minute sans clé API, 120 000/minute avec clé gratuite. Licence : domaine public (données gouvernementales US).

| # | Question métier |
|---|---|
| Q1 | Peut-on prédire si un rapport d'effet indésirable est associé à une **hospitalisation du patient** ? |
| Q2 | Peut-on prédire si le médicament suspect est impliqué dans le **décès du patient** ? |
| Q3 | Peut-on identifier si un rapport provient d'un **professionnel de santé** ou d'un consommateur, à partir des caractéristiques de l'événement rapporté ? |

---

#### API 2 — openFDA Drug Enforcement (`/drug/enforcement.json`)
**Description :** Données sur les rappels de médicaments initiés par la FDA, classifiés par niveau de dangerosité (Class I, II, III).
**Quotas :** Mêmes conditions que FAERS. Licence : domaine public.

| # | Question métier |
|---|---|
| Q1 | Peut-on prédire si un rappel de médicament est classifié en **Class I** (danger immédiat pour la santé) ? |
| Q2 | Peut-on prédire si le rappel concerne un **produit à usage hospitalier** plutôt qu'un produit grand public ? |

---

#### API 3 — ClinicalTrials.gov API (`/query/full_studies`)
**Description :** Registre public des essais cliniques mondiaux, avec métadonnées sur le statut, les résultats, les pathologies ciblées et les événements indésirables déclarés.
**Quotas :** Accès libre, sans clé API. Licence : domaine public (NIH).

| # | Question métier |
|---|---|
| Q1 | Peut-on prédire si un essai clinique sera **interrompu prématurément** (statut *Terminated*) ? |
| Q2 | Peut-on prédire si un essai rapporte des **effets indésirables graves** dans ses résultats ? |

---

### 1.3. Choix final — API + question métier

**API retenue : openFDA FAERS — Question Q1**

> *Prédire si un rapport d'effet indésirable médicamenteux est associé à une hospitalisation du patient.*

**Justification du choix :**

| Critère | openFDA FAERS | Drug Enforcement | ClinicalTrials.gov |
|---|---|---|---|
| Volume de données (≥ 10 000 lignes) | ✅ Millions de rapports disponibles | ❌ < 10 000 rappels historiques au total | ✅ Suffisant mais extraction complexe |
| Variable cible native et non artificielle | ✅ Champ `seriousnesshospitalization` natif | ✅ Champ `classification` natif | ⚠️ Variable cible mal documentée dans l'API |
| Déséquilibre naturel des classes (5–25 %) | ✅ ~15 % d'hospitalisations naturellement | ⚠️ Class I trop majoritaire selon les périodes | ⚠️ Proportion d'essais terminés variable |
| Richesse des features (≥ 8) | ✅ Patient, médicament, déclarant, réaction | ⚠️ Peu de variables exploitables | ✅ Riche mais structuration complexe |
| Enjeu métier clair et mesurable | ✅ Pharmacovigilance, priorisation des revues | ✅ Mais enjeu moins granulaire | ⚠️ Enjeu métier moins immédiat |

openFDA FAERS est la seule API réunissant toutes les contraintes du projet : volume suffisant, variable cible native, déséquilibre naturel, richesse des features, et pertinence métier directe en pharmacovigilance.

---

## 2. Sujet retenu et domaine métier

**Domaine métier :** Pharmacovigilance — sécurité des médicaments post-commercialisation

**Question métier :**
> À partir d'un rapport d'effet indésirable soumis à la FDA (FAERS), est-il possible de prédire automatiquement si cet événement est associé à une **hospitalisation du patient** ?

**Contexte :**
Le système FAERS (*FDA Adverse Event Reporting System*) reçoit des millions de rapports par an, soumis par des professionnels de santé, des patients et des industriels. Les équipes de pharmacovigilance doivent prioriser leur revue manuelle de ces rapports. Un modèle capable d'identifier automatiquement les rapports à risque d'hospitalisation permettrait de concentrer les ressources humaines sur les cas les plus graves.

---

## 2. Objectifs métiers quantifiés

| # | Objectif métier | Indicateur de succès | Cible quantifiée |
|---|---|---|---|
| M1 | Détecter les rapports associés à une hospitalisation pour les soumettre en priorité à revue humaine | Taux de détection des hospitalisations réelles parmi toutes les hospitalisations présentes | **≥ 80 % des hospitalisations identifiées** (recall ≥ 0,80) |
| M2 | Limiter la surcharge des équipes en ne générant pas trop de fausses alertes | Fraction des rapports signalés comme hospitalisations qui sont effectivement des hospitalisations | **≥ 50 % des alertes sont confirmées** (precision ≥ 0,50) |
| M3 | Maintenir un niveau de performance stable sur différentes périodes de collecte | Score F1 stable lors d'une validation croisée temporelle | **F1-score ≥ 0,60 sur les folds de validation** |

---

## 3. Traduction métier → Objectifs ML

| Objectif métier | Objectif ML | Métrique principale | Seuil cible |
|---|---|---|---|
| **M1** — Détecter 80 % des hospitalisations (ne pas rater des cas graves) | Maximiser le recall sur la classe `1` (hospitalisation) | **Recall** (classe 1) | ≥ 0,80 |
| **M2** — Limiter les fausses alertes pour ne pas surcharger les équipes | Maintenir une précision acceptable sur la classe `1` | **Precision** (classe 1) | ≥ 0,50 |
| **M3** — Équilibre global entre détection et précision | Maximiser le F1-score sur la classe minoritaire | **F1-score** (classe 1) | ≥ 0,60 |
| Suivi global de la courbe de compromis précision/rappel | Maximiser l'aire sous la courbe PR | **PR-AUC** | Maximiser |

> **Note sur la métrique principale retenue :** Le **recall** sur la classe `1` est la métrique de pilotage principale, car rater une hospitalisation (faux négatif) est systématiquement plus coûteux que signaler à tort un rapport non-hospitalisation (faux positif). Le **F1-score** et la **PR-AUC** servent de métriques secondaires pour éviter un recall trivial de 1,0 obtenu en classant tout comme hospitalisation.

---

## 4. Analyse du coût métier asymétrique

### Question fondamentale : que coûte plus cher — un faux positif ou un faux négatif ?

Dans notre contexte de pharmacovigilance, le coût est clairement **asymétrique en faveur du rappel** :

| Type d'erreur | Situation concrète | Conséquence métier | Coût estimé |
|---|---|---|---|
| **Faux négatif (FN)** | Le modèle prédit *pas d'hospitalisation* alors qu'il y en a une | Le rapport grave n'est pas priorisé → revue tardive → risque de signal de sécurité manqué → potentiellement des patients continuent à être exposés à un médicament dangereux | **Élevé** — risque sanitaire, responsabilité réglementaire, coût de signal manqué estimé à plusieurs dizaines de milliers d'euros (études de signal post-hoc, procédures réglementaires correctives, atteinte à la réputation de l'agence) |
| **Faux positif (FP)** | Le modèle prédit *hospitalisation* alors qu'il n'y en a pas | Un rapport non-grave est inutilement priorisé → analyste perd ~30 min à le requalifier | **Faible** — surcharge de travail limitée, estimée à ~30 minutes × coût horaire analyste ≈ **15–30 €** par fausse alerte |

### Ratio d'asymétrie estimé

En hypothèse conservatrice :
- Coût d'un **faux négatif** : ~ 50 000 € (signal de sécurité manqué, avec probabilité de conséquences réglementaires)
- Coût d'un **faux positif** : ~ 25 € (temps analyste perdu)
- **Ratio asymétrie** ≈ **2 000 : 1**

Cette asymétrie massive justifie de **privilégier fortement le recall**, quitte à accepter une precision modérée (50 %), ce qui correspond à tolérer une fausse alerte pour chaque vrai positif détecté — un compromis largement acceptable au regard du ratio de coût.

---

## 5. Choix et justification des métriques

### Métriques retenues

| Métrique | Rôle | Justification |
|---|---|---|
| **Recall (classe 1)** | Métrique principale de pilotage | Directement liée à l'objectif M1 ; mesure la fraction d'hospitalisations effectivement détectées. Priorité absolue vu le coût asymétrique des FN. |
| **Precision (classe 1)** | Métrique secondaire de contrôle | Évite un recall trivial de 1,0 ; assure que le modèle génère un nombre raisonnable d'alertes traitables par les équipes. |
| **F1-score (classe 1)** | Métrique de synthèse | Moyenne harmonique recall/precision — utile pour comparer des modèles entre eux et suivre la progression. |
| **PR-AUC** | Métrique de comparaison de modèles | Mesure globale du compromis precision/recall sur tous les seuils — robuste sur données déséquilibrées, contrairement à la ROC-AUC. Utilisée pour sélectionner le meilleur modèle. |

### Métriques explicitement exclues comme métrique principale

| Métrique exclue | Raison |
|---|---|
| **Accuracy** | Trompeuse sur données déséquilibrées : un modèle naïf prédisant toujours `0` obtiendrait ~85 % d'accuracy sans détecter aucune hospitalisation. |
| **ROC-AUC seule** | Optimiste sur données déséquilibrées — insensible au ratio de classes réel. Utilisée uniquement en complément, jamais comme métrique principale. |

---

## 6. Résumé du cadrage

| Élément | Valeur |
|---|---|
| **Domaine** | Pharmacovigilance |
| **Problème ML** | Classification supervisée binaire |
| **Variable cible** | `seriousnesshospitalization` (0 / 1) |
| **Classe minoritaire** | `1` — hospitalisation (~15 % du dataset) |
| **Source des données** | openFDA FAERS (`/drug/event.json`) + openFDA Drug Label (`/drug/label.json`) |
| **Taille du dataset** | 10 000 lignes, 12 colonnes (11 features + 1 cible) |
| **Erreur la plus coûteuse** | Faux négatif (hospitalisation non détectée) |
| **Métrique principale** | Recall (classe 1) ≥ 0,80 |
| **Métriques secondaires** | Precision ≥ 0,50 · F1-score ≥ 0,60 · PR-AUC maximisé |
| **Stratégie seuil** | Abaissement du seuil de décision en Phase 2 pour maximiser le recall |
