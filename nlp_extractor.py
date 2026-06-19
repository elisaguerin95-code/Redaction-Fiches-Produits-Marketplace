"""
nlp_extractor.py
-----------------
Extraction de caractéristiques produit depuis un texte libre (sans
virgules), en combinant deux ressources déjà présentes dans le projet :

1. nltk  — tokenisation française (découpage en mots et en phrases)
2. LEFFF — lexique de 41 902 noms communs français (data/genre_noms_fr.csv)
           qu'on réutilise ici pour identifier si un token est un nom
           (et donc potentiellement une caractéristique produit)

Ce pipeline NLP "maison" remplace le besoin d'un modèle de langue externe
(type spaCy fr_core_news_sm) qui pèserait ~50 Mo et alourdirait le
déploiement Streamlit Cloud.

Pipeline en 4 étapes :
  1. Extraction des patterns techniques connus (regex : dimensions,
     capacités, certifications, origines géographiques...)
  2. Tokenisation avec nltk word_tokenize
  3. Regroupement des tokens en "chunks" autour des noms identifiés
     grâce au dictionnaire LEFFF
  4. Déduplication et nettoyage final

Résultat : une liste de caractéristiques dans le même format que si
l'utilisateur avait séparé ses infos par des virgules — ce qui permet
de réutiliser le reste du pipeline generator.py sans aucun changement.
"""

import re
import os
import unicodedata

import nltk

# ---------------------------------------------------------------------
# Chargement du lexique LEFFF (noms communs français + genre)
# Réutilisé depuis generator.py — pas de double chargement en mémoire
# si Streamlit garde le module en cache.
# ---------------------------------------------------------------------

def _sans_accents(texte: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texte)
        if unicodedata.category(c) != "Mn"
    )


def _charger_noms_lefff() -> set:
    """Charge l'ensemble des noms communs du LEFFF (genre ignoré ici,
    on veut juste savoir si un mot est un nom ou pas)."""
    chemin = os.path.join(os.path.dirname(__file__), "data", "genre_noms_fr.csv")
    noms = set()
    with open(chemin, encoding="utf-8") as f:
        for ligne in f:
            mot = ligne.split(",")[0]
            noms.add(_sans_accents(mot.lower()))
    return noms


NOMS_LEFFF = _charger_noms_lefff()

# Mots à ne jamais traiter comme une caractéristique produit (trop généraux
# ou trop grammaticaux même s'ils sont dans le LEFFF)
MOTS_EXCLUS = {
    "produit", "article", "chose", "objet", "modele", "version",
    "serie", "type", "genre", "style", "format", "taille", "couleur",
    "couleurs", "matiere", "matieres", "caractere", "caracteres",
}

# Conjonctions et prépositions sur lesquelles on découpe les groupes de mots
SEPARATEURS_LOGIQUES = {"et", "ou", "mais", "avec", "sans", "pour", "dont",
                         "ainsi", "notamment", "egalement", "aussi"}

# ---------------------------------------------------------------------
# Patterns techniques (regex) : reconnus avant la tokenisation nltk
# pour ne pas les fragmenter en mots individuels
# ---------------------------------------------------------------------

PATTERNS_TECHNIQUES = [
    # Dimensions : 150x80cm, 40 x 30 cm, 1.5m x 0.8m
    (r"\d+[\.,]?\d*\s*[xX×]\s*\d+[\.,]?\d*\s*(?:cm|mm|m|pouces?)?", "dimension"),
    # Capacités : 750ml, 1.5L, 40 litres
    (r"\d+[\.,]?\d*\s*(?:ml|cl|dl|litres?|l\b)", "capacite"),
    # Autonomie / durée : 30h, 12 heures
    (r"\d+[\.,]?\d*\s*(?:heures?|h\b)", "autonomie"),
    # Puissance : 1200W, 2000 watts
    (r"\d+[\.,]?\d*\s*(?:watts?|w\b)", "puissance"),
    # Poids : 500g, 2.5 kg
    (r"\d+[\.,]?\d*\s*(?:grammes?|g\b|kilos?|kg\b)", "poids"),
    # Certifications : IPX4, IP67, CE
    (r"\bip[x]?\d+\b", "certification"),
    (r"\bce\b", "certification"),
    # Normes / labels
    (r"\bmade\s+in\s+france\b", "origine"),
    (r"\bfabriqué\s+en\s+france\b", "origine"),
    (r"\bfabrication\s+française\b", "origine"),
    (r"\bsans\s+bpa\b", "securite"),
    (r"\binox\b", "materiau"),
    (r"\bbluetooth\s+\d[\.,]\d\b", "connectivite"),
]


def extraire_patterns_techniques(texte: str) -> tuple[list[str], str]:
    """
    Identifie et extrait les patterns techniques connus (dimensions,
    capacités, certifications...) avant la tokenisation nltk, pour ne
    pas les découper en morceaux.

    Retourne (liste des patterns extraits, texte restant sans ces patterns).
    """
    extraits = []
    texte_restant = texte.lower()

    for motif, _ in PATTERNS_TECHNIQUES:
        matches = re.findall(motif, texte_restant, re.IGNORECASE)
        for match in matches:
            extrait = match.strip()
            if extrait and extrait not in extraits:
                extraits.append(extrait)
        # on retire le pattern du texte pour ne pas le re-traiter
        texte_restant = re.sub(motif, " ", texte_restant, flags=re.IGNORECASE)

    return extraits, texte_restant


def _est_nom(token: str) -> bool:
    """Vérifie si un token est un nom commun français (via LEFFF)."""
    token_na = _sans_accents(token.lower())
    if token_na in MOTS_EXCLUS:
        return False
    if token_na in NOMS_LEFFF:
        return True
    # pluriel simple en -s (bouilloires -> bouilloire)
    if token_na.endswith("s") and token_na[:-1] in NOMS_LEFFF:
        return True
    return False


def _tokeniser(texte: str) -> list[str]:
    """Tokenise un texte avec nltk word_tokenize (gère la ponctuation française)."""
    try:
        return nltk.word_tokenize(texte, language="french")
    except LookupError:
        nltk.download("punkt_tab", quiet=True)
        return nltk.word_tokenize(texte, language="french")


def extraire_chunks_nominaux(texte: str) -> list[str]:
    """
    Extrait des groupes de mots nominaux depuis un texte libre en français.

    Stratégie : on tokenise, on repère les noms (LEFFF), et on regroupe
    les tokens consécutifs qui gravitent autour d'un nom (adjectifs et
    mots techniques qui précèdent ou suivent immédiatement). On découpe
    sur les séparateurs logiques (et, ou, mais, avec...).
    """
    tokens = _tokeniser(texte)
    if not tokens:
        return []

    # Découpage en groupes sur les séparateurs logiques et la ponctuation
    groupes = []
    groupe_courant = []
    for token in tokens:
        if _sans_accents(token.lower()) in SEPARATEURS_LOGIQUES or token in ".,;:!?":
            if groupe_courant:
                groupes.append(groupe_courant)
            groupe_courant = []
        else:
            groupe_courant.append(token)
    if groupe_courant:
        groupes.append(groupe_courant)

    # Pour chaque groupe, on ne le retient que s'il contient au moins un nom
    chunks = []
    for groupe in groupes:
        texte_groupe = " ".join(groupe).strip()
        mots_significatifs = [t for t in groupe if len(t) >= 3 and t.isalpha()]
        contient_nom = any(_est_nom(m) for m in mots_significatifs)
        if contient_nom and len(texte_groupe) >= 3:
            chunks.append(texte_groupe)

    return chunks


def extraire_caracteristiques(texte: str) -> list[str]:
    """
    Fonction principale du module.

    À partir d'un texte libre (sans virgules), retourne une liste de
    caractéristiques produit — dans le même format que si l'utilisateur
    avait séparé ses infos par des virgules.

    Combine patterns techniques (regex) + NLP (nltk + LEFFF).
    """
    if not texte or not texte.strip():
        return []

    # Étape 1 : patterns techniques connus (regex)
    patterns, texte_restant = extraire_patterns_techniques(texte)

    # Étape 2 : chunks nominaux sur le texte restant (nltk + LEFFF)
    chunks = extraire_chunks_nominaux(texte_restant)

    # Étape 3 : fusion, déduplication, nettoyage
    toutes = patterns + chunks
    vus = set()
    resultat = []
    for c in toutes:
        c_propre = c.strip(" .,;:-")
        c_na = _sans_accents(c_propre.lower())
        if c_propre and c_na not in vus and len(c_propre) >= 3:
            vus.add(c_na)
            resultat.append(c_propre)

    return resultat


if __name__ == "__main__":
    # Tests sur des cas réalistes de saisie libre (sans virgules)
    exemples = [
        "table basse transparente 150 x 80 cm made in France facilement nettoyable",
        "bouilloire électrique 1.7 litres en inox brossé avec arrêt automatique et indicateur de niveau",
        "sac à dos 40 litres imperméable avec compartiment ordinateur et bretelles rembourrées",
        "750ml garde le froid 24h sans BPA anse de transport",
    ]
    for ex in exemples:
        print(f"\nTexte : {ex}")
        print(f"Résultat : {extraire_caracteristiques(ex)}")
