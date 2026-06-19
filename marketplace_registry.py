"""
marketplace_registry.py
-------------------------
Table de correspondance entre catégories Amazon détectées et marketplaces
françaises pertinentes, avec les métadonnées de chaque marketplace
(nom affiché, logo emoji, spécificités à communiquer à l'utilisateur).

Aucune logique de génération ici — ce module est une source de données
pure, importée par app.py et les modules d'export.
"""

# ---------------------------------------------------------------------
# Métadonnées des marketplaces supportées
# ---------------------------------------------------------------------

MARKETPLACES = {
    "amazon": {
        "nom": "Amazon",
        "emoji": "📦",
        "description": "Généraliste n°1 en France",
        "note": "Export déjà inclus dans chaque fiche générée.",
        "ean_obligatoire": False,
    },
    "cdiscount": {
        "nom": "Cdiscount",
        "emoji": "🛒",
        "description": "Généraliste n°2 en France (groupe Casino / Octopia)",
        "note": "EAN recommandé (mettre GENEAN si absent). "
                "Titre max 132 car. — format : [Type] - [Marque] - [Mots-clés].",
        "ean_obligatoire": False,
    },
    "fnac_darty": {
        "nom": "Fnac Darty",
        "emoji": "🎵",
        "description": "Spécialiste culture, tech & électroménager (29M visiteurs/mois)",
        "note": "EAN obligatoire — tout produit sans EAN est rejeté automatiquement.",
        "ean_obligatoire": True,
    },
    "manomano": {
        "nom": "ManoMano",
        "emoji": "🔧",
        "description": "Spécialiste bricolage, jardinage et maison",
        "note": "Marketplace sélective : expertise sectorielle recommandée.",
        "ean_obligatoire": True,
    },
    "maisons_du_monde": {
        "nom": "Maisons du Monde",
        "emoji": "🛋️",
        "description": "Spécialiste mobilier & déco (Mirakl)",
        "note": "EAN obligatoire. DEA (Déchets d'Éléments d'Ameublement) requis pour le mobilier. Matériau mappé vers valeurs MdM.",
        "ean_obligatoire": True,
    },
    "leroy_merlin": {
        "nom": "Leroy Merlin",
        "emoji": "🏡",
        "description": "Bricolage & maison — 19M visiteurs/mois (Mirakl)",
        "note": "EAN obligatoire. Marketplace sélective : expertise bricolage/amélioration de l'habitat requise.",
        "ean_obligatoire": True,
    },
    "fnac": {
        "nom": "Fnac",
        "emoji": "📚",
        "description": "Culture, tech & high-tech",
        "note": "Portail Catalogue commun avec Darty depuis juillet 2025.",
        "ean_obligatoire": True,
    },
    "la_redoute": {
        "nom": "La Redoute",
        "emoji": "👗",
        "description": "Mode & maison, audience féminine qualifiée",
        "note": "Marketplace sélective — validation éditoriale des fiches.",
        "ean_obligatoire": False,
    },
    "zalando": {
        "nom": "Zalando",
        "emoji": "👟",
        "description": "Spécialiste mode & chaussures en Europe",
        "note": "La plus exigeante sur la qualité des données — validation avant mise en ligne.",
        "ean_obligatoire": True,
    },
    "back_market": {
        "nom": "Back Market",
        "emoji": "♻️",
        "description": "Spécialiste reconditionné & seconde main",
        "note": "Réservé aux produits reconditionnés certifiés.",
        "ean_obligatoire": True,
    },
    "decathlon": {
        "nom": "Decathlon",
        "emoji": "⚽",
        "description": "Sport & outdoor",
        "note": "Marketplace sélective — expertise sport recommandée.",
        "ean_obligatoire": True,
    },
}

# ---------------------------------------------------------------------
# Mapping catégorie → marketplaces suggérées (ordre = pertinence)
# Sources : Lengow 2026, ecommercemag.fr 2026
# ---------------------------------------------------------------------

CATEGORIES_VERS_MARKETPLACES = {
    "Cuisine & Maison": [
        "amazon", "cdiscount", "fnac_darty", "leroy_merlin",
    ],
    "Électroménager": [
        "amazon", "cdiscount", "fnac_darty",
    ],
    "High-Tech": [
        "amazon", "cdiscount", "fnac_darty", "back_market",
    ],
    "Sport & Plein air": [
        "amazon", "cdiscount", "decathlon",
    ],
    "Bagagerie & Voyage": [
        "amazon", "cdiscount", "fnac_darty", "la_redoute",
    ],
    "Animalerie": [
        "amazon", "cdiscount",
    ],
    "Maison & Luminaire": [
        "amazon", "cdiscount", "leroy_merlin", "maisons_du_monde",
    ],
    "Mobilier & Décoration": [
        "amazon", "maisons_du_monde", "leroy_merlin", "cdiscount",
    ],
    "Jardin & Extérieur": [
        "amazon", "cdiscount", "leroy_merlin",
    ],
    "Bricolage & Outillage": [
        "amazon", "cdiscount", "leroy_merlin",
    ],
    "Mode & Vêtements": [
        "amazon", "zalando", "la_redoute",
    ],
    "Bijoux & Montres": [
        "amazon", "fnac_darty", "la_redoute",
    ],
    "Beauté & Santé": [
        "amazon", "cdiscount", "fnac_darty",
    ],
    "Hygiène & Santé": [
        "amazon", "cdiscount",
    ],
    "Bébé & Puériculture": [
        "amazon", "cdiscount", "la_redoute",
    ],
    "Jouets & Jeux": [
        "amazon", "cdiscount", "fnac_darty",
    ],
    "Fournitures de bureau": [
        "amazon", "cdiscount",
    ],
    "Instruments de musique": [
        "amazon", "fnac",
    ],
    "Epicerie & Boissons": [
        "amazon", "cdiscount",
    ],
    "Auto & Moto": [
        "amazon", "cdiscount",
    ],
    "Autre": [
        "amazon", "cdiscount", "fnac_darty",
    ],
}


def get_marketplaces_suggereees(categorie: str) -> list[str]:
    """Retourne la liste des clés de marketplace suggérées pour une catégorie."""
    return CATEGORIES_VERS_MARKETPLACES.get(categorie, CATEGORIES_VERS_MARKETPLACES["Autre"])


def get_marketplace_info(cle: str) -> dict:
    """Retourne les métadonnées d'une marketplace par sa clé."""
    return MARKETPLACES.get(cle, {})
