"""
export_maisons_du_monde.py
---------------------------
Génère une ligne d'export au format Maisons du Monde Marketplace (Mirakl).

Spécifications encodées (sources : ChannelEngine MdM guide 2024,
BeezUP MdM help, documentation Mirakl MdM) :

- EAN (ean_code)      : EAN-8 ou EAN-13 obligatoire. Tout produit sans
                        EAN valide est rejeté automatiquement.
- Titre               : descriptif, SEO-friendly.
- Matériau principal  : doit correspondre à une valeur connue de MdM
                        (liste en anglais dans leur back-office, traduite
                        en français sur le site). Ex: "metal", "wood",
                        "fabric", "glass", "plastic".
- Dimensions          : hauteur, largeur, longueur en cm (sans emballage).
- DEA                 : Déchets d'Éléments d'Ameublement — OBLIGATOIRE
                        pour les marchands français vendant du mobilier
                        (valeur numérique en euros).
- Images              : image principale + jusqu'à 9 images secondaires
                        (Media 2 à 10).

Contexte : MdM est spécialisé décoration et mobilier. Marketplace
sélective tournant sur Mirakl. Audience : acheteurs recherchant style
et design pour la maison. Idéal pour : meubles, luminaires, textiles
maison, vaisselle, déco.
"""

import re
import unicodedata


# Mapping des matériaux courants vers les valeurs attendues par MdM
MATERIAUX_MDM = {
    "inox": "metal",
    "acier": "metal",
    "aluminium": "metal",
    "fer": "metal",
    "metal": "metal",
    "métal": "metal",
    "bois": "wood",
    "chêne": "wood",
    "pin": "wood",
    "mdf": "wood",
    "verre": "glass",
    "glass": "glass",
    "plastique": "plastic",
    "pvc": "plastic",
    "tissu": "fabric",
    "velours": "fabric",
    "coton": "fabric",
    "lin": "fabric",
    "cuir": "leather",
    "marbre": "marble",
    "ceramique": "ceramic",
    "céramique": "ceramic",
    "porcelaine": "ceramic",
    "rotin": "rattan",
    "osier": "rattan",
    "bambou": "bamboo",
    "béton": "concrete",
    "pierre": "stone",
}


def _sans_accents(texte: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texte)
        if unicodedata.category(c) != "Mn"
    )


def _mapper_materiau(materiau: str) -> str:
    """Convertit le matériau libre vers une valeur reconnue par MdM."""
    if not materiau:
        return ""
    materiau_na = _sans_accents(materiau.lower().strip())
    for mot, valeur in MATERIAUX_MDM.items():
        if mot in materiau_na:
            return valeur
    return materiau.lower()  # valeur libre si non reconnue


def _nettoyer_sku(texte: str) -> str:
    texte_propre = re.sub(r"[^a-zA-Z0-9\-_]", "-", texte)
    return re.sub(r"-+", "-", texte_propre).strip("-")[:50]


def generer_ligne_export_maisons_du_monde(raw_input: dict, listing: dict,
                                           image_url: str = "",
                                           images_secondaires: list = None,
                                           indice: int = None) -> dict:
    """
    Construit une ligne au format Maisons du Monde Marketplace (Mirakl).
    """
    marque = raw_input.get("marque", "")
    type_produit = raw_input.get("type_produit", "")
    couleur = raw_input.get("couleur", "")
    materiau = raw_input.get("materiau", "")
    images_secondaires = images_secondaires or []

    sku = raw_input.get("sku", "").strip()
    if not sku:
        base = f"{marque}-{type_produit}"
        if indice is not None:
            base += f"-{indice + 1:03d}"
        sku = _nettoyer_sku(base)

    attributs = listing.get("attributs_specifiques", {})

    ligne = {
        # Identification
        "seller_product_id": sku,
        "ean_code": raw_input.get("ean", ""),  # EAN obligatoire
        "brand": marque,

        # Contenu
        "title": f"{marque} {type_produit}".strip()[:200],
        "description": listing.get("description", ""),
        "short_description": " | ".join(listing.get("bullets", [])[:3]),

        # Catégorie
        "product_type": listing.get("category_suggestion", ""),

        # Attributs produit (spécifiques MdM)
        "main_material": _mapper_materiau(materiau),
        "color": couleur,

        # Dimensions SANS emballage (en cm) - importantes pour MdM
        "height": attributs.get("Hauteur (cm)", ""),
        "width": attributs.get("Largeur (cm)", ""),
        "length": attributs.get("Longueur (cm)", ""),
        "measurement_unit_height": "cm",
        "measurement_unit_width": "cm",
        "measurement_unit_length": "cm",

        # DEA - Déchets d'Éléments d'Ameublement
        # Obligatoire pour marchands FR vendant du mobilier.
        # Valeur en euros, fournie par l'éco-organisme (Eco-mobilier).
        "dea_value": "",  # à compléter par le vendeur

        # Image principale
        "main_image_url": image_url,

        # Offre
        "price": "",
        "stock": "",
        "lead_time_to_ship": "",

        # Méta
        "note_export": (
            "⚠️ EAN obligatoire — tout produit sans EAN valide est rejeté. "
            "DEA (Déchets d'Éléments d'Ameublement) obligatoire pour le mobilier "
            "en France : valeur fournie par Eco-mobilier. "
            "Matériau mappé automatiquement vers les valeurs MdM."
        ),
    }

    # Images secondaires (Media 2 à 10)
    for i, url in enumerate(images_secondaires[:9], start=2):
        ligne[f"media_{i}"] = url

    return ligne


if __name__ == "__main__":
    from generator import generer_fiche

    exemple = {
        "marque": "DesignHome", "type_produit": "table basse",
        "materiau": "verre", "couleur": "transparent",
        "infos_produits": "150 x 80 cm, made in France, facile a nettoyer",
    }
    listing = generer_fiche(exemple)
    ligne = generer_ligne_export_maisons_du_monde(exemple, listing, indice=0)
    for k, v in ligne.items():
        print(f"{k:25s} : {v}")
