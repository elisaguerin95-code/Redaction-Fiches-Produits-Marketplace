"""
generator.py
-------------
Génère une fiche produit Amazon à partir d'une matrice à 5 colonnes
remplie par les équipes : marque, type_produit, materiau, couleur,
infos_produits (texte libre, séparé par des virgules).

Aucun appel à une IA externe : tout est fait avec des règles de texte
(templates, mots-clés, regex) -> gratuit, instantané, ne plante jamais.

Ce module fait 3 choses :
1. Génère la fiche Amazon classique (titre, bullets, description, mots-clés)
2. Détecte la catégorie ET le genre grammatical du produit (pour écrire
   "le" ou "la" correctement -> voir detecter_categorie_et_genre)
3. Devine les attributs techniques spécifiques à la catégorie Amazon
   détectée (ex: Autonomie pour le High-Tech, Capacité pour la Cuisine)
"""

import re
import os
import unicodedata
from rules import STOPWORDS_FR_EN  # on réutilise la liste de stopwords déjà définie

# ---------------------------------------------------------------------
# Dictionnaire de genre grammatical (39 784 noms communs français,
# extrait du lexique LEFFF - une ressource linguistique libre). Permet
# de savoir si "gourde" est féminin ou "sac" est masculin SANS appeler
# une IA : c'est juste une grande table de correspondance, chargée une
# fois au démarrage de l'app.
# ---------------------------------------------------------------------

def _sans_accents(texte: str) -> str:
    """Retire les accents pour une recherche plus tolérante (écouteur -> ecouteur)."""
    return "".join(
        c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn"
    )


def _charger_dictionnaire_genre() -> dict:
    """Charge data/genre_noms_fr.csv une seule fois (mot -> 'm' ou 'f')."""
    chemin = os.path.join(os.path.dirname(__file__), "data", "genre_noms_fr.csv")
    dictionnaire = {}
    with open(chemin, encoding="utf-8") as f:
        for ligne in f:
            mot, genre = ligne.rstrip("\n").split(",")
            dictionnaire[_sans_accents(mot)] = genre
    return dictionnaire


DICTIONNAIRE_GENRE = _charger_dictionnaire_genre()


def deviner_genre(type_produit: str) -> str | None:
    """
    Devine si le premier mot de type_produit est masculin ou féminin, en
    s'appuyant sur le dictionnaire LEFFF. En français, le nom principal
    d'un groupe nominal est presque toujours le premier mot
    ("gourde isotherme", "sac à dos", "lampe de bureau").

    Tolère l'absence d'accents et le pluriel simple (mot qui se termine
    par "s"). Retourne None si le mot n'est pas trouvé (genre inconnu).
    """
    if not type_produit:
        return None

    premier_mot = _sans_accents(type_produit.strip().split()[0].lower())

    if premier_mot in DICTIONNAIRE_GENRE:
        genre = DICTIONNAIRE_GENRE[premier_mot]
    elif premier_mot.endswith("s") and premier_mot[:-1] in DICTIONNAIRE_GENRE:
        genre = DICTIONNAIRE_GENRE[premier_mot[:-1]]  # pluriel simple -> singulier
    else:
        return None

    return "masculin" if genre == "m" else "feminin"

# ---------------------------------------------------------------------
# Données de connaissance produit (le "petit dictionnaire" qui remplace
# la compréhension du langage qu'aurait une vraie IA)
# ---------------------------------------------------------------------

# Mots-clés DE TYPE DE PRODUIT -> catégorie Amazon. Le genre n'est plus
# codé ici : il est désormais déduit automatiquement par deviner_genre()
# à partir du dictionnaire LEFFF (39 784 mots), beaucoup plus complet.
MOTS_CLES_PRODUIT = {
    "gourde": "Cuisine & Maison",
    "bouteille": "Cuisine & Maison",
    "gamelle": "Animalerie",
    "ecouteur": "High-Tech",
    "casque": "High-Tech",
    "sac a dos": "Bagagerie & Plein air",
    "lampe": "Maison & Luminaire",
}

# Mots-clés DE CARACTÉRISTIQUE (pas le nom du produit lui-même) -> on
# connait la catégorie mais pas le genre (on ne sait pas de quel mot il
# s'agit grammaticalement), donc pas utilisé pour les accords.
MOTS_CLES_CATEGORIE_GENERIQUE = {
    "bluetooth": "High-Tech",
    "led": "Maison & Luminaire",
    "randonnee": "Bagagerie & Plein air",
    "impermeable": "Bagagerie & Plein air",
    "chien": "Animalerie",
    "chat": "Animalerie",
}

# Pour chaque catégorie : quels attributs Amazon on cherche à remplir
# (en plus de Matériau/Couleur qui sont communs à toutes les catégories).
# Chaque tuple = (mot-clé à chercher dans "infos_produits", label affiché)
ATTRIBUTS_BOOLEENS_PAR_CATEGORIE = {
    "Cuisine & Maison": [("lave-vaisselle", "Compatible lave-vaisselle"), ("bpa", "Sans BPA")],
    "High-Tech": [("bluetooth", "Connectivité Bluetooth"), ("etanche", "Étanche")],
    "Bagagerie & Plein air": [("impermeable", "Imperméable"), ("compartiment", "Plusieurs compartiments")],
    "Maison & Luminaire": [("variateur", "Variateur de luminosité"), ("usb", "Port USB intégré")],
    "Animalerie": [("antiderapant", "Base antidérapante"), ("nettoyer", "Facile à nettoyer")],
}

# Unités numériques qu'on sait reconnaître dans "infos_produits" (ex: "750ml",
# "30h", "15w") pour remplir automatiquement un attribut numérique pertinent.
UNITES_NUMERIQUES = [
    (r"\d+\s*ml\b", "Capacité (ml)"),
    (r"\d+\s*litres?\b", "Capacité (L)"),
    (r"\d+\s*h\b", "Autonomie (h)"),
    (r"\d+\s*w\b", "Puissance (W)"),
    (r"\d+\s*kg\b", "Poids (kg)"),
]

BULLETS_GENERIQUES = [
    "QUALITÉ GARANTIE - conçu pour un usage quotidien fiable et durable",
    "FACILE À UTILISER - pensé pour une prise en main immédiate",
    "DESIGN SOIGNÉ - une finition pensée pour s'intégrer partout",
    "SATISFACTION CLIENT - pensé pour répondre aux attentes du quotidien",
    "PRODUIT POLYVALENT - s'adapte à de nombreux usages",
]


def nettoyer_caracteristiques(texte_brut: str) -> list[str]:
    """Découpe le champ 'infos_produits' (texte libre séparé par virgules)."""
    if not texte_brut:
        return []
    morceaux = texte_brut.split(",")
    return [m.strip() for m in morceaux if m.strip()]


def detecter_categorie_et_genre(type_produit: str, infos_produits: str) -> tuple[str, str | None]:
    """
    Devine la catégorie Amazon (via mots-clés) ET le genre grammatical
    du produit (via le dictionnaire LEFFF, beaucoup plus complet qu'une
    liste codée à la main).
    """
    type_produit_lower = type_produit.lower()

    categorie = "Autre"
    for mot_cle, cat in MOTS_CLES_PRODUIT.items():
        if mot_cle in type_produit_lower:
            categorie = cat
            break
    else:
        texte_complet = (type_produit + " " + infos_produits).lower()
        for mot_cle, cat in MOTS_CLES_CATEGORIE_GENERIQUE.items():
            if mot_cle in texte_complet:
                categorie = cat
                break

    genre = deviner_genre(type_produit)
    return categorie, genre


def extraire_valeur_numerique(infos_produits: str) -> tuple[str, str] | tuple[None, None]:
    """Cherche un premier nombre+unité connu (ex: '750ml', '30h') dans le texte."""
    texte_lower = infos_produits.lower()
    for motif, label in UNITES_NUMERIQUES:
        match = re.search(motif, texte_lower)
        if match:
            return label, match.group()
    return None, None


def generer_attributs_specifiques(categorie: str, materiau: str, couleur: str,
                                   infos_produits: str) -> dict:
    """
    Construit le tableau des attributs techniques attendus par Amazon pour
    la catégorie détectée (en plus des champs de fiche classiques).
    """
    attributs = {
        "Matériau": materiau or "Non précisé",
        "Couleur": couleur or "Non précisé",
    }

    label_numerique, valeur_numerique = extraire_valeur_numerique(infos_produits)
    if label_numerique:
        attributs[label_numerique] = valeur_numerique

    for mot_cle, label in ATTRIBUTS_BOOLEENS_PAR_CATEGORIE.get(categorie, []):
        attributs[label] = "Oui" if mot_cle in infos_produits.lower() else "Non précisé"

    return attributs


def generer_titre(marque: str, type_produit: str, materiau: str, couleur: str,
                   caracteristiques: list[str], longueur_max: int = 75) -> str:
    """Construit le titre (75 caractères max), en ajoutant matériau/couleur/infos tant qu'il reste de la place."""
    base = f"{marque} {type_produit}".strip()
    place_restante = longueur_max - len(base) - 3

    candidats = [c for c in [materiau, couleur] + caracteristiques if c]
    ajoutes = []
    for c in candidats:
        essai = ", ".join(ajoutes + [c])
        if len(essai) <= place_restante:
            ajoutes.append(c)
        else:
            break

    titre = f"{base} - {', '.join(ajoutes)}" if ajoutes else base
    return titre[:longueur_max].rstrip(" -,")


def generer_item_highlights(materiau: str, couleur: str, caracteristiques: list[str],
                             longueur_max: int = 125, nombre_max: int = 3) -> list[str]:
    """Sélectionne jusqu'à 3 informations courtes pour le champ Item Highlights."""
    candidats = [c for c in [materiau, couleur] + caracteristiques if c]
    highlights = [c.capitalize() for c in candidats if len(c) <= longueur_max]
    return highlights[:nombre_max]


def generer_bullets(materiau: str, couleur: str, caracteristiques: list[str],
                     nombre_attendu: int = 5, longueur_max: int = 200) -> list[str]:
    """Construit les 5 bullets avec un label précis pour matériau/couleur, déduit pour le reste."""
    bullets = []

    if materiau:
        bullets.append(f"MATÉRIAU - Fabriqué en {materiau}, gage de qualité et de durabilité"[:longueur_max])
    if couleur:
        bullets.append(f"COULEUR - Disponible en {couleur}, pour s'adapter à tous les styles"[:longueur_max])

    for c in caracteristiques:
        mots_significatifs = [m for m in c.split() if m.lower() not in STOPWORDS_FR_EN]
        # il faut au moins 3 mots significatifs pour que le label (2 premiers
        # mots) ne soit pas une pure duplication du contenu entier
        if len(mots_significatifs) >= 3:
            label = " ".join(mots_significatifs[:2]).upper()
        else:
            label = "POINT FORT"
        bullets.append(f"{label} - {c.capitalize()}"[:longueur_max])

    i = 0
    while len(bullets) < nombre_attendu:
        bullets.append(BULLETS_GENERIQUES[i % len(BULLETS_GENERIQUES)])
        i += 1

    return bullets[:nombre_attendu]


def generer_backend_keywords(materiau: str, couleur: str, caracteristiques: list[str],
                              titre: str, longueur_max_octets: int = 249) -> str:
    """Extrait des mots-clés de recherche, en minuscules, sans doublon avec le titre."""
    mots_titre = {w.lower().strip(",.;:!?") for w in titre.split()}

    mots_retenus = []
    for source in [materiau, couleur] + caracteristiques:
        for mot in source.lower().split():
            mot_propre = mot.strip(",.;:!?")
            if (mot_propre and mot_propre not in STOPWORDS_FR_EN
                    and mot_propre not in mots_titre and mot_propre not in mots_retenus):
                mots_retenus.append(mot_propre)

    resultat = ""
    for mot in mots_retenus:
        essai = (resultat + " " + mot).strip()
        if len(essai.encode("utf-8")) <= longueur_max_octets:
            resultat = essai
        else:
            break
    return resultat


def generer_description_marketing(marque: str, type_produit: str, materiau: str,
                                   couleur: str, caracteristiques: list[str],
                                   genre: str | None, longueur_max: int = 2000) -> str:
    """
    Description inspirée du framework Amazon "Problème -> Solution ->
    Spécificités -> Conclusion". Ne recopie pas les bullets mot pour mot.

    Si on connait le genre du produit (via MOTS_CLES_PRODUIT), on écrit une
    vraie phrase avec "un"/"une". Sinon, on utilise un style "accroche
    publicitaire" qui évite le problème d'accord (voir explication donnée
    à l'utilisatrice : le programme ne comprend pas le français, il suit
    juste des règles écrites à l'avance).
    """
    type_produit_aff = type_produit.strip()

    if genre == "feminin":
        accroche = f"Vous cherchez une {type_produit_aff} fiable et pratique au quotidien ? {marque} a pensé à tout."
    elif genre == "masculin":
        accroche = f"Vous cherchez un {type_produit_aff} fiable et pratique au quotidien ? {marque} a pensé à tout."
    else:
        accroche = f"{marque} : {type_produit_aff.capitalize()} — fiable et pratique au quotidien."

    phrases = [accroche]

    details = []
    if materiau:
        details.append(f"fabriqué en {materiau}")
    if couleur:
        details.append(f"disponible en {couleur}")
    if details:
        phrases.append(" et ".join(details).capitalize() + ".")

    if caracteristiques:
        phrases.append("Points forts : " + ", ".join(caracteristiques) + ".")

    phrases.append(f"Un choix de confiance pour les amateurs de {type_produit_aff}.")

    return " ".join(phrases)[:longueur_max]


def generer_fiche(raw_input: dict) -> dict:
    """
    Fonction principale : prend la ligne de matrice (1 produit) et
    retourne une fiche complète, prête à être notée par rules.py, plus
    les attributs techniques spécifiques à la catégorie détectée.
    """
    marque = raw_input.get("marque", "").strip() or "Marque"
    type_produit = raw_input.get("type_produit", "").strip() or "Produit"
    materiau = raw_input.get("materiau", "").strip()
    couleur = raw_input.get("couleur", "").strip()
    infos_produits = raw_input.get("infos_produits", "").strip()
    caracteristiques = nettoyer_caracteristiques(infos_produits)

    categorie, genre = detecter_categorie_et_genre(type_produit, infos_produits)
    titre = generer_titre(marque, type_produit, materiau, couleur, caracteristiques)

    return {
        "title": titre,
        "item_highlights": generer_item_highlights(materiau, couleur, caracteristiques),
        "bullets": generer_bullets(materiau, couleur, caracteristiques),
        "description": generer_description_marketing(
            marque, type_produit, materiau, couleur, caracteristiques, genre
        ),
        "backend_keywords": generer_backend_keywords(materiau, couleur, caracteristiques, titre),
        "category_suggestion": categorie,
        "attributs_specifiques": generer_attributs_specifiques(
            categorie, materiau, couleur, infos_produits
        ),
    }


if __name__ == "__main__":
    # Test rapide sans Streamlit : un produit avec genre connu (gourde,
    # féminin) et un produit avec genre inconnu pour vérifier le fallback.
    exemples = [
        {
            "marque": "Hydra+", "type_produit": "gourde isotherme",
            "materiau": "inox", "couleur": "bleu nuit",
            "infos_produits": "750ml, garde le froid 24h, sans BPA, anse de transport",
        },
        {
            "marque": "SoundWave", "type_produit": "ecouteurs",
            "materiau": "plastique recycle", "couleur": "noir mat",
            "infos_produits": "bluetooth 5.3, autonomie 30h, etanche ipx5",
        },
    ]
    for exemple in exemples:
        print("=" * 70)
        fiche = generer_fiche(exemple)
        for cle, valeur in fiche.items():
            print(f"\n{cle.upper()} :")
            print(valeur)
