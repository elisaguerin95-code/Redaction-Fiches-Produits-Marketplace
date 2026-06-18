"""
app.py
-------
Application Streamlit : outil d'aide à la création de fiches produits
marketplace (Amazon).

Deux modes d'entrée :
- Fiche unique : formulaire pour un produit
- Lot (Excel) : upload de plusieurs produits d'un coup

Un troisième onglet affiche l'historique des fiches générées pendant la
session en cours (pas persistant entre deux visites, voir README).

À chaque génération, la fiche est passée au moteur de règles (rules.py)
pour calculer un score de conformité texte, et à image_check.py si une
image est fournie.
"""

import io
from datetime import datetime

import streamlit as st
import pandas as pd

from generator import generer_fiche
from rules import evaluate_listing
from image_check import verifier_image
from export_amazon import generer_ligne_export_amazon

st.set_page_config(
    page_title="Création Fiche Produit Marketplace",
    page_icon="🏷️",
    layout="wide",
)

# ---------------------------------------------------------------------
# Constantes d'affichage
# ---------------------------------------------------------------------

LABELS_AFFICHAGE = {
    "marque": "Marque",
    "type_produit": "Type de produit",
    "materiau": "Matériau",
    "couleur": "Couleur",
    "infos_produits": "Infos produits",
    "image_url": "Image principale",
}


def majuscule_initiale(texte: str) -> str:
    """Met une majuscule au premier caractère sans toucher au reste (contrairement à .capitalize())."""
    return texte[0].upper() + texte[1:] if texte else texte


def icone_depuis_score(score: float) -> str:
    if score >= 85:
        return "✅"
    if score >= 65:
        return "⚠️"
    return "❌"


def grade_depuis_score(score: float) -> str:
    if score >= 85:
        return "Excellent"
    if score >= 65:
        return "Correct, à améliorer"
    return "Non conforme"


def ajouter_a_historique(raw_input: dict, listing: dict, score_texte: float, score_image):
    if "historique" not in st.session_state:
        st.session_state["historique"] = []
    st.session_state["historique"].append({
        "horodatage": datetime.now().strftime("%H:%M:%S"),
        "marque": raw_input.get("marque", ""),
        "type_produit": raw_input.get("type_produit", ""),
        "titre_genere": listing.get("title", ""),
        "score_texte": score_texte,
        "score_image": score_image if score_image is not None else "",
    })


# ---------------------------------------------------------------------
# Sidebar : info sur le moteur (pas de clé API nécessaire)
# ---------------------------------------------------------------------
st.sidebar.title("À propos")
st.sidebar.caption(
    "Génération 100% déterministe (aucun appel à une IA générative externe) : "
    "le moteur applique des règles de texte et de conformité, donc "
    "aucune clé API n'est nécessaire et aucun risque de plantage."
)
st.sidebar.markdown("---")
st.sidebar.caption(
    "Moteur de conformité basé sur les règles Amazon Seller Central "
    "vérifiées en juin 2026, incluant la nouvelle limite de titre à "
    "75 caractères applicable au 27/07/2026."
)
st.sidebar.markdown("---")
st.sidebar.caption(
    "L'historique (3ᵉ onglet) ne couvre que la session en cours : il est "
    "perdu si tu fermes ou recharges la page."
)

# ---------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------
st.title("🏷️ Création Fiche Produit Marketplace")
st.caption(
    "Transforme des infos produit brutes en fiche Amazon optimisée et "
    "conforme, avec score de conformité instantané."
)

tab_single, tab_batch, tab_historique = st.tabs(["Fiche unique", "Lot (Excel)", "Historique"])


def afficher_bloc_conformite(titre: str, score: float, checks: list, cle_expander: str):
    """Bloc réutilisé pour le texte ET l'image : note + icône + détail dépliable."""
    st.markdown("---")
    st.subheader(titre)
    score_col, grade_col = st.columns([1, 3])
    with score_col:
        st.metric("Score de conformité", f"{score}/100")
    with grade_col:
        st.markdown(f"### {icone_depuis_score(score)} {grade_depuis_score(score)}")
    with st.expander("Voir le détail des vérifications", key=cle_expander):
        for c in checks:
            icon = "✅" if (c["passed"] if isinstance(c, dict) else c.passed) else "⚠️"
            label = c["label"] if isinstance(c, dict) else c.label
            detail = c["detail"] if isinstance(c, dict) else c.detail
            st.markdown(f"{icon} **{label}** — {detail}")


def render_result(raw_input: dict, listing: dict):
    """Affiche l'export, le avant/après, le score de conformité et l'image pour une fiche."""
    report = evaluate_listing(listing)
    image_url = raw_input.get("image_url", "")
    images_secondaires = raw_input.get("images_secondaires", [])

    # --- Export façon Amazon : tout en haut, directement visible ---
    ligne_export = generer_ligne_export_amazon(
        raw_input, listing, image_url=image_url, images_secondaires=images_secondaires
    )
    export_df = pd.DataFrame([ligne_export])
    export_buffer = io.BytesIO()
    export_df.to_excel(export_buffer, index=False, engine="openpyxl")
    st.download_button(
        "📤 Télécharger l'export façon Amazon (à copier-coller dans le vrai template)",
        data=export_buffer.getvalue(),
        file_name="export_amazon.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.markdown("---")
    col_before, col_after = st.columns(2)
    with col_before:
        st.subheader("Avant (infos brutes)")
        for k, v in raw_input.items():
            if k == "images_secondaires" or not v:
                continue
            label = LABELS_AFFICHAGE.get(k, k)
            st.markdown(f"**{label}** : {majuscule_initiale(str(v))}")
        if images_secondaires:
            st.markdown(f"**Images secondaires** : {len(images_secondaires)} fournie(s)")
        if image_url:
            st.image(image_url, caption="Image principale fournie", use_container_width=True)

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

    afficher_bloc_conformite("Conformité du texte", report.score, report.checks, "expander_texte")

    score_image_pour_historique = None

    if image_url:
        rapport_image = verifier_image(image_url, image_principale=True)
        if not rapport_image["url_valide"]:
            st.markdown("---")
            st.subheader("Conformité de l'image principale")
            st.error(f"Image non vérifiable : {rapport_image['erreur']}")
        else:
            afficher_bloc_conformite(
                "Conformité de l'image principale", rapport_image["score"],
                rapport_image["checks"], "expander_image_principale",
            )
            score_image_pour_historique = rapport_image["score"]

    if images_secondaires:
        st.markdown("---")
        st.subheader(f"Conformité des {len(images_secondaires)} image(s) secondaire(s)")
        st.caption("Règles plus souples que l'image principale : pas de fond blanc requis.")
        for idx, url in enumerate(images_secondaires, start=1):
            rapport = verifier_image(url, image_principale=False)
            if not rapport["url_valide"]:
                st.warning(f"Image secondaire {idx} non vérifiable : {rapport['erreur']}")
                continue
            with st.expander(f"Image secondaire {idx} — score {rapport['score']}/100"):
                for c in rapport["checks"]:
                    icon = "✅" if c["passed"] else "⚠️"
                    st.markdown(f"{icon} **{c['label']}** — {c['detail']}")

    ajouter_a_historique(raw_input, listing, report.score, score_image_pour_historique)


def parser_urls(texte: str) -> list:
    """Découpe un champ 'plusieurs URLs séparées par des virgules' en liste propre."""
    if not texte:
        return []
    return [u.strip() for u in texte.split(",") if u.strip()]


# ---------------------------------------------------------------------
# Onglet 1 : fiche unique
# ---------------------------------------------------------------------
with tab_single:
    st.caption("* champs obligatoires")
    with st.form("single_listing_form"):
        c1, c2 = st.columns(2)
        with c1:
            brand = st.text_input("Marque *", placeholder="ex : Hydra+")
            product_type = st.text_input("Type de produit *", placeholder="ex : gourde isotherme")
        with c2:
            materiau = st.text_input("Matériau", placeholder="ex : inox")
            couleur = st.text_input("Couleur", placeholder="ex : bleu nuit")

        infos_produits = st.text_area(
            "Infos produits (séparées par des virgules)",
            placeholder="750ml, garde le froid 24h, sans BPA, anse de transport...",
            height=100,
        )

        image_url = st.text_input(
            "URL de l'image principale (déjà hébergée)",
            placeholder="https://...",
            help="L'image doit être déjà hébergée en ligne (Drive, serveur...). "
                 "Attention : un lien de partage Google Drive classique ne fonctionne "
                 "pas tel quel, il faut un lien d'accès direct à l'image.",
        )

        images_secondaires_brut = st.text_area(
            "URLs des images secondaires (optionnel, séparées par des virgules)",
            placeholder="https://..., https://...",
            height=70,
            help="Amazon est plus souple sur ces images (pas de fond blanc requis).",
        )

        submitted = st.form_submit_button("Générer la fiche optimisée", type="primary")

    if submitted:
        if not brand or not product_type:
            st.error("Marque et Type de produit sont obligatoires.")
        else:
            if infos_produits and "," not in infos_produits and len(infos_produits.split()) > 6:
                st.warning(
                    "💡 Le champ 'Infos produits' ne contient pas de virgule : il sera "
                    "traité comme une seule information. Pour de meilleurs résultats, "
                    "sépare chaque info par une virgule (ex: 150x80cm, made in France, "
                    "facile à nettoyer)."
                )
            raw_input = {
                "marque": brand,
                "type_produit": product_type,
                "materiau": materiau,
                "couleur": couleur,
                "infos_produits": infos_produits,
                "image_url": image_url,
                "images_secondaires": parser_urls(images_secondaires_brut),
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
        "Le fichier Excel doit contenir les colonnes : `marque` * , "
        "`type_produit` * , `materiau`, `couleur`, `infos_produits`, "
        "`image_url`, `images_secondaires` (* obligatoires ; infos et "
        "URLs séparées par des virgules dans la cellule)."
    )

    template_df = pd.DataFrame([
        {"marque": "Hydra+", "type_produit": "gourde isotherme", "materiau": "inox",
         "couleur": "bleu nuit",
         "infos_produits": "750ml, garde le froid 24h, sans BPA, anse de transport",
         "image_url": "https://...", "images_secondaires": ""},
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

        verifier_images = st.checkbox(
            "Vérifier aussi la conformité des images (plus lent : 1 téléchargement par image)",
            value=True,
        )

        if st.button("Générer toutes les fiches", type="primary"):
            results = []
            lignes_export_amazon = []
            lignes_sans_virgule = 0
            lignes_incompletes = 0
            progress = st.progress(0, text="Génération en cours...")
            total = len(df_input)

            for i, row in df_input.iterrows():
                marque = str(row.get("marque", "")).strip()
                type_produit = str(row.get("type_produit", "")).strip()

                if not marque or not type_produit:
                    lignes_incompletes += 1
                    progress.progress((i + 1) / total, text=f"Produit {i + 1}/{total} traité")
                    continue

                infos = str(row.get("infos_produits", ""))
                if infos and "," not in infos and len(infos.split()) > 6:
                    lignes_sans_virgule += 1

                image_url = str(row.get("image_url", ""))
                images_secondaires = parser_urls(str(row.get("images_secondaires", "")))

                raw_input = {
                    "marque": marque,
                    "type_produit": type_produit,
                    "materiau": row.get("materiau", ""),
                    "couleur": row.get("couleur", ""),
                    "infos_produits": infos,
                    "image_url": image_url,
                    "images_secondaires": images_secondaires,
                }
                listing = generer_fiche(raw_input)
                report = evaluate_listing(listing)

                score_image = ""
                if verifier_images and image_url:
                    rapport_image = verifier_image(image_url, image_principale=True)
                    score_image = rapport_image["score"] if rapport_image["url_valide"] else "Erreur"

                results.append({
                    **{k: v for k, v in raw_input.items() if k != "images_secondaires"},
                    "nb_images_secondaires": len(images_secondaires),
                    "titre_optimise": listing["title"],
                    "description_marketing": listing["description"],
                    "bullets": " | ".join(listing.get("bullets", [])),
                    "backend_keywords": listing.get("backend_keywords", ""),
                    "categorie_suggeree": listing.get("category_suggestion", ""),
                    "attributs_specifiques": " | ".join(
                        f"{k}: {v}" for k, v in listing.get("attributs_specifiques", {}).items()
                    ),
                    "score_conformite_texte": report.score,
                    "score_conformite_image": score_image,
                })
                lignes_export_amazon.append(
                    generer_ligne_export_amazon(
                        raw_input, listing, image_url=image_url,
                        images_secondaires=images_secondaires, indice=i,
                    )
                )
                ajouter_a_historique(raw_input, listing, report.score, score_image or None)

                progress.progress((i + 1) / total, text=f"Produit {i + 1}/{total} traité")

            if lignes_incompletes:
                st.error(
                    f"⛔ {lignes_incompletes} ligne(s) ignorée(s) car 'marque' ou "
                    "'type_produit' (obligatoires) sont manquants."
                )
            if lignes_sans_virgule:
                st.warning(
                    f"💡 {lignes_sans_virgule} ligne(s) ont une colonne 'infos_produits' "
                    "sans virgule (traitée comme une seule information). Sépare chaque "
                    "info par une virgule pour de meilleurs résultats."
                )

            result_df = pd.DataFrame(results)
            st.session_state["batch_results"] = result_df
            st.session_state["batch_export_amazon"] = pd.DataFrame(lignes_export_amazon)

    if "batch_results" in st.session_state:
        export_buffer = io.BytesIO()
        st.session_state["batch_export_amazon"].to_excel(export_buffer, index=False, engine="openpyxl")
        st.download_button(
            "📤 Télécharger l'export façon Amazon (Excel, à copier-coller dans le vrai template)",
            data=export_buffer.getvalue(),
            file_name="export_amazon_lot.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        st.markdown("### Résultats détaillés")
        st.dataframe(st.session_state["batch_results"], use_container_width=True)

        result_buffer = io.BytesIO()
        st.session_state["batch_results"].to_excel(result_buffer, index=False, engine="openpyxl")
        st.download_button(
            "Télécharger les résultats détaillés (Excel)",
            data=result_buffer.getvalue(),
            file_name="fiches_optimisees.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


# ---------------------------------------------------------------------
# Onglet 3 : historique de la session
# ---------------------------------------------------------------------
with tab_historique:
    st.caption(
        "Historique des fiches générées pendant cette session uniquement "
        "(perdu si tu fermes ou recharges la page — pas de base de données)."
    )
    historique = st.session_state.get("historique", [])
    if not historique:
        st.info("Aucune fiche générée pour le moment.")
    else:
        historique_df = pd.DataFrame(historique)
        st.dataframe(historique_df, use_container_width=True)

        historique_buffer = io.BytesIO()
        historique_df.to_excel(historique_buffer, index=False, engine="openpyxl")
        st.download_button(
            "Télécharger l'historique (Excel)",
            data=historique_buffer.getvalue(),
            file_name="historique_session.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        if st.button("Vider l'historique"):
            st.session_state["historique"] = []
            st.rerun()
