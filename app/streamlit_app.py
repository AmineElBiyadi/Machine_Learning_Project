import streamlit as st
import pandas as pd
import requests
import io

import os
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Prédiction d'Hospitalisation FAERS",
    page_icon="🏥",
    layout="wide"
)

# Sidebar for navigation
page = st.sidebar.radio("Navigation", ["Formulaire de Prédiction", "Prédiction par Lot (CSV)", "Informations Modèle"])

# Mappings for UI
SEX_MAPPING = {"Inconnu": 0, "Homme": 1, "Femme": 2}
OUTCOME_MAPPING = {
    "Rétabli": 1,
    "En cours de rétablissement": 2,
    "Non rétabli": 3,
    "Rétabli avec séquelles": 4,
    "Décès": 5,
    "Inconnu": 6
}
REPORTER_MAPPING = {
    "Médecin": 1,
    "Pharmacien": 2,
    "Autre professionnel de santé": 3,
    "Avocat": 4,
    "Consommateur/Non-professionnel": 5
}
YES_NO_MAPPING = {"Non": 0, "Oui": 1}

def get_prediction_mock(data):
    """Mock prediction logic for development without API."""
    # Simple logic to mock the behavior
    risk = "risque élevé" if data["patient_age"] > 60 or data["worst_reaction_outcome"] >= 4 else "risque faible"
    prob = 0.85 if risk == "risque élevé" else 0.15
    return {"risk_level": risk, "probability": prob, "label": 1 if risk == "risque élevé" else 0}

if page == "Formulaire de Prédiction":
    st.title("🏥 Prédiction du Risque d'Hospitalisation")
    st.write("Veuillez saisir les caractéristiques du patient et de l'événement indésirable.")

    with st.form("prediction_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Patient")
            patient_age = st.number_input("Âge du patient", min_value=0.0, max_value=120.0, value=45.0, step=1.0)
            patient_sex = st.selectbox("Sexe du patient", options=list(SEX_MAPPING.keys()))
            country = st.text_input("Code Pays (ex: US, FR)", value="US")
            
        with col2:
            st.subheader("Détails du Signalement")
            reporter_qualification = st.selectbox("Qualification du déclarant", options=list(REPORTER_MAPPING.keys()))
            route_of_admin = st.text_input("Voie d'administration (ex: 001 pour oral)", value="001")
            
        st.subheader("Médicaments et Réactions")
        col3, col4, col5 = st.columns(3)
        with col3:
            nb_drugs = st.number_input("Nombre total de médicaments", min_value=1, value=1)
            nb_suspect_drugs = st.number_input("Nombre de médicaments suspects", min_value=0, max_value=int(nb_drugs), value=1)
        with col4:
            nb_reactions = st.number_input("Nombre de réactions", min_value=1, value=1)
            worst_reaction_outcome = st.selectbox("Pire résultat de réaction", options=list(OUTCOME_MAPPING.keys()))
        with col5:
            has_black_box_warning = st.selectbox("Avertissement Black Box présent", options=list(YES_NO_MAPPING.keys()))
            is_concomitant_present = st.selectbox("Médicaments concomitants présents", options=list(YES_NO_MAPPING.keys()))

        submitted = st.form_submit_button("Prédire")
        
        if submitted:
            # Prepare payload
            payload = {
                "patient_age": patient_age,
                "nb_drugs": int(nb_drugs),
                "nb_reactions": int(nb_reactions),
                "nb_suspect_drugs": int(nb_suspect_drugs),
                "worst_reaction_outcome": OUTCOME_MAPPING[worst_reaction_outcome],
                "patient_sex": SEX_MAPPING[patient_sex],
                "reporter_qualification": REPORTER_MAPPING[reporter_qualification],
                "has_black_box_warning": YES_NO_MAPPING[has_black_box_warning],
                "is_concomitant_present": YES_NO_MAPPING[is_concomitant_present],
                "route_of_admin": route_of_admin,
                "country": country
            }
            
            try:
                response = requests.post(f"{API_URL}/predict", json=payload, timeout=5)
                if response.status_code == 200:
                    result = response.json()
                    risk = "risque élevé" if result.get("label") == 1 else "risque faible"
                    prob = result.get("probability", 0.0)
                else:
                    st.warning("L'API n'est pas disponible ou a renvoyé une erreur. Utilisation des données mockées.")
                    result = get_prediction_mock(payload)
                    risk = result["risk_level"]
                    prob = result["probability"]
            except requests.exceptions.RequestException:
                st.warning("L'API est inaccessible. Utilisation des données mockées en attendant P1.")
                result = get_prediction_mock(payload)
                risk = result["risk_level"]
                prob = result["probability"]
                
            st.divider()
            if risk == "risque élevé":
                st.error(f"⚠️ **Résultat : {risk.upper()}** (Probabilité : {prob:.2f})")
                st.write("Le patient présente un risque élevé d'hospitalisation.")
            else:
                st.success(f"✅ **Résultat : {risk.upper()}** (Probabilité : {prob:.2f})")
                st.write("Le patient présente un risque faible d'hospitalisation.")


elif page == "Prédiction par Lot (CSV)":
    st.title("📂 Prédiction par Lot (Mode Batch)")
    st.write("Uploadez un fichier CSV contenant plusieurs signalements pour obtenir les prédictions enrichies.")
    
    uploaded_file = st.file_uploader("Choisissez un fichier CSV", type="csv")
    
    if uploaded_file is not None:
        if st.button("Lancer les prédictions"):
            with st.spinner("Traitement en cours..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
                    response = requests.post(f"{API_URL}/predict/csv", files=files, timeout=30)
                    
                    if response.status_code == 200:
                        st.success("Prédictions terminées avec succès !")
                        
                        # Provide download button
                        st.download_button(
                            label="📥 Télécharger les prédictions enrichies",
                            data=response.content,
                            file_name=f"predictions_{uploaded_file.name}",
                            mime="text/csv"
                        )
                        
                        # Show a preview
                        df_preview = pd.read_csv(io.BytesIO(response.content))
                        st.write("Aperçu des résultats :")
                        st.dataframe(df_preview.head())
                        
                    else:
                        st.error(f"Erreur API : {response.status_code} - {response.text}")
                except requests.exceptions.RequestException:
                    st.error("L'API est inaccessible. Le mode batch mocké n'est pas complètement implémenté, veuillez démarrer l'API.")


elif page == "Informations Modèle":
    st.title("ℹ️ Informations sur le Modèle")
    
    try:
        response = requests.get(f"{API_URL}/model/info", timeout=5)
        if response.status_code == 200:
            info = response.json()
            
            st.header(info.get("name", "Modèle FAERS"))
            st.write(f"**Version :** {info.get('version')}")
            st.write(f"**Cible :** {info.get('target')}")
            st.write(f"**Date de chargement :** {info.get('loaded_at')}")
            
            st.subheader("Performances")
            metrics = info.get("metrics", {})
            if metrics:
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Accuracy", f"{metrics.get('accuracy', 0):.4f}")
                col2.metric("Precision", f"{metrics.get('precision', 0):.4f}")
                col3.metric("Recall", f"{metrics.get('recall', 0):.4f}")
                col4.metric("F1-Score", f"{metrics.get('f1', 0):.4f}")
            else:
                st.info("Les métriques de performance ne sont pas disponibles dans ce pipeline.")
                
            st.subheader("Caractéristiques Utilisées")
            st.write(", ".join(info.get("feature_names", [])))
            
        else:
            st.error("Impossible de récupérer les informations du modèle depuis l'API.")
    except requests.exceptions.RequestException:
        st.warning("L'API est inaccessible. Données statiques affichées.")
        
        st.header("Modèle FAERS (Mock)")
        st.write("Ce modèle utilise les données ouvertes de la FDA (openFDA FAERS) pour prédire le risque d'hospitalisation.")
        
        st.subheader("Limites")
        st.write("- Les données FAERS sont des déclarations spontanées et peuvent contenir des biais de signalement.")
        st.write("- Le modèle dépend de la qualité de la saisie (valeurs manquantes, etc.).")
        st.write("- Les performances réelles peuvent varier en fonction des nouvelles données de pharmacovigilance.")
