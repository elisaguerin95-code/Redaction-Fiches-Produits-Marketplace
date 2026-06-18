"""
export_amazon.py
------------------
Construit une ligne d'export avec les noms de colonnes standards qu'on
retrouve dans la plupart des flat files Amazon (item_name, brand_name,
bullet_point1-5, product_description, generic_keywords, color_name,
material_type, main_image_url...).

Important : Amazon génère un template DIFFÉRENT pour chaque catégorie,
téléchargé depuis Seller Central -> on ne peut pas reproduire le fichier
exact sans cet accès. Cet export n'est donc pas un import direct, mais
un fichier pensé pour être copié-collé dans le vrai template une fois
téléchargé pour la bonne catégorie : il couvre les colonnes communes à
la quasi-totalité des catégories.
"""

import re


def generer_sku(marque: str, type_produit: str, indice: int = None) -> str:
    """Génère un SKU lisible à partir de la marque et du type de produit (placeholder, à remplacer par le vrai SKU interne si besoin)."""
    base = f"{marque}-{type_produit}".lower()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    if indice is not None:
        base = f"{base}-{indice + 1:03d}"
    return base or "sku-a-completer"


def generer_ligne_export_amazon(raw_input: dict, listing: dict, image_url: str = "",
                                 indice: int = None) -> dict:
    """
    Construit une ligne au format export Amazon à partir d'une fiche déjà
    générée. Les attributs spécifiques à la catégorie (Capacité, Étanche...)
    sont ajoutés comme colonnes supplémentaires.
    """
    bullets = listing.get("bullets", [])
    bullets_completes = bullets + [""] * (5 - len(bullets))  # sécurité si moins de 5

    ligne = {
        "item_sku": generer_sku(raw_input.get("marque", ""), raw_input.get("type_produit", ""), indice),
        "item_name": listing.get("title", ""),
        "brand_name": raw_input.get("marque", ""),
        "manufacturer": raw_input.get("marque", ""),
        "bullet_point1": bullets_completes[0],
        "bullet_point2": bullets_completes[1],
        "bullet_point3": bullets_completes[2],
        "bullet_point4": bullets_completes[3],
        "bullet_point5": bullets_completes[4],
        "product_description": listing.get("description", ""),
        "generic_keywords": listing.get("backend_keywords", ""),
        "color_name": raw_input.get("couleur", ""),
        "material_type": raw_input.get("materiau", ""),
        "main_image_url": image_url,
        "feed_product_type": listing.get("category_suggestion", ""),
    }

    # on ajoute les attributs spécifiques détectés (Capacité, Étanche...)
    ligne.update(listing.get("attributs_specifiques", {}))

    return ligne


if __name__ == "__main__":
    from generator import generer_fiche

    exemple_input = {
        "marque": "Hydra+", "type_produit": "gourde isotherme",
        "materiau": "inox", "couleur": "bleu nuit",
        "infos_produits": "750ml, garde le froid 24h, sans BPA, anse de transport",
    }
    listing = generer_fiche(exemple_input)
    ligne = generer_ligne_export_amazon(exemple_input, listing, image_url="https://exemple.com/photo.jpg")
    for cle, valeur in ligne.items():
        print(f"{cle:20s} : {valeur}")
