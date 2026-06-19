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
import json
import hashlib
import unicodedata
from rules import STOPWORDS_FR_EN
from nlp_extractor import extraire_caracteristiques

# ---------------------------------------------------------------------
# Dictionnaire de genre grammatical (41 902 noms communs français)
# ---------------------------------------------------------------------

def _sans_accents(texte: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn"
    )


def _charger_dictionnaire_genre() -> dict:
    chemin = os.path.join(os.path.dirname(__file__), "data", "genre_noms_fr.csv")
    dictionnaire = {}
    with open(chemin, encoding="utf-8") as f:
        for ligne in f:
            mot, genre = ligne.rstrip("\n").split(",")
            dictionnaire[_sans_accents(mot)] = genre
    return dictionnaire


def _charger_categories_amazon() -> dict:
    """Charge le dictionnaire de 6 700+ mots-clés -> catégorie Amazon,
    extrait du fichier officiel Amazon Browse Tree Mappings (fr)."""
    chemin = os.path.join(os.path.dirname(__file__), "data", "categories_amazon_fr.json")
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


DICTIONNAIRE_GENRE = _charger_dictionnaire_genre()
CATEGORIES_AMAZON = _charger_categories_amazon()


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

# ---------------------------------------------------------------------
# Variété marketing : 2 variantes par catégorie (10 au total), pour que
# deux produits différents dans la même catégorie n'aient pas une
# description et des bullets génériques identiques. Toujours sans IA :
# ce sont des templates écrits à l'avance, choisis de façon déterministe
# (voir selectionner_variante_marketing) selon le produit.
#
# Tous les adjectifs utilisés sont épicènes (identiques au masculin et au
# féminin : pratique, fiable, simple, robuste, agréable, confortable,
# efficace) pour éviter tout risque de faute d'accord avec le genre du
# produit, comme pour la description de base.
# ---------------------------------------------------------------------

TEMPLATES_MARKETING = {
    "Cuisine & Maison": [
        {
            "structure": "question",
            "adjectif": "pratique et fiable",
            "benefice": "vos préparations du quotidien",
            "cloture": "Un allié fiable pour la cuisine de tous les jours.",
            "bullets_generiques": [
                "USAGE QUOTIDIEN - conçu pour accompagner vos préparations au jour le jour",
                "FACILE À NETTOYER - un entretien simple pour un usage répété",
                "GAIN DE PLACE - un format pensé pour s'intégrer dans toutes les cuisines",
                "RÉSISTANT À L'USAGE - pensé pour accompagner vos préparations sur la durée",
                "PRISE EN MAIN IMMÉDIATE - aucun réglage complexe nécessaire",
            ],
        },
        {
            "structure": "affirmation",
            "adjectif": "simple et durable",
            "benefice": "simplifier votre cuisine au quotidien",
            "cloture": "Pensé pour durer, au cœur de votre cuisine.",
            "bullets_generiques": [
                "ADAPTÉ AU QUOTIDIEN - conçu pour un usage répété en cuisine",
                "ENTRETIEN SIMPLE - se nettoie facilement après chaque usage",
                "FORMAT PRATIQUE - pensé pour se ranger facilement",
                "FABRICATION SOIGNÉE - des matériaux choisis pour la durabilité",
                "POLYVALENT - s'adapte à de nombreuses préparations",
            ],
        },
    ],
    "High-Tech": [
        {
            "structure": "question",
            "adjectif": "efficace et simple d'utilisation",
            "benefice": "votre usage quotidien de la technologie",
            "cloture": "Une technologie pensée pour s'intégrer facilement à votre quotidien.",
            "bullets_generiques": [
                "PRISE EN MAIN IMMÉDIATE - aucun réglage complexe nécessaire",
                "DESIGN COMPACT - pensé pour vous accompagner partout",
                "FABRICATION SOIGNÉE - des matériaux choisis pour la durabilité",
                "COMPATIBLE AU QUOTIDIEN - s'intègre facilement à vos habitudes",
                "USAGE PROLONGÉ - pensé pour accompagner un usage régulier",
            ],
        },
        {
            "structure": "affirmation",
            "adjectif": "compact et performant",
            "benefice": "vous accompagner dans vos usages connectés",
            "cloture": "Pensé pour suivre le rythme de vos usages connectés.",
            "bullets_generiques": [
                "INSTALLATION RAPIDE - opérationnel en quelques minutes",
                "FORMAT NOMADE - pensé pour vous suivre au quotidien",
                "MATÉRIAUX SÉLECTIONNÉS - choisis pour la résistance à l'usage",
                "COMPATIBILITÉ ÉTENDUE - s'intègre à vos appareils du quotidien",
                "SIMPLE D'UTILISATION - une prise en main intuitive",
            ],
        },
    ],
    "Bagagerie & Plein air": [
        {
            "structure": "question",
            "adjectif": "robuste et pratique",
            "benefice": "vos déplacements et vos sorties",
            "cloture": "Pensé pour suivre vos déplacements, où que vous alliez.",
            "bullets_generiques": [
                "RÉSISTANT AUX USAGES INTENSIFS - conçu pour suivre vos déplacements",
                "RANGEMENT OPTIMISÉ - plusieurs espaces pensés pour le quotidien",
                "CONFORT DE PORT - pensé pour un usage prolongé",
                "FORMAT ADAPTÉ AUX DÉPLACEMENTS - pratique au quotidien",
                "FABRICATION SOIGNÉE - des matériaux choisis pour la durabilité",
            ],
        },
        {
            "structure": "affirmation",
            "adjectif": "solide et confortable",
            "benefice": "accompagner vos sorties en plein air",
            "cloture": "Un compagnon fiable pour vos sorties, quelle que soit la météo.",
            "bullets_generiques": [
                "CONÇU POUR L'EXTÉRIEUR - pensé pour résister aux usages répétés",
                "PRATIQUE AU QUOTIDIEN - facile à transporter et à ranger",
                "CONFORT DURABLE - pensé pour un usage prolongé",
                "RANGEMENT ASTUCIEUX - plusieurs espaces pour s'organiser facilement",
                "FINITION SOIGNÉE - des matériaux choisis pour la résistance",
            ],
        },
    ],
    "Maison & Luminaire": [
        {
            "structure": "question",
            "adjectif": "simple et agréable à utiliser",
            "benefice": "apporter une ambiance soignée à votre intérieur",
            "cloture": "Pensé pour s'intégrer naturellement à votre intérieur.",
            "bullets_generiques": [
                "INSTALLATION SIMPLE - opérationnel en quelques minutes",
                "AMBIANCE SOIGNÉE - pensé pour s'intégrer à votre décoration",
                "USAGE QUOTIDIEN - conçu pour un usage prolongé",
                "FABRICATION SOIGNÉE - des matériaux choisis pour la durabilité",
                "FACILE À ENTRETENIR - un nettoyage simple au quotidien",
            ],
        },
        {
            "structure": "affirmation",
            "adjectif": "discret et fonctionnel",
            "benefice": "illuminer votre intérieur avec simplicité",
            "cloture": "Une touche de confort, pensée pour durer.",
            "bullets_generiques": [
                "DESIGN DISCRET - s'intègre facilement à toute décoration",
                "PRISE EN MAIN IMMÉDIATE - aucun réglage complexe nécessaire",
                "USAGE PROLONGÉ - pensé pour accompagner le quotidien",
                "FINITION SOIGNÉE - des matériaux choisis pour la durabilité",
                "ENTRETIEN SIMPLE - se nettoie facilement",
            ],
        },
    ],
    "Animalerie": [
        {
            "structure": "question",
            "adjectif": "pratique et confortable",
            "benefice": "le bien-être quotidien de votre compagnon",
            "cloture": "Pensé pour le confort et le bien-être de votre compagnon.",
            "bullets_generiques": [
                "CONFORT AU QUOTIDIEN - pensé pour le bien-être de votre compagnon",
                "FACILE À ENTRETENIR - un nettoyage simple pour un usage répété",
                "ADAPTÉ À UN USAGE RÉGULIER - conçu pour accompagner le quotidien",
                "MATÉRIAUX SÉLECTIONNÉS - choisis pour la sécurité de votre animal",
                "PRISE EN MAIN IMMÉDIATE - aucun réglage complexe nécessaire",
            ],
        },
        {
            "structure": "affirmation",
            "adjectif": "simple et sécurisant",
            "benefice": "simplifier le quotidien de votre animal",
            "cloture": "Un geste simple pour prendre soin de votre animal au quotidien.",
            "bullets_generiques": [
                "PENSÉ POUR LE QUOTIDIEN - accompagne votre compagnon au jour le jour",
                "ENTRETIEN FACILE - se nettoie rapidement après usage",
                "FORMAT ADAPTÉ - pensé pour un usage régulier",
                "FABRICATION SOIGNÉE - des matériaux choisis avec attention",
                "USAGE SÉCURISÉ - pensé pour le confort de votre animal",
            ],
        },
    ],
}


def selectionner_variante_marketing(categorie: str, marque: str, type_produit: str) -> dict | None:
    """
    Choisit une des 2 variantes marketing de la catégorie de façon
    déterministe (même produit -> toujours la même variante, mais 2
    produits différents de la même catégorie ont de bonnes chances de
    tomber sur des variantes différentes). Retourne None si la catégorie
    n'a pas de variantes dédiées (ex: "Autre") -> on garde alors le style
    neutre par défaut.

    On utilise un hash stable (md5) plutôt que hash() de Python, qui
    n'est volontairement pas reproductible d'une exécution à l'autre.
    """
    variantes = TEMPLATES_MARKETING.get(categorie)
    if not variantes:
        return None
    cle = f"{marque}-{type_produit}".lower()
    empreinte = int(hashlib.md5(cle.encode("utf-8")).hexdigest(), 16)
    return variantes[empreinte % len(variantes)]


def nettoyer_caracteristiques(texte_brut: str) -> list[str]:
    """
    Découpe le champ 'infos_produits' en caractéristiques individuelles.

    - Si le texte contient des virgules : découpage simple (comportement
      classique, le plus fiable).
    - Si le texte est une phrase libre sans virgules (6 mots ou plus) :
      on active le pipeline NLP (nltk + LEFFF) pour extraire les
      caractéristiques automatiquement, sans forcer l'utilisateur à
      reformater son texte.
    """
    if not texte_brut:
        return []

    if "," in texte_brut:
        morceaux = texte_brut.split(",")
        return [m.strip() for m in morceaux if m.strip()]

    if len(texte_brut.split()) >= 6:
        return extraire_caracteristiques(texte_brut)

    return [texte_brut.strip()] if texte_brut.strip() else []


def dedupliquer_caracteristiques(caracteristiques: list[str], materiau: str,
                                  couleur: str, type_produit: str) -> list[str]:
    """
    Retire les éléments qui répètent déjà le matériau, la couleur ou le
    type de produit (ex: si couleur="Transparent" et qu'une info dit déjà
    "table transparente...", cette info est redondante et masquée).

    Cas typique : l'utilisateur a tapé une phrase complète au lieu
    d'informations séparées par des virgules -> la phrase entière
    contient souvent déjà la couleur/le type de produit.
    """
    mots_a_eviter = [v.lower() for v in [materiau, couleur, type_produit] if v]

    resultat = []
    for c in caracteristiques:
        c_lower = c.lower()
        # redondant si l'info contient déjà matériau/couleur/type de produit,
        # OU si l'info est elle-même contenue dedans (ex: type_produit="bouilloire
        # électrique" et info="bouilloire" -> redondant dans les deux cas)
        est_redondant = any(mot in c_lower or c_lower in mot for mot in mots_a_eviter)
        if est_redondant:
            continue
        resultat.append(c)
    return resultat


def detecter_categorie_et_genre(type_produit: str, infos_produits: str) -> tuple[str, str | None]:
    """
    Détecte la catégorie Amazon (via 6 700+ mots-clés extraits du Browse
    Tree Mappings officiel Amazon FR) et le genre grammatical (via LEFFF).
    """
    # Recherche dans le type_produit mot par mot (sans accents pour tolérance)
    type_produit_na = _sans_accents(type_produit.lower())
    categorie = "Autre"

    # On teste d'abord les mots du type_produit, puis les infos_produits
    for texte in [type_produit_na, _sans_accents(infos_produits.lower())]:
        for mot in texte.split():
            mot_propre = mot.strip(",.;:!?()")
            if mot_propre in CATEGORIES_AMAZON:
                categorie = CATEGORIES_AMAZON[mot_propre]
                break
        if categorie != "Autre":
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
                     bullets_generiques: list[str] = None,
                     nombre_attendu: int = 5, longueur_max: int = 200) -> list[str]:
    """Construit les 5 bullets avec un label précis pour matériau/couleur, déduit pour le reste."""
    bullets_generiques = bullets_generiques or BULLETS_GENERIQUES
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
        bullets.append(bullets_generiques[i % len(bullets_generiques)])
        i += 1

    return bullets[:nombre_attendu]


def generer_backend_keywords(materiau: str, couleur: str, caracteristiques: list[str],
                              titre: str, longueur_max_octets: int = 249) -> str:
    """
    Extrait des mots-clés de recherche, en minuscules, en évitant si
    possible les doublons avec le titre (bonne pratique Amazon).

    Si exclure les mots déjà dans le titre ne laisse plus aucun mot-clé
    (cas des produits avec peu d'infos, où le titre absorbe tout), on les
    garde malgré le doublon plutôt que de renvoyer un champ vide : un
    mot-clé back-end identique au titre reste plus utile qu'un champ vide.
    """
    mots_titre = {w.lower().strip(",.;:!?") for w in titre.split()}

    mots_sans_doublon = []
    mots_toutes_sources = []
    for source in [materiau, couleur] + caracteristiques:
        for mot in source.lower().split():
            mot_propre = mot.strip(",.;:!?")
            if not mot_propre or mot_propre in STOPWORDS_FR_EN:
                continue
            if mot_propre not in mots_toutes_sources:
                mots_toutes_sources.append(mot_propre)
            if mot_propre not in mots_titre and mot_propre not in mots_sans_doublon:
                mots_sans_doublon.append(mot_propre)

    # on préfère exclure les doublons avec le titre, mais seulement si ça
    # laisse au moins un mot-clé -> sinon on retombe sur toutes les sources
    mots_retenus = mots_sans_doublon if mots_sans_doublon else mots_toutes_sources

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
                                   genre: str | None, variante: dict | None = None,
                                   longueur_max: int = 2000) -> str:
    """
    Description inspirée du framework Amazon "Problème -> Solution ->
    Spécificités -> Conclusion". Ne recopie pas les bullets mot pour mot.

    Si une variante marketing est fournie (catégorie reconnue), on
    l'utilise pour varier la structure et le vocabulaire d'un produit à
    l'autre. Sinon (catégorie "Autre"), on retombe sur le style neutre
    par défaut, identique à avant.

    Si on connait le genre du produit (dictionnaire LEFFF), on écrit une
    vraie phrase avec "un"/"une". Sinon, on utilise un style "accroche
    publicitaire" qui évite le problème d'accord (le programme ne
    comprend pas le français, il suit des règles écrites à l'avance).
    """
    type_produit_aff = type_produit.strip()

    if variante is None:
        if genre == "feminin":
            accroche = f"Vous cherchez une {type_produit_aff} fiable et pratique au quotidien ? {marque} a pensé à tout."
        elif genre == "masculin":
            accroche = f"Vous cherchez un {type_produit_aff} fiable et pratique au quotidien ? {marque} a pensé à tout."
        else:
            accroche = f"{marque} : {type_produit_aff.capitalize()} — fiable et pratique au quotidien."
        cloture = f"Un choix de confiance pour les amateurs de {type_produit_aff}."
    else:
        participe = "pensée" if genre == "feminin" else "pensé"
        adjectif = variante["adjectif"]
        benefice = variante["benefice"]

        if variante["structure"] == "question":
            if genre == "feminin":
                accroche = f"Vous cherchez une {type_produit_aff} {adjectif} ? {marque} l'a {participe} pour {benefice}."
            elif genre == "masculin":
                accroche = f"Vous cherchez un {type_produit_aff} {adjectif} ? {marque} l'a {participe} pour {benefice}."
            else:
                accroche = f"{marque} : {type_produit_aff.capitalize()} — {adjectif}, {participe} pour {benefice}."
        else:  # structure "affirmation"
            if genre == "feminin":
                accroche = f"{marque} présente une {type_produit_aff} {adjectif}, {participe} pour {benefice}."
            elif genre == "masculin":
                accroche = f"{marque} présente un {type_produit_aff} {adjectif}, {participe} pour {benefice}."
            else:
                accroche = f"{marque} présente : {type_produit_aff.capitalize()} — {adjectif}, {participe} pour {benefice}."
        cloture = variante["cloture"]

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

    phrases.append(cloture)

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
    caracteristiques = dedupliquer_caracteristiques(caracteristiques, materiau, couleur, type_produit)

    categorie, genre = detecter_categorie_et_genre(type_produit, infos_produits)
    variante = selectionner_variante_marketing(categorie, marque, type_produit)
    titre = generer_titre(marque, type_produit, materiau, couleur, caracteristiques)

    return {
        "title": titre,
        "item_highlights": generer_item_highlights(materiau, couleur, caracteristiques),
        "bullets": generer_bullets(
            materiau, couleur, caracteristiques,
            bullets_generiques=variante["bullets_generiques"] if variante else None,
        ),
        "description": generer_description_marketing(
            marque, type_produit, materiau, couleur, caracteristiques, genre, variante
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
