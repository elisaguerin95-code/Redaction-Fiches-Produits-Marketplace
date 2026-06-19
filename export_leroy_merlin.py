"""
export_leroy_merlin.py
-----------------------
Génère une ligne d'export au format Leroy Merlin Marketplace (Mirakl).

Spécifications encodées (sources : ChannelEngine Leroy Merlin guide,
BeezUP Help Center, iziflux.com 2024-2026) :

- EAN (product_identifier) : EAN-13 obligatoire. Sans EAN valide, le
  produit ne peut pas être créé ("The product doesn't exist").
- Marque (brand)           : obligatoire. Si marque inconnue de LM,
  contacter LM pour ajout ou utiliser "Autre".
- Titre                    : clair et descriptif, SEO-friendly.
- Description              : texte long, pas de limite stricte.
- Dimensions               : hauteur, largeur, longueur en cm.
  Importantes pour LM qui vend beaucoup de produits avec contraintes
  de livraison (encombrement).
- Images                   : URL directes, plusieurs autorisées.

Contexte : Leroy Merlin est une marketplace sélective (expertise
bricolage / amélioration de l'habitat requise). 19,2M visiteurs uniques
mensuels, top 3 marques préférées des Français.

Catégories privilégiées : bricolage, outillage, jardin, luminaires,
cuisine, salle de bain, décoration maison.
"""

import re
import unicodedata


TITRE_MAX = 200


def _nettoyer_sku(texte: str) -> str:
    texte_propre = re.sub(r"[^a-zA-Z0-9\-_]", "-", texte)
    return re.sub(r"-+", "-", texte_propre).strip("-")[:50]


def generer_ligne_export_leroy_merlin(raw_input: dict, listing: dict,
                                       image_url: str = "", indice: int = None) -> dict:
    """
    Construit une ligne au format Leroy Merlin Marketplace (Mirakl).
    Les dimensions et le poids sont extraits automatiquement des
    attributs spécifiques déjà détectés par generator.py si disponibles.
    """
    marque = raw_input.get("marque", "")
    type_produit = raw_input.get("type_produit", "")
    couleur = raw_input.get("couleur", "")
    materiau = raw_input.get("materiau", "")

    sku = raw_input.get("sku", "").strip()
    if not sku:
        base = f"{marque}-{type_produit}"
        if indice is not None:
            base += f"-{indice + 1:03d}"
        sku = _nettoyer_sku(base)

    # Récupération des attributs techniques déjà extraits
    attributs = listing.get("attributs_specifiques", {})

    titre = f"{marque} {type_produit}".strip()
    if couleur:
        titre += f" {couleur}"
    titre = titre[:TITRE_MAX]

    return {
        # Identification
        "seller_product_id": sku,
        "product_identifier": raw_input.get("ean", ""),   # EAN-13 obligatoire
        "brand": marque or "Autre",

        # Contenu
        "title": titre,
        "description": listing.get("description", ""),
        "short_description": " | ".join(listing.get("bullets", [])[:3]),
        "keywords": listing.get("backend_keywords", ""),

        # Catégorie
        "category": listing.get("category_suggestion", ""),

        # Attributs produit
        "color": couleur,
        "main_material": materiau,

        # Dimensions (à compléter par le vendeur si non détectées)
        "height_cm": attributs.get("Hauteur (cm)", ""),
        "width_cm": attributs.get("Largeur (cm)", ""),
        "length_cm": attributs.get("Longueur (cm)", ""),
        "weight_kg": attributs.get("Poids (kg)", ""),

        # Images
        "main_image_url": image_url,

        # Offre (à compléter)
        "price": "",
        "stock": "",
        "lead_time_to_ship": "",

        # Méta
        "note_export": (
            "⚠️ EAN-13 obligatoire — sans EAN valide le produit est rejeté. "
            "Si votre marque n'est pas reconnue par LM, contactez-les pour l'ajouter "
            "ou utilisez 'Autre'. Dimensions à compléter si pertinentes."
        ),
    }


if __name__ == "__main__":
    from generator import generer_fiche

    exemple = {
        "marque": "LumiHome", "type_produit": "lampe de bureau led",
        "materiau": "aluminium", "couleur": "blanc",
        "infos_produits": "3 temperatures, variateur tactile, port usb",
    }
    listing = generer_fiche(exemple)
    ligne = generer_ligne_export_leroy_merlin(exemple, listing, indice=0)
    for k, v in ligne.items():
        print(f"{k:25s} : {v}")
