"""
export_cdiscount.py
--------------------
Génère une ligne d'export au format Cdiscount Marketplace (via Octopia).

Spécifications encodées (sources : tutoriel officiel Cdiscount 2024,
ChannelEngine / Octopia guide 2024) :

- Référence vendeur   : max 50 caractères, caractères autorisés : lettres,
                        chiffres, _ - / et espace
- EAN                 : 13 chiffres obligatoires (ou "GENEAN" si absent)
- Titre               : max 132 caractères, format recommandé :
                        [Type produit] - [Marque] - [Mots-clés] - [Modèle]
                        Caractères interdits : ° © ® ™ ? et expressions régulières
- Description longue  : HTML autorisé (contrairement à Amazon), pas de limite
                        stricte mais ~2000 recommandés
- Description courte  : résumé de 5 points max, ~500 car.
- Marque              : obligatoire
- Image principale    : JPEG/GIF/PNG, 500x500 px min, 3000x3000 px max, 5 Mo max
- Couleur, matière    : attributs libres

Différence clé avec Amazon : sur Cdiscount, plusieurs vendeurs partagent
la même fiche produit. Si la fiche existe déjà (EAN reconnu), ce fichier
sert à créer l'OFFRE (prix, stock) et non la fiche elle-même. S'il s'agit
d'un nouveau produit, il sert à créer la fiche.
"""

import re
import unicodedata


TITRE_MAX = 132
DESCRIPTION_COURTE_MAX = 500
DESCRIPTION_LONGUE_MAX = 2000

CHARS_INTERDITS_CDISCOUNT = ["°", "©", "®", "™", "?"]


def _sans_accents_ref(texte: str) -> str:
    """Retire les accents pour générer une référence vendeur propre."""
    return "".join(
        c for c in unicodedata.normalize("NFD", texte)
        if unicodedata.category(c) != "Mn"
    )


def _nettoyer_reference(texte: str) -> str:
    """Génère une référence vendeur valide (max 50 car., caractères autorisés uniquement)."""
    texte_na = _sans_accents_ref(texte.lower())
    texte_propre = re.sub(r"[^a-z0-9_\-/ ]", "-", texte_na)
    texte_propre = re.sub(r"-+", "-", texte_propre).strip("-")
    return texte_propre[:50]


def _nettoyer_titre(titre: str) -> str:
    """Retire les caractères interdits par Cdiscount du titre."""
    for char in CHARS_INTERDITS_CDISCOUNT:
        titre = titre.replace(char, "")
    return titre[:TITRE_MAX]


def generer_titre_cdiscount(marque: str, type_produit: str, caracteristiques: list,
                             couleur: str) -> str:
    """
    Format recommandé Cdiscount :
    [Type produit] - [Marque] - [Mots-clés descriptifs]
    Limite : 132 caractères (vs 75 pour Amazon).
    """
    base = f"{type_produit.capitalize()} - {marque}"
    extras = [c for c in ([couleur] + caracteristiques[:3]) if c]
    if extras:
        titre = f"{base} - {', '.join(extras)}"
    else:
        titre = base
    return _nettoyer_titre(titre)


def generer_description_courte(bullets: list) -> str:
    """
    Cdiscount accepte une description courte (résumé en quelques points).
    On utilise les bullets déjà générés, en les joignant en texte simple.
    """
    lignes = [f"• {b}" for b in bullets[:5]]
    return "\n".join(lignes)[:DESCRIPTION_COURTE_MAX]


def generer_ligne_export_cdiscount(raw_input: dict, listing: dict,
                                    image_url: str = "", indice: int = None) -> dict:
    """
    Construit une ligne au format export Cdiscount à partir d'une fiche déjà
    générée. Les champs EAN et stock sont laissés vides (à compléter par le
    vendeur — l'outil ne peut pas les inventer).
    """
    marque = raw_input.get("marque", "")
    type_produit = raw_input.get("type_produit", "")
    couleur = raw_input.get("couleur", "")
    materiau = raw_input.get("materiau", "")
    infos_produits = raw_input.get("infos_produits", "")

    # Caractéristiques nettoyées (on reconstruit depuis infos_produits)
    caracteristiques = [c.strip() for c in infos_produits.split(",") if c.strip()]

    # Référence vendeur : SKU fourni ou généré
    ref_vendeur = raw_input.get("sku", "").strip()
    if not ref_vendeur:
        base_ref = f"{marque}-{type_produit}"
        if indice is not None:
            base_ref += f"-{indice + 1:03d}"
        ref_vendeur = _nettoyer_reference(base_ref)

    titre_cdiscount = generer_titre_cdiscount(
        marque, type_produit, caracteristiques, couleur
    )

    return {
        # Champs identification
        "reference_vendeur": ref_vendeur,
        "ean": raw_input.get("ean", "GENEAN"),
        "marque": marque,

        # Contenu de la fiche
        "titre": titre_cdiscount,
        "description_courte": generer_description_courte(listing.get("bullets", [])),
        "description_longue": listing.get("description", ""),

        # Attributs produit
        "couleur": couleur,
        "matiere": materiau,
        "categorie_suggereee": listing.get("category_suggestion", ""),

        # Image
        "image_principale": image_url,

        # Champs à compléter par le vendeur
        "prix_HT": "",
        "stock": "",
        "delai_livraison": "",

        # Méta
        "nb_caracteres_titre": len(titre_cdiscount),
        "note_export": (
            "EAN : renseigne le vrai code-barres produit (13 chiffres) ou laisse "
            "'GENEAN' si absent. Prix et stock à compléter avant import."
        ),
    }


if __name__ == "__main__":
    from generator import generer_fiche

    exemple = {
        "marque": "Hydra+", "type_produit": "gourde isotherme",
        "materiau": "inox", "couleur": "bleu nuit",
        "infos_produits": "750ml, garde le froid 24h, sans BPA",
    }
    listing = generer_fiche(exemple)
    ligne = generer_ligne_export_cdiscount(exemple, listing, indice=0)
    for k, v in ligne.items():
        print(f"{k:30s} : {v}")
