"""
export_fnac_darty.py
---------------------
Génère une ligne d'export au format Fnac Darty Portail Catalogue.

Spécifications encodées (sources : Fnac Darty Marketplace FAQ 2025,
BeezUP Help Center, ChannelEngine Fnac guide) :

- EAN/ISBN           : OBLIGATOIRE — tout produit sans EAN est rejeté
                       automatiquement (ERR_026). Pas de contournement possible
                       comme le "GENEAN" de Cdiscount.
- SKU (seller_id)    : identifiant unique vendeur, max 50 caractères
- Libellé (titre)    : titre du produit en français
- Typologie          : catégorie dans l'arborescence Fnac Darty
- Description        : description longue du produit
- Marque             : obligatoire
- Image principale   : URL directe obligatoire
- Format import      : CSV, JSON ou Excel (virgule comme séparateur CSV)

Depuis juillet 2025 : Fnac Mirakl est obsolète, tout passe par le
Portail Catalogue Fnac Darty (commun Fnac ET Darty — un seul fichier
pour les deux enseignes).

Point clé pour le pitch : Fnac Darty touche 29M visiteurs/mois,
idéal pour tech, culture et électroménager.
"""

import re
import unicodedata


LIBELLE_MAX = 200   # limite documentée Fnac Darty
DESCRIPTION_MAX = 5000


def _nettoyer_sku(texte: str) -> str:
    """SKU vendeur : max 50 caractères, alphanumérique + - _"""
    texte_propre = re.sub(r"[^a-zA-Z0-9\-_]", "-", texte)
    texte_propre = re.sub(r"-+", "-", texte_propre).strip("-")
    return texte_propre[:50]


def generer_libelle_fnac(marque: str, type_produit: str, caracteristiques: list,
                          couleur: str) -> str:
    """
    Fnac Darty n'impose pas un format aussi strict qu'Amazon ou Cdiscount
    pour le titre, mais privilégie la clarté et la pertinence SEO.
    On reprend le titre Amazon (déjà optimisé) en l'élargissant jusqu'à
    la limite Fnac (200 car. vs 75 pour Amazon).
    """
    base = f"{marque} {type_produit.strip()}"
    extras = [c for c in ([couleur] + caracteristiques[:4]) if c]
    if extras:
        libelle = f"{base} - {', '.join(extras)}"
    else:
        libelle = base
    return libelle[:LIBELLE_MAX]


def generer_ligne_export_fnac_darty(raw_input: dict, listing: dict,
                                     image_url: str = "", indice: int = None) -> dict:
    """
    Construit une ligne au format Portail Catalogue Fnac Darty à partir
    d'une fiche déjà générée.

    Champs EAN et stock laissés vides ou avec des placeholders clairs :
    l'outil ne peut pas inventer un EAN, c'est un code normalisé GS1.
    """
    marque = raw_input.get("marque", "")
    type_produit = raw_input.get("type_produit", "")
    couleur = raw_input.get("couleur", "")
    materiau = raw_input.get("materiau", "")
    infos_produits = raw_input.get("infos_produits", "")

    caracteristiques = [c.strip() for c in infos_produits.split(",") if c.strip()]

    # SKU : fourni par le vendeur ou généré
    sku = raw_input.get("sku", "").strip()
    if not sku:
        base_sku = f"{marque}-{type_produit}"
        if indice is not None:
            base_sku += f"-{indice + 1:03d}"
        sku = _nettoyer_sku(base_sku)

    libelle = generer_libelle_fnac(marque, type_produit, caracteristiques, couleur)

    # Description : bullets + description longue (Fnac accepte plus de texte qu'Amazon)
    bullets_texte = "\n".join(f"• {b}" for b in listing.get("bullets", []))
    description_complete = f"{bullets_texte}\n\n{listing.get('description', '')}".strip()

    return {
        # Champs obligatoires Fnac Darty
        "seller_id": sku,
        "ean": raw_input.get("ean", ""),  # vide = rejet automatique, avertissement dans l'app
        "libelle": libelle,
        "marque": marque,
        "typologie": listing.get("category_suggestion", ""),

        # Contenu
        "description": description_complete[:DESCRIPTION_MAX],
        "mots_cles": listing.get("backend_keywords", ""),

        # Attributs
        "couleur": couleur,
        "matiere": materiau,

        # Images
        "image_url_1": image_url,

        # Champs offre (à compléter par le vendeur)
        "prix": "",
        "stock": "",
        "delai_livraison_jours": "",

        # Méta
        "nb_caracteres_libelle": len(libelle),
        "note_export": (
            "⚠️ EAN OBLIGATOIRE — tout produit sans EAN valide est automatiquement "
            "rejeté par Fnac Darty (erreur ERR_026). Renseigne l'EAN avant import. "
            "Prix et stock à compléter."
        ),
    }


if __name__ == "__main__":
    from generator import generer_fiche

    exemple = {
        "marque": "SoundWave", "type_produit": "ecouteurs bluetooth",
        "materiau": "plastique recycle", "couleur": "noir mat",
        "infos_produits": "bluetooth 5.3, autonomie 30h, etanche ipx5",
    }
    listing = generer_fiche(exemple)
    ligne = generer_ligne_export_fnac_darty(exemple, listing, indice=0)
    for k, v in ligne.items():
        print(f"{k:30s} : {v}")
