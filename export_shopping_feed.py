"""
export_shopping_feed.py
------------------------
Génère un flux au format Google Shopping (Google Merchant Center), qui
est le standard universel accepté par les outils de gestion de flux :
ShoppingFeed, Lengow, Channable, BeezUP, iziflux, etc.

Ces outils se connectent à votre boutique e-commerce (PrestaShop,
WooCommerce, Shopify) via plugin pour tirer le catalogue automatiquement,
mais ils acceptent aussi l'import d'un flux au format Google Shopping —
ce qui permet d'alimenter ces outils même sans boutique en ligne.

Une fois importé dans ShoppingFeed (ou Lengow, Channable...), l'outil
se charge de distribuer les produits dans le bon format vers chaque
marketplace connectée (Amazon, Cdiscount, Fnac Darty, Leroy Merlin...).

Colonnes du flux Google Shopping (standard GMC 2026) :
- id             : identifiant unique du produit (SKU)
- title          : titre produit (max 150 car.)
- description    : description longue (max 5000 car.)
- link           : URL de la fiche produit (à renseigner)
- image_link     : URL image principale
- additional_image_link : images secondaires (une colonne par image)
- availability   : disponibilité (in_stock / out_of_stock / preorder)
- price          : prix avec devise (ex: 29.99 EUR)
- condition      : état (new / refurbished / used)
- brand          : marque
- gtin           : EAN/UPC (code barre)
- mpn            : référence fabricant
- google_product_category : catégorie Google Taxonomy (numéro ou texte)
- product_type   : catégorie libre (hiérarchie avec >, ex: Maison > Cuisine)
- color          : couleur
- material       : matériau
- item_group_id  : groupe de variantes (même produit, couleurs/tailles diff.)
"""

# Mapping catégories internes → Google Product Taxonomy (IDs numériques 2026)
# Source : https://support.google.com/merchants/answer/6324436
GOOGLE_TAXONOMY = {
    "Cuisine & Maison":        "638",   # Home & Garden > Kitchen & Dining
    "Électroménager":          "604",   # Home & Garden > Household Appliances
    "High-Tech":               "222",   # Electronics
    "Sport & Plein air":       "990",   # Sporting Goods
    "Bagagerie & Voyage":      "110",   # Luggage & Bags
    "Animalerie":              "1",     # Animals & Pet Supplies
    "Maison & Luminaire":      "594",   # Home & Garden > Lighting
    "Jardin & Extérieur":      "689",   # Home & Garden > Lawn & Garden
    "Bricolage & Outillage":   "632",   # Hardware > Tools
    "Mode & Vêtements":        "1604",  # Apparel & Accessories
    "Bijoux & Montres":        "188",   # Apparel & Accessories > Jewelry
    "Beauté & Santé":          "469",   # Health & Beauty
    "Hygiène & Santé":         "491",   # Health & Beauty > Personal Care
    "Bébé & Puériculture":     "537",   # Baby & Toddler
    "Jouets & Jeux":           "1239",  # Toys & Games
    "Fournitures de bureau":   "922",   # Office Supplies
    "Instruments de musique":  "395",   # Musical Instruments
    "Mobilier & Décoration":   "436",   # Furniture
    "Epicerie & Boissons":     "422",   # Food, Beverages & Tobacco
    "Auto & Moto":             "5613",  # Vehicles & Parts
    "Autre":                   "0",
}

TITRE_MAX = 150
DESCRIPTION_MAX = 5000


def generer_flux_shopping_feed(raw_input: dict, listing: dict,
                                image_url: str = "",
                                images_secondaires: list = None,
                                indice: int = None) -> dict:
    """
    Construit une ligne au format Google Shopping / flux universel
    compatible ShoppingFeed, Lengow, Channable et autres outils de
    gestion de flux e-commerce.

    Les champs 'price' et 'link' sont laissés vides : le prix relève
    de la stratégie commerciale du vendeur, et l'URL de fiche dépend
    de sa boutique en ligne.
    """
    marque = raw_input.get("marque", "")
    type_produit = raw_input.get("type_produit", "")
    couleur = raw_input.get("couleur", "")
    materiau = raw_input.get("materiau", "")
    images_secondaires = images_secondaires or []

    # SKU comme identifiant unique
    sku = raw_input.get("sku", "").strip()
    if not sku:
        import re
        import unicodedata
        base = f"{marque}-{type_produit}".lower()
        base = "".join(
            c for c in unicodedata.normalize("NFD", base)
            if unicodedata.category(c) != "Mn"
        )
        base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
        if indice is not None:
            base += f"-{indice + 1:03d}"
        sku = base[:50]

    categorie = listing.get("category_suggestion", "Autre")

    titre = listing.get("title", f"{marque} {type_produit}".strip())[:TITRE_MAX]
    description = listing.get("description", "")[:DESCRIPTION_MAX]

    ligne = {
        # Champs obligatoires Google Shopping
        "id": sku,
        "title": titre,
        "description": description,
        "link": "",                  # URL fiche produit — à renseigner
        "image_link": image_url,
        "availability": "in_stock",  # par défaut
        "price": "",                 # ex: 29.99 EUR — à renseigner
        "condition": "new",

        # Identification produit
        "brand": marque,
        "gtin": raw_input.get("ean", ""),  # EAN/code barre
        "mpn": sku,                          # référence fabricant = SKU par défaut

        # Catégories
        "google_product_category": GOOGLE_TAXONOMY.get(categorie, "0"),
        "product_type": categorie,

        # Attributs
        "color": couleur,
        "material": materiau,
        "item_group_id": "",  # à renseigner si variantes (tailles, couleurs)

        # Mots-clés (champ custom accepté par la plupart des outils)
        "custom_label_0": listing.get("backend_keywords", "")[:100],

        # Bullets en custom_label (utilisés par certains outils pour les attributs)
        "custom_label_1": listing.get("bullets", [""])[0][:100] if listing.get("bullets") else "",
        "custom_label_2": listing.get("bullets", ["", ""])[1][:100] if len(listing.get("bullets", [])) > 1 else "",
    }

    # Images secondaires
    for i, url in enumerate(images_secondaires[:8], start=1):
        ligne[f"additional_image_link_{i}"] = url

    return ligne


if __name__ == "__main__":
    from generator import generer_fiche

    exemples = [
        {"marque": "SoundWave", "type_produit": "ecouteurs bluetooth",
         "materiau": "plastique", "couleur": "noir",
         "infos_produits": "bluetooth 5.3, autonomie 30h"},
        {"marque": "DesignHome", "type_produit": "table basse",
         "materiau": "verre", "couleur": "transparent",
         "infos_produits": "150 x 80 cm, made in France"},
    ]
    for ex in exemples:
        listing = generer_fiche(ex)
        ligne = generer_flux_shopping_feed(ex, listing, indice=0)
        print(f"\n--- {ex['marque']} ---")
        for k, v in ligne.items():
            if v:
                print(f"  {k:30s} : {v}")
