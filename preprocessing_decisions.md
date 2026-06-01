# Décisions de Nettoyage des Données - Phase 2

**Dataset :** FAERS Drug Hospitalization Dataset  
**Fichier source :** `data/dataset.csv`  
**Dimension initiale :** 10,200 lignes x 12 colonnes  
**Fichier nettoyé :** `data/dataset_cleaned.csv`  
**Dimension finale :** 7,747 lignes x 12 colonnes

---

## Résumé Exécutif

Le nettoyage a été corrigé pour éviter une erreur méthodologique importante : les doublons doivent être détectés sur les données brutes avant imputation. Sinon, l'imputation peut créer artificiellement des lignes identiques.

| Aspect | Résultat |
|--------|----------|
| Valeurs manquantes traitées | 6 variables |
| Doublons exacts bruts supprimés | 2,042 lignes |
| Doublons post-imputation supprimés | 411 lignes |
| Incohérences métier corrigées | 9 âges convertis de jours vers années |
| Valeurs manquantes finales | 0 |
| Doublons finaux | 0 |
| Dimensions finales | 7,747 lignes x 12 colonnes |

Distribution finale de la cible :

| Classe | Nombre | Pourcentage |
|--------|--------|-------------|
| 0 - pas d'hospitalisation | 5,900 | 76.16% |
| 1 - hospitalisation | 1,847 | 23.84% |

La classe minoritaire reste dans la contrainte du projet : entre 5% et 25%.

---

## Tâche 2.1 - Valeurs Manquantes

Les taux ci-dessous sont calculés après suppression des doublons exacts bruts, afin de ne pas laisser les doublons biaiser les statistiques d'imputation.

| Variable | Type métier | Manquants | Stratégie | Valeur utilisée | Justification |
|----------|-------------|-----------|-----------|-----------------|---------------|
| `patient_age` | Numérique | 1,916 | Imputation médiane | 60.0 | Variable numérique avec asymétrie et outliers ; la médiane est robuste. |
| `route_of_admin` | Catégorielle | 1,754 | Imputation mode | `048` | Code FDA catégoriel ; le mode conserve la modalité dominante sans supprimer beaucoup de lignes. |
| `worst_reaction_outcome` | Catégorielle ordinale | 632 | Imputation mode | 6.0 | Le code 6 correspond à `unknown`, cohérent avec une issue non renseignée. |
| `country` | Catégorielle | 516 | Imputation mode | `US` | Pays majoritaire dans FAERS ; suppression non souhaitable. |
| `reporter_qualification` | Catégorielle | 318 | Imputation mode | 5.0 | Taux modéré ; modalité la plus fréquente utilisée. |
| `patient_sex` | Catégorielle | 71 | Imputation mode | 2.0 | Taux faible ; imputation simple suffisante. |
| Autres variables | Numérique/catégorielle | 0 | Aucune | - | Données complètes. |

**Choix non retenus :**

- Suppression de colonne : aucune variable ne dépasse 50% de valeurs manquantes.
- KNN Imputer : non retenu pour cette étape car plusieurs variables sont catégorielles codées, et une imputation simple est plus explicable pour le livrable de nettoyage.
- Suppression de lignes manquantes : non retenue pour les variables à fort taux de manque (`patient_age`, `route_of_admin`) car elle ferait perdre trop d'observations.

---

## Tâche 2.2 - Doublons et Incohérences

### Doublons Exacts

La détection est faite avec `df.duplicated()` sur toutes les colonnes.

| Étape | Résultat | Décision |
|-------|----------|----------|
| Avant imputation | 2,042 doublons exacts | Suppression |
| Après imputation | 411 doublons exacts supplémentaires | Suppression |
| Dataset final | 0 doublon exact | OK |

**Justification :** les doublons exacts peuvent surpondérer certains profils pendant l'apprentissage. La détection principale est réalisée avant imputation pour éviter de confondre vraies répétitions et doublons créés artificiellement par les valeurs imputées.

### Incohérences Logiques

| Vérification | Résultat | Décision |
|--------------|----------|----------|
| `patient_age < 0` | 0 ligne | Aucune action |
| `patient_age > 120` | 9 lignes | Correction métier |
| `nb_drugs >= 1` | Toutes valides | Aucune action |
| `nb_reactions >= 1` | Toutes valides | Aucune action |
| `nb_suspect_drugs <= nb_drugs` | Toutes valides | Aucune action |
| `worst_reaction_outcome` dans [1, 6] | Toutes valides après imputation | Aucune action |

### Incohérences Métier

Neuf valeurs de `patient_age` étaient impossibles en années (`604`, `905`, `16430`, `19639`, `22240`, `22928`, `23628`, `24434`, `32193`). Ces valeurs sont cohérentes avec des âges stockés en jours dans FAERS. Elles ont donc été converties en années par division par 365.25 lorsque le résultat restait dans l'intervalle métier 0-120 ans.

Après correction, `patient_age` est compris entre 0.0 et 103.0 ans.

---

## Tâche 2.3 - Outliers

Les outliers sont analysés après correction des incohérences métier et imputation.

| Variable numérique | Méthode IQR | Méthode Z-score | Décision |
|--------------------|-------------|-----------------|----------|
| `patient_age` | Outliers attendus sur nourrissons/personnes âgées | Aucun âge impossible après correction | Conserver les âges entre 0 et 120 ans |
| `nb_drugs` | Valeurs élevées liées à la polymédication | Valeurs extrêmes possibles | Conserver |
| `nb_reactions` | Valeurs élevées liées à plusieurs réactions reportées | Valeurs extrêmes possibles | Conserver |
| `nb_suspect_drugs` | Valeurs élevées liées à plusieurs médicaments suspects | Valeurs extrêmes possibles | Conserver |

**Justification générale :** dans un contexte de pharmacovigilance, les valeurs élevées de nombre de médicaments, réactions ou médicaments suspects peuvent être porteuses de signal clinique. Elles ne doivent pas être supprimées uniquement parce qu'elles sont rares.

---

## Tâche 2.4 - Tableau Récapitulatif des Décisions

| Variable | Problème détecté | Action effectuée | Justification |
|----------|------------------|------------------|---------------|
| `patient_age` | 1,916 manquants après dédoublonnage ; 9 valeurs > 120 | Conversion des 9 âges en jours vers années ; imputation médiane 60.0 ; conservation des outliers valides | La médiane est robuste ; les âges corrigés sont plausibles ; les âges extrêmes valides peuvent porter un signal. |
| `nb_drugs` | Outliers statistiques | Conservation | La polymédication est métier-validée et potentiellement prédictive. |
| `nb_reactions` | Outliers statistiques | Conservation | Plusieurs réactions peuvent indiquer une sévérité plus élevée. |
| `worst_reaction_outcome` | 632 manquants | Imputation mode 6.0 | Le code 6 correspond à une issue inconnue. |
| `nb_suspect_drugs` | Outliers statistiques | Conservation | Plusieurs médicaments suspects sont plausibles en pharmacovigilance. |
| `patient_sex` | 71 manquants | Imputation mode 2.0 | Taux faible ; variable catégorielle FDA. |
| `reporter_qualification` | 318 manquants | Imputation mode 5.0 | Taux modéré ; conservation des lignes. |
| `route_of_admin` | 1,754 manquants | Imputation mode `048` | Variable catégorielle ; voie dominante utilisée. |
| `country` | 516 manquants | Imputation mode `US` | Pays dominant dans FAERS ; suppression non nécessaire. |
| `has_black_box_warning` | Aucun manquant | Aucune action | Variable binaire valide. |
| `is_concomitant_present` | Aucun manquant | Aucune action | Variable binaire valide. |
| `seriousnesshospitalization` | Aucun manquant | Aucune action | Variable cible binaire valide. |
| Toutes les colonnes | 2,042 doublons exacts bruts ; 411 doublons post-imputation | Suppression des doublons | Évite la surpondération de profils identiques dans la modélisation. |

---

## Résultats Finaux

| Métrique | Avant | Après |
|----------|-------|-------|
| Lignes | 10,200 | 7,747 |
| Colonnes | 12 | 12 |
| Valeurs manquantes | Présentes sur 6 variables | 0 |
| Doublons exacts | 2,042 bruts + 411 post-imputation | 0 |
| Âges invalides | 9 | 0 |
| Classe minoritaire | 18.83% | 23.84% |

Le livrable Membre 2 est donc réalisé après correction : `notebooks/03_preprocessing.ipynb`, `data/dataset_cleaned.csv`, `data/outliers_boxplot.png` et `preprocessing_decisions.md`.
