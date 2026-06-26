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
import os
from datetime import datetime

import streamlit as st
import pandas as pd

from generator import generer_fiche
from rules import evaluate_listing
from image_check import verifier_image
from export_amazon import generer_ligne_export_amazon
from export_cdiscount import generer_ligne_export_cdiscount
from export_fnac_darty import generer_ligne_export_fnac_darty
from export_leroy_merlin import generer_ligne_export_leroy_merlin
from export_maisons_du_monde import generer_ligne_export_maisons_du_monde
from marketplace_registry import (
    get_marketplaces_suggereees, get_marketplace_info, MARKETPLACES
)

st.set_page_config(
    page_title="Création Fiche Produit Marketplace",
    page_icon="🏷️",
    layout="wide",
)

# ── Injection CSS ────────────────────────────────────────────────
def _inject_styles():
    css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
    with open(css_path, encoding="utf-8") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

_inject_styles()

# ── Hero header (HTML custom, pas st.title générique) ───────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600&display=swap');
</style>

<div style="
  position: relative;
  padding: 2.25rem 0 1.75rem;
  border-bottom: 1px solid #2E3545;
  margin-bottom: 1.5rem;
  overflow: hidden;
  min-height: 130px;
">
  <!-- Dot pattern -->
  <div style="
    position: absolute; inset: 0;
    background-image: radial-gradient(circle, rgba(58,68,85,0.9) 1px, transparent 1px);
    background-size: 22px 22px;
    opacity: 0.55;
    pointer-events: none;
  "></div>
  <!-- Fade gauche/droite -->
  <div style="
    position: absolute; inset: 0;
    background: linear-gradient(90deg, #1E2128 0%, rgba(30,33,40,0.4) 30%, rgba(30,33,40,0.4) 60%, #1E2128 100%);
    pointer-events: none;
  "></div>
  <!-- SVG étiquettes — ancrées en bas à droite pour rester visibles -->
  <div style="
    position: absolute;
    right: 2rem; bottom: -8px;
    opacity: 0.22; pointer-events: none;
    line-height: 0;
  ">
    <svg xmlns="http://www.w3.org/2000/svg" width="160" height="110" viewBox="0 0 160 110">
      <!-- Étiquette principale légèrement inclinée -->
      <g transform="rotate(-10, 65, 55)">
        <path d="M28,16 L28,92 Q28,99 35,99 L82,99 Q89,99 89,92 L89,16 Q89,9 82,9 L35,9 Q28,9 28,16 Z"
              fill="none" stroke="#C4606E" stroke-width="1.5"/>
        <circle cx="58" cy="4" r="4" fill="none" stroke="#C4606E" stroke-width="1.5"/>
        <line x1="58" y1="0" x2="58" y2="9" stroke="#C4606E" stroke-width="1.5" stroke-linecap="round"/>
        <text x="58" y="57" text-anchor="middle" font-family="Georgia,serif" font-style="italic" font-size="14" fill="#C4606E">✦</text>
        <line x1="35" y1="73" x2="35" y2="85" stroke="#C4606E" stroke-width="2.5"/>
        <line x1="39" y1="73" x2="39" y2="85" stroke="#C4606E" stroke-width="1"/>
        <line x1="43" y1="73" x2="43" y2="85" stroke="#C4606E" stroke-width="3"/>
        <line x1="47" y1="73" x2="47" y2="85" stroke="#C4606E" stroke-width="1"/>
        <line x1="51" y1="73" x2="51" y2="85" stroke="#C4606E" stroke-width="2"/>
        <line x1="55" y1="73" x2="55" y2="85" stroke="#C4606E" stroke-width="1"/>
        <line x1="59" y1="73" x2="59" y2="85" stroke="#C4606E" stroke-width="3"/>
        <line x1="63" y1="73" x2="63" y2="85" stroke="#C4606E" stroke-width="1"/>
        <line x1="67" y1="73" x2="67" y2="85" stroke="#C4606E" stroke-width="2"/>
        <line x1="71" y1="73" x2="71" y2="85" stroke="#C4606E" stroke-width="1.5"/>
        <line x1="75" y1="73" x2="75" y2="85" stroke="#C4606E" stroke-width="2.5"/>
        <line x1="79" y1="73" x2="79" y2="85" stroke="#C4606E" stroke-width="1"/>
        <line x1="83" y1="73" x2="83" y2="85" stroke="#C4606E" stroke-width="1.5"/>
      </g>
      <!-- Étiquette secondaire -->
      <g transform="rotate(7, 120, 45) translate(82, 8)">
        <path d="M8,13 L8,72 Q8,77 13,77 L52,77 Q57,77 57,72 L57,13 Q57,8 52,8 L13,8 Q8,8 8,13 Z"
              fill="none" stroke="#D4826E" stroke-width="1.2" opacity="0.75"/>
        <circle cx="32" cy="4" r="3.5" fill="none" stroke="#D4826E" stroke-width="1.2" opacity="0.75"/>
        <line x1="32" y1="0.5" x2="32" y2="8" stroke="#D4826E" stroke-width="1.2" stroke-linecap="round" opacity="0.75"/>
        <line x1="15" y1="28" x2="50" y2="28" stroke="#D4826E" stroke-width="0.8" opacity="0.5"/>
        <line x1="15" y1="38" x2="43" y2="38" stroke="#D4826E" stroke-width="0.8" opacity="0.5"/>
        <line x1="15" y1="48" x2="47" y2="48" stroke="#D4826E" stroke-width="0.8" opacity="0.5"/>
      </g>
    </svg>
  </div>
  <!-- Contenu -->
  <div style="position: relative; z-index: 1;">
    <p style="font-family:'DM Sans',sans-serif; font-size:0.65rem; font-weight:600; text-transform:uppercase; letter-spacing:0.18em; color:#C4606E; margin:0 0 0.45rem;">✦ &nbsp;Outil catalogue marketplace</p>
    <h1 style="font-family:'DM Serif Display',Georgia,serif; font-size:2.2rem; font-weight:400; color:#F4F1EA; margin:0 0 0.55rem; line-height:1.15; letter-spacing:-0.02em;">
      Création Fiche Produit<br>
      <em style="color:#8A9BB0; font-style:italic;">Marketplace</em>
    </h1>
    <p style="font-family:'DM Sans',sans-serif; font-size:0.82rem; color:#6E7A8A; margin:0; max-width:460px; line-height:1.65;">
      Une saisie, plusieurs exports — Amazon, Cdiscount, Fnac Darty,<br>Leroy Merlin et Maisons du Monde.
    </p>
  </div>
</div>
""", unsafe_allow_html=True)

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
tab_single, tab_batch, tab_historique = st.tabs(["Fiche unique", "Lot (Excel)", "Historique"])


def _section_label(texte: str):
    """En-tête de section avec bordure gauche terracotta."""
    st.markdown(f"""
    <div style="
      border-left: 2px solid #C4606E;
      padding-left: 10px;
      margin: 1.25rem 0 0.6rem;
    ">
      <span style="
        font-family: 'DM Sans', sans-serif;
        font-size: 0.65rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #8A9BB0;
      ">{texte}</span>
    </div>
    """, unsafe_allow_html=True)


def afficher_bloc_conformite(titre: str, score: float, checks: list, cle_expander: str):
    """Bloc réutilisé pour le texte ET l'image : note + icône + détail dépliable."""
    st.markdown("---")
    st.subheader(titre)
    score_col, grade_col = st.columns([1, 3])
    with score_col:
        st.metric("Score de conformité", f"{score}/100")
    with grade_col:
        st.markdown(f"### {icone_depuis_score(score)} {grade_depuis_score(score)}")
    if f"{cle_expander}_open" not in st.session_state:
        st.session_state[f"{cle_expander}_open"] = False
    label_bouton = "▾ Voir le détail des vérifications" if st.session_state[f"{cle_expander}_open"] else "▸ Voir le détail des vérifications"
    if st.button(label_bouton, key=f"{cle_expander}_btn"):
        st.session_state[f"{cle_expander}_open"] = not st.session_state[f"{cle_expander}_open"]
    if st.session_state[f"{cle_expander}_open"]:
        for c in checks:
            icon = "✅" if (c["passed"] if isinstance(c, dict) else c.passed) else "⚠️"
            label = c["label"] if isinstance(c, dict) else c.label
            detail = c["detail"] if isinstance(c, dict) else c.detail
            st.markdown(f"{icon} **{label}** — {detail}")


MARKETPLACES_SUPPORTEES = ["amazon", "cdiscount", "fnac_darty", "leroy_merlin", "maisons_du_monde"]


def generer_exports_marketplaces(raw_input: dict, listing: dict,
                                  marketplaces_selectionnees: list,
                                  image_url: str, images_secondaires: list) -> dict:
    """Génère les fichiers d'export pour chaque marketplace sélectionnée."""
    exports = {}
    for cle in marketplaces_selectionnees:
        if cle == "amazon":
            exports["amazon"] = pd.DataFrame([generer_ligne_export_amazon(
                raw_input, listing, image_url=image_url, images_secondaires=images_secondaires)])
        elif cle == "cdiscount":
            exports["cdiscount"] = pd.DataFrame([generer_ligne_export_cdiscount(
                raw_input, listing, image_url=image_url)])
        elif cle == "fnac_darty":
            exports["fnac_darty"] = pd.DataFrame([generer_ligne_export_fnac_darty(
                raw_input, listing, image_url=image_url)])
        elif cle == "leroy_merlin":
            exports["leroy_merlin"] = pd.DataFrame([generer_ligne_export_leroy_merlin(
                raw_input, listing, image_url=image_url)])
        elif cle == "maisons_du_monde":
            exports["maisons_du_monde"] = pd.DataFrame([generer_ligne_export_maisons_du_monde(
                raw_input, listing, image_url=image_url, images_secondaires=images_secondaires)])
    return exports


def render_result(raw_input: dict, listing: dict):
    """Affiche les exports, le avant/après, les scores de conformité et l'image."""
    report = evaluate_listing(listing)
    image_url = raw_input.get("image_url", "")
    images_secondaires = raw_input.get("images_secondaires", [])
    categorie = listing.get("category_suggestion", "Autre")
    marketplaces_selectionnees = raw_input.get("marketplaces", ["amazon"])

    # --- Section exports ---
    _section_label("Exports")
    st.markdown("---")

    # Alertes de pertinence
    marketplaces_suggerees = get_marketplaces_suggereees(categorie)
    non_pertinentes = [
        cle for cle in marketplaces_selectionnees
        if cle not in marketplaces_suggerees
    ]
    for cle in non_pertinentes:
        info = get_marketplace_info(cle)
        suggerees_noms = [
            get_marketplace_info(k).get("nom", k)
            for k in marketplaces_suggerees
            if k in MARKETPLACES_SUPPORTEES
        ]
        st.warning(
            f"⚠️ **{info.get('nom', cle)}** est peu adapté à la catégorie "
            f"**{categorie}** — les marketplaces recommandées sont : "
            f"{', '.join(suggerees_noms[:3])}. Tu peux quand même générer l'export."
        )

    if not marketplaces_selectionnees:
        st.info("Aucune marketplace ou outil sélectionné — coche au moins une option en haut de page.")
    else:
        exports = generer_exports_marketplaces(
            raw_input, listing, marketplaces_selectionnees,
            image_url, images_secondaires,
        )
        tous_les_exports = list(exports.keys())
        if tous_les_exports:
            dl_cols = st.columns(min(len(tous_les_exports), 3))
            for idx, cle in enumerate(tous_les_exports):
                buf = io.BytesIO()
                exports[cle].to_excel(buf, index=False, engine="openpyxl")
                nom_fichier = f"export_{cle}.xlsx"
                if cle == "shopping_feed":
                    label = "⬇️ Flux Google Shopping"
                else:
                    info = get_marketplace_info(cle)
                    label = f"⬇️ {info.get('emoji','')} {info.get('nom', cle)}"
                with dl_cols[idx % 3]:
                    st.download_button(
                        label, data=buf.getvalue(), file_name=nom_fichier,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_{cle}",
                    )

    _section_label("Fiche générée")
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
    # ── Sélection marketplace : une seule sélection avec logo + case à cocher ──
    _section_label("Marketplaces cibles")
    st.caption("Coche les marketplaces pour lesquelles tu veux générer un export.")

    MARKETPLACE_META = [
        ("amazon", "Amazon", "amazon.fr", True),
        ("cdiscount", "Cdiscount", "cdiscount.com", True),
        ("fnac_darty", "Fnac Darty", "fnac.com", False),
        ("leroy_merlin", "Leroy Merlin", "leroymerlin.fr", False),
        ("maisons_du_monde", "Maisons du Monde", "maisonsdumonde.com", False),
    ]

    selected_marketplaces = []
    mp_cols = st.columns(len(MARKETPLACE_META))

    for col, (key, name, domain, default_checked) in zip(mp_cols, MARKETPLACE_META):
        favicon = (
            "https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON"
            f"&fallback_opts=TYPE,SIZE,URL&url=https://{domain}&size=64"
        )
        with col:
            checked = st.checkbox(
                f"![{name}]({favicon}) **{name}**",
                value=default_checked,
                key=f"mp_{key}",
            )
            if checked:
                selected_marketplaces.append(key)

    st.markdown("---")

    # Le choix est hors du formulaire : sinon Streamlit ne rafraîchit pas l'affichage
    # des champs optionnels tant que le bouton de génération n'a pas été cliqué.
    with st.expander("Ajouter des caractéristiques optionnelles"):

    with st.form("single_listing_form"):
        c1, c2 = st.columns(2)
        with c1:
            brand = st.text_input("Marque *", placeholder="ex : Hydra+")
        with c2:
            product_type = st.text_input("Type de produit *", placeholder="ex : gourde isotherme")

        # Valeurs par défaut si les caractéristiques optionnelles ne sont pas affichées
        materiau = ""
        sku = ""
        couleur = ""
        fabricant = ""
        infos_produits = ""
        image_url = ""
        images_secondaires_brut = ""

        if afficher_caracteristiques:
            c3, c4 = st.columns(2)
            with c3:
                materiau = st.text_input("Matériau", placeholder="ex : inox")
                sku = st.text_input(
                    "SKU (référence interne)",
                    placeholder="ex : GRD-INOX-750-BN",
                    help="Laisse vide pour générer un SKU automatique à partir de la marque et du type de produit.",
                )
            with c4:
                couleur = st.text_input("Couleur", placeholder="ex : bleu nuit")
                fabricant = st.text_input(
                    "Fabricant",
                    placeholder="ex : Hydra+ SAS",
                    help="Si différent de la marque. Laisse vide pour utiliser la marque.",
                )

            infos_produits = st.text_area(
                "Infos produits",
                placeholder="Avec virgules : 750ml, garde le froid 24h, sans BPA\n"
                            "Ou texte libre : gourde isotherme 750ml garde le froid 24h sans BPA anse de transport",
                height=100,
                help="Séparés par des virgules ou en texte libre : le NLP (nltk + LEFFF) "
                     "extrait automatiquement les caractéristiques si aucune virgule n'est détectée.",
            )

            image_url = st.text_input(
                "URL de l'image principale (déjà hébergée)",
                placeholder="https://...",
                help="L'image doit être hébergée en ligne avec un lien direct vers le fichier. "
                     "Clic droit sur la photo → 'Copier l'adresse de l'image'.",
            )

            images_secondaires_brut = st.text_area(
                "URLs des images secondaires (séparées par des virgules)",
                placeholder="https://..., https://...",
                height=70,
                help="Amazon est plus souple sur ces images (pas de fond blanc requis).",
            )

        st.caption("* champs obligatoires")
        submitted = st.form_submit_button("🚀 Générer la fiche optimisée", type="primary")

    if submitted:
        if not brand or not product_type:
            st.error("Marque et Type de produit sont obligatoires.")
        else:
            raw_input = {
                "marque": brand,
                "type_produit": product_type,
                "materiau": materiau,
                "couleur": couleur,
                "infos_produits": infos_produits,
                "image_url": image_url,
                "images_secondaires": parser_urls(images_secondaires_brut),
                "sku": sku,
                "fabricant": fabricant,
                "marketplaces": selected_marketplaces,
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

    uploaded_file = st.file_uploader("Sélectionner un fichier Excel", type=["xlsx"])

    if uploaded_file is not None:
        df_input = pd.read_excel(uploaded_file)
        df_input = df_input.fillna("")  # évite les erreurs sur les cellules vides
        st.dataframe(df_input, use_container_width=True)

        verifier_images = st.checkbox(
            "Vérifier aussi la conformité des images (plus lent : 1 téléchargement par image)",
            value=True,
        )

        st.markdown("**Marketplaces à exporter :**")
        mp_cols = st.columns(3)
        with mp_cols[0]:
            export_amazon_lot = st.checkbox("📦 Amazon", value=True, key="lot_amazon")
        with mp_cols[1]:
            export_cdiscount_lot = st.checkbox("🛒 Cdiscount", value=True, key="lot_cdiscount")
        with mp_cols[2]:
            export_fnac_lot = st.checkbox("🎵 Fnac Darty", value=False, key="lot_fnac")

        if st.button("Générer toutes les fiches", type="primary"):
            results = []
            lignes_export_amazon = []
            lignes_export_cdiscount = []
            lignes_export_fnac = []
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
                if export_amazon_lot:
                    lignes_export_amazon.append(
                        generer_ligne_export_amazon(
                            raw_input, listing, image_url=image_url,
                            images_secondaires=images_secondaires, indice=i,
                        )
                    )
                if export_cdiscount_lot:
                    lignes_export_cdiscount.append(
                        generer_ligne_export_cdiscount(raw_input, listing, image_url=image_url, indice=i)
                    )
                if export_fnac_lot:
                    lignes_export_fnac.append(
                        generer_ligne_export_fnac_darty(raw_input, listing, image_url=image_url, indice=i)
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
            if lignes_export_amazon:
                st.session_state["batch_export_amazon"] = pd.DataFrame(lignes_export_amazon)
            if lignes_export_cdiscount:
                st.session_state["batch_export_cdiscount"] = pd.DataFrame(lignes_export_cdiscount)
            if lignes_export_fnac:
                st.session_state["batch_export_fnac"] = pd.DataFrame(lignes_export_fnac)

    if "batch_results" in st.session_state:
        st.markdown("### Télécharger les exports")
        dl_cols = st.columns(3)
        with dl_cols[0]:
            if "batch_export_amazon" in st.session_state:
                buf = io.BytesIO()
                st.session_state["batch_export_amazon"].to_excel(buf, index=False, engine="openpyxl")
                st.download_button(
                    "📦 Export Amazon",
                    data=buf.getvalue(), file_name="export_amazon_lot.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
        with dl_cols[1]:
            if "batch_export_cdiscount" in st.session_state:
                buf = io.BytesIO()
                st.session_state["batch_export_cdiscount"].to_excel(buf, index=False, engine="openpyxl")
                st.download_button(
                    "🛒 Export Cdiscount",
                    data=buf.getvalue(), file_name="export_cdiscount_lot.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
        with dl_cols[2]:
            if "batch_export_fnac" in st.session_state:
                buf = io.BytesIO()
                st.session_state["batch_export_fnac"].to_excel(buf, index=False, engine="openpyxl")
                st.download_button(
                    "🎵 Export Fnac Darty",
                    data=buf.getvalue(), file_name="export_fnac_darty_lot.xlsx",
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
