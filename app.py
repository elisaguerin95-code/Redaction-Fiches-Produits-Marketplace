"""
app.py
-------
Application Streamlit : Copilot de fiches produits marketplace (Amazon).

Deux modes d'entrée :
- Fiche unique : formulaire pour un produit
- Lot (Excel) : upload de plusieurs produits d'un coup

À chaque génération, la fiche est passée au moteur de règles (rules.py)
pour calculer un score de conformité affiché au vendeur.
"""

import io
import streamlit as st
import pandas as pd

from generator import generer_fiche
from rules import evaluate_listing

st.set_page_config(
    page_title="Marketplace Listing Copilot",
    page_icon="🛒",
    layout="wide",
)

# ---------------------------------------------------------------------
# Sidebar : info sur le moteur (pas de clé API nécessaire)
# ---------------------------------------------------------------------
st.sidebar.title("À propos")
st.sidebar.caption(
    "Génération 100% déterministe (aucun appel à une IA externe) : "
    "le moteur applique des règles de texte et de conformité, donc "
    "aucune clé API n'est nécessaire et aucun risque de plantage."
)
st.sidebar.markdown("---")
st.sidebar.caption(
    "Moteur de conformité basé sur les règles Amazon Seller Central "
    "vérifiées en juin 2026, incluant la nouvelle limite de titre à "
    "75 caractères applicable au 27/07/2026."
)

# ---------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------
st.title("🛒 Marketplace Listing Copilot")
st.caption(
    "Transforme des infos produit brutes en fiche Amazon optimisée et "
    "conforme, avec score de conformité instantané."
)

tab_single, tab_batch = st.tabs(["Fiche unique", "Lot (Excel)"])


def render_result(raw_input: dict, listing: dict):
    """Affiche le avant/après + le score de conformité pour une fiche."""
    report = evaluate_listing(listing)

    col_before, col_after = st.columns(2)
    with col_before:
        st.subheader("Avant (infos brutes)")
        for k, v in raw_input.items():
            if v:
                st.markdown(f"**{k}** : {v}")

    with col_after:
        st.subheader("Après (fiche optimisée)")
        st.markdown(f"**Titre** ({len(listing['title'])} car.)")
        st.write(listing["title"])
        st.markdown("**Item Highlights**")
        for h in listing.get("item_highlights", []):
            st.write(f"• {h}")
        st.markdown("**Bullet points**")
        for b in listing.get("bullets", []):
            st.write(f"• {b}")
        st.markdown("**Description**")
        st.write(listing.get("description", ""))
        st.markdown("**Mots-clés back-end**")
        st.code(listing.get("backend_keywords", ""))
        st.markdown(f"**Catégorie suggérée** : {listing.get('category_suggestion', '')}")

        st.markdown("**Attributs techniques (catégorie Amazon détectée)**")
        for label, valeur in listing.get("attributs_specifiques", {}).items():
            st.write(f"• {label} : {valeur}")

    st.markdown("---")
    score_col, grade_col = st.columns([1, 3])
    with score_col:
        st.metric("Score de conformité", f"{report.score}/100")
    with grade_col:
        st.markdown(f"### {report.grade}")

    with st.expander("Voir le détail des vérifications"):
        for c in report.checks:
            icon = "✅" if c.passed else "⚠️"
            st.markdown(f"{icon} **{c.label}** ({c.points_earned}/{c.points_max}) — {c.detail}")


# ---------------------------------------------------------------------
# Onglet 1 : fiche unique
# ---------------------------------------------------------------------
with tab_single:
    with st.form("single_listing_form"):
        c1, c2 = st.columns(2)
        with c1:
            brand = st.text_input("Marque", placeholder="ex : Hydra+")
            product_type = st.text_input("Type de produit", placeholder="ex : gourde isotherme")
        with c2:
            materiau = st.text_input("Matériau", placeholder="ex : inox")
            couleur = st.text_input("Couleur", placeholder="ex : bleu nuit")

        infos_produits = st.text_area(
            "Infos produits (séparées par des virgules)",
            placeholder="750ml, garde le froid 24h, sans BPA, anse de transport...",
            height=100,
        )

        submitted = st.form_submit_button("Générer la fiche optimisée", type="primary")

    if submitted:
        if not (brand or product_type or infos_produits):
            st.error("Renseigne au moins une information sur le produit.")
        else:
            raw_input = {
                "marque": brand,
                "type_produit": product_type,
                "materiau": materiau,
                "couleur": couleur,
                "infos_produits": infos_produits,
            }
            listing = generer_fiche(raw_input)
            st.session_state["last_listing"] = (raw_input, listing)

    if "last_listing" in st.session_state:
        raw_input, listing = st.session_state["last_listing"]
        render_result(raw_input, listing)


# ---------------------------------------------------------------------
# Onglet 2 : traitement par lot (Excel)
# ---------------------------------------------------------------------
with tab_batch:
    st.markdown(
        "Le fichier Excel doit contenir les colonnes : `marque`, "
        "`type_produit`, `materiau`, `couleur`, `infos_produits` "
        "(infos séparées par des virgules dans la cellule)."
    )

    template_df = pd.DataFrame([
        {"marque": "Hydra+", "type_produit": "gourde isotherme", "materiau": "inox",
         "couleur": "bleu nuit",
         "infos_produits": "750ml, garde le froid 24h, sans BPA, anse de transport"},
    ])
    template_buffer = io.BytesIO()
    template_df.to_excel(template_buffer, index=False, engine="openpyxl")
    st.download_button(
        "Télécharger le modèle Excel",
        data=template_buffer.getvalue(),
        file_name="modele_produits.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    uploaded_file = st.file_uploader("Importer la matrice Excel des produits", type=["xlsx"])

    if uploaded_file is not None:
        df_input = pd.read_excel(uploaded_file)
        df_input = df_input.fillna("")  # évite les erreurs sur les cellules vides
        st.dataframe(df_input, use_container_width=True)

        if st.button("Générer toutes les fiches", type="primary"):
            results = []
            progress = st.progress(0, text="Génération en cours...")
            total = len(df_input)

            for i, row in df_input.iterrows():
                raw_input = {
                    "marque": row.get("marque", ""),
                    "type_produit": row.get("type_produit", ""),
                    "materiau": row.get("materiau", ""),
                    "couleur": row.get("couleur", ""),
                    "infos_produits": row.get("infos_produits", ""),
                }
                listing = generer_fiche(raw_input)
                report = evaluate_listing(listing)
                results.append({
                    **raw_input,
                    "titre_optimise": listing["title"],
                    "description_marketing": listing["description"],
                    "bullets": " | ".join(listing.get("bullets", [])),
                    "backend_keywords": listing.get("backend_keywords", ""),
                    "categorie_suggeree": listing.get("category_suggestion", ""),
                    "attributs_specifiques": " | ".join(
                        f"{k}: {v}" for k, v in listing.get("attributs_specifiques", {}).items()
                    ),
                    "score_conformite": report.score,
                })

                progress.progress((i + 1) / total, text=f"Produit {i + 1}/{total} traité")

            result_df = pd.DataFrame(results)
            st.session_state["batch_results"] = result_df

    if "batch_results" in st.session_state:
        st.markdown("### Résultats")
        st.dataframe(st.session_state["batch_results"], use_container_width=True)

        result_buffer = io.BytesIO()
        st.session_state["batch_results"].to_excel(result_buffer, index=False, engine="openpyxl")
        st.download_button(
            "Télécharger les résultats (Excel)",
            data=result_buffer.getvalue(),
            file_name="fiches_optimisees.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
