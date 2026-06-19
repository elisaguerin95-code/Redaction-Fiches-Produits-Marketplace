"""
rules.py
---------
Moteur de conformité Amazon : vérifie une fiche produit générée par l'IA
par rapport aux règles réelles du Seller Central (vérifiées juin 2026).

Aucun appel API ici : tout est déterministe et testable seul, sans clé LLM.
C'est volontaire -> c'est la brique la plus fiable du produit, celle qui
"ne plante jamais" même si l'API du LLM tombe pendant le pitch.

Règles encodées :
- Titre : nouvelle limite stricte de 75 caractères (entrée en vigueur le
  27/07/2026), tout en gardant en mémoire l'ancienne limite de 200 car.
  pour info. On scorise sur la nouvelle règle car c'est plus exigeant
  et ça montre qu'on anticipe le changement réglementaire.
- Item Highlights : nouveau champ, 125 caractères max.
- Bullet points : exactement 5, ~200 caractères chacun pour un vendeur
  standard (non Brand Registry).
- Description : 2000 caractères max.
- Mots-clés back-end : 249 octets max, minuscules, sans ponctuation,
  sans doublon avec le titre.
- Caractères interdits, mots promotionnels interdits, répétition de mots.
"""

from __future__ import annotations
from dataclasses import dataclass, field


# ---------------------------------------------------------------------
# Constantes réglementaires (sources : Seller Central + presse spécialisée,
# vérifiées juin 2026)
# ---------------------------------------------------------------------

TITLE_MAX_NEW = 75          # nouvelle règle, obligatoire au 27/07/2026
TITLE_MAX_LEGACY = 200      # règle encore valable jusqu'au 27/07/2026
HIGHLIGHT_MAX = 125
BULLET_MAX = 200
NUM_BULLETS_EXPECTED = 5
DESCRIPTION_MAX = 2000
BACKEND_KEYWORDS_MAX_BYTES = 249

FORBIDDEN_SPECIAL_CHARS = ["!", "$", "?", "_", "{", "}", "^", "¬", "¦"]

# Mots/expressions promotionnels interdits (liste non exhaustive mais
# représentative des motifs de suppression de fiche les plus fréquents)
FORBIDDEN_PROMO_WORDS = [
    "best seller", "bestseller", "best", "cheapest", "n°1", "numero 1",
    "free shipping", "livraison gratuite", "100% guaranteed",
    "100% garanti", "guaranteed", "garanti à vie", "top quality",
    "premium quality", "qualité premium", "pas cher", "promo",
    "meilleur", "incroyable",
]

STOPWORDS_FR_EN = {
    "le", "la", "les", "de", "des", "du", "un", "une", "et", "ou",
    "the", "a", "an", "and", "or", "of", "for", "with", "in", "on",
}


@dataclass
class CheckResult:
    """Résultat d'une vérification unitaire."""
    label: str
    passed: bool
    detail: str
    points_earned: float
    points_max: float


@dataclass
class ComplianceReport:
    """Rapport global de conformité d'une fiche produit."""
    score: float  # /100
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def grade(self) -> str:
        if self.score >= 85:
            return "Excellent"
        if self.score >= 65:
            return "Correct, à améliorer"
        return "Non conforme"


def _count_word_repetitions(text: str) -> dict[str, int]:
    """Compte les répétitions de mots significatifs (hors stopwords)."""
    words = [w.lower().strip(",.;:!?") for w in text.split()]
    counts: dict[str, int] = {}
    for w in words:
        if not w or w in STOPWORDS_FR_EN:
            continue
        counts[w] = counts.get(w, 0) + 1
    return {w: c for w, c in counts.items() if c > 2}


def _contains_forbidden_promo(text: str) -> list[str]:
    lower = text.lower()
    return [w for w in FORBIDDEN_PROMO_WORDS if w in lower]


def _contains_forbidden_chars(text: str) -> list[str]:
    return [c for c in FORBIDDEN_SPECIAL_CHARS if c in text]


def check_title(title: str) -> list[CheckResult]:
    results = []

    # Longueur vs nouvelle règle stricte (75 car.)
    length = len(title)
    if length <= TITLE_MAX_NEW:
        results.append(CheckResult(
            "Titre - longueur (règle 2026: 75 car.)", True,
            f"{length}/{TITLE_MAX_NEW} caractères — conforme à la nouvelle règle.",
            20, 20,
        ))
    elif length <= TITLE_MAX_LEGACY:
        results.append(CheckResult(
            "Titre - longueur (règle 2026: 75 car.)", False,
            f"{length} caractères : conforme à l'ancienne limite (200) mais "
            f"dépasse la nouvelle limite de {TITLE_MAX_NEW} car. en vigueur "
            f"au 27/07/2026.",
            10, 20,
        ))
    else:
        results.append(CheckResult(
            "Titre - longueur (règle 2026: 75 car.)", False,
            f"{length} caractères : dépasse même l'ancienne limite de "
            f"{TITLE_MAX_LEGACY} car. Risque de suppression de la fiche.",
            0, 20,
        ))

    # Caractères interdits
    bad_chars = _contains_forbidden_chars(title)
    if bad_chars:
        results.append(CheckResult(
            "Titre - caractères interdits", False,
            f"Caractère(s) interdit(s) détecté(s) : {', '.join(bad_chars)}",
            0, 5,
        ))
    else:
        results.append(CheckResult(
            "Titre - caractères interdits", True, "Aucun caractère interdit.", 5, 5,
        ))

    # Répétition de mots (max 2 occurrences)
    repeats = _count_word_repetitions(title)
    if repeats:
        details = ", ".join(f"'{w}' x{c}" for w, c in repeats.items())
        results.append(CheckResult(
            "Titre - répétition de mots", False,
            f"Mot(s) répété(s) plus de 2 fois : {details}", 0, 5,
        ))
    else:
        results.append(CheckResult(
            "Titre - répétition de mots", True, "Pas de répétition excessive.", 5, 5,
        ))

    # Mots promotionnels interdits
    promo = _contains_forbidden_promo(title)
    if promo:
        results.append(CheckResult(
            "Titre - mots promotionnels", False,
            f"Formulation(s) interdite(s) : {', '.join(promo)}", 0, 5,
        ))
    else:
        results.append(CheckResult(
            "Titre - mots promotionnels", True, "Aucune formulation promotionnelle.", 5, 5,
        ))

    return results


def check_item_highlights(highlights: list[str]) -> list[CheckResult]:
    results = []
    if not highlights:
        return [CheckResult(
            "Item Highlights - présence", False,
            "Aucun Item Highlight fourni (nouveau champ 2026, recommandé).",
            0, 10,
        )]

    too_long = [h for h in highlights if len(h) > HIGHLIGHT_MAX]
    if too_long:
        results.append(CheckResult(
            "Item Highlights - longueur", False,
            f"{len(too_long)} highlight(s) dépassent {HIGHLIGHT_MAX} caractères.",
            5, 10,
        ))
    else:
        results.append(CheckResult(
            "Item Highlights - longueur", True,
            f"{len(highlights)} highlight(s), tous sous {HIGHLIGHT_MAX} caractères.",
            10, 10,
        ))
    return results


def check_bullets(bullets: list[str]) -> list[CheckResult]:
    results = []

    if len(bullets) != NUM_BULLETS_EXPECTED:
        results.append(CheckResult(
            "Bullets - nombre", False,
            f"{len(bullets)} bullet(s) fourni(s), {NUM_BULLETS_EXPECTED} attendus.",
            5, 10,
        ))
    else:
        results.append(CheckResult(
            "Bullets - nombre", True, f"{NUM_BULLETS_EXPECTED} bullets fournis.", 10, 10,
        ))

    too_long = [b for b in bullets if len(b) > BULLET_MAX]
    if too_long:
        results.append(CheckResult(
            "Bullets - longueur", False,
            f"{len(too_long)} bullet(s) dépassent {BULLET_MAX} caractères.",
            5, 10,
        ))
    else:
        results.append(CheckResult(
            "Bullets - longueur", True, f"Tous les bullets sous {BULLET_MAX} caractères.", 10, 10,
        ))

    promo_hits = [b for b in bullets if _contains_forbidden_promo(b)]
    if promo_hits:
        results.append(CheckResult(
            "Bullets - mots promotionnels", False,
            f"{len(promo_hits)} bullet(s) contiennent une formulation interdite.",
            0, 5,
        ))
    else:
        results.append(CheckResult(
            "Bullets - mots promotionnels", True, "Aucune formulation promotionnelle.", 5, 5,
        ))

    return results


def check_description(description: str) -> list[CheckResult]:
    length = len(description)
    if length == 0:
        return [CheckResult(
            "Description - présence", False, "Description manquante.", 0, 15,
        )]
    if length <= DESCRIPTION_MAX:
        return [CheckResult(
            "Description - longueur", True,
            f"{length}/{DESCRIPTION_MAX} caractères.", 15, 15,
        )]
    return [CheckResult(
        "Description - longueur", False,
        f"{length} caractères : dépasse la limite de {DESCRIPTION_MAX}.",
        7, 15,
    )]


def check_backend_keywords(keywords: str, title: str) -> list[CheckResult]:
    results = []

    if not keywords or not keywords.strip():
        return [CheckResult(
            "Mots-clés back-end",
            False,
            "Champ vide : aucun mot-clé ne sera indexé par Amazon. "
            "Renseigne matériau, couleur ou infos produits pour générer des mots-clés.",
            0, 20,
        )]

    byte_length = len(keywords.encode("utf-8"))

    if byte_length <= BACKEND_KEYWORDS_MAX_BYTES:
        results.append(CheckResult(
            "Mots-clés back-end - taille", True,
            f"{byte_length}/{BACKEND_KEYWORDS_MAX_BYTES} octets.", 10, 10,
        ))
    else:
        results.append(CheckResult(
            "Mots-clés back-end - taille", False,
            f"{byte_length} octets : dépasse {BACKEND_KEYWORDS_MAX_BYTES} octets "
            f"— aucun mot-clé ne sera indexé par Amazon.", 0, 10,
        ))

    if keywords != keywords.lower():
        results.append(CheckResult(
            "Mots-clés back-end - casse", False,
            "Les mots-clés contiennent des majuscules (sans bénéfice, gaspille des octets).",
            5, 10,
        ))
    else:
        results.append(CheckResult(
            "Mots-clés back-end - casse", True, "Tout en minuscules.", 10, 10,
        ))

    title_words = {w.lower().strip(",.;:!?") for w in title.split()}
    keyword_words = {w.lower().strip(",.;:!?") for w in keywords.split()}
    duplicates = title_words & keyword_words - STOPWORDS_FR_EN
    if duplicates:
        results.append(CheckResult(
            "Mots-clés back-end - doublons avec le titre", False,
            f"Mot(s) déjà présents dans le titre (octets gaspillés) : "
            f"{', '.join(sorted(duplicates))}", 5, 10,
        ))
    else:
        results.append(CheckResult(
            "Mots-clés back-end - doublons avec le titre", True,
            "Pas de doublon avec le titre.", 10, 10,
        ))

    return results


def evaluate_listing(listing: dict) -> ComplianceReport:
    """
    Évalue une fiche produit complète et retourne un score /100 + détail.

    `listing` doit contenir les clés :
    title (str), item_highlights (list[str]), bullets (list[str]),
    description (str), backend_keywords (str)
    """
    all_checks: list[CheckResult] = []
    all_checks += check_title(listing.get("title", ""))
    all_checks += check_item_highlights(listing.get("item_highlights", []))
    all_checks += check_bullets(listing.get("bullets", []))
    all_checks += check_description(listing.get("description", ""))
    all_checks += check_backend_keywords(
        listing.get("backend_keywords", ""), listing.get("title", "")
    )

    total_earned = sum(c.points_earned for c in all_checks)
    total_max = sum(c.points_max for c in all_checks)
    score = round((total_earned / total_max) * 100, 1) if total_max else 0.0

    return ComplianceReport(score=score, checks=all_checks)


if __name__ == "__main__":
    # Petit test manuel, sans API : permet de vérifier le moteur seul.
    demo_listing = {
        "title": "Gourde Isotherme Inox 750ml - Best Seller!!! Garde le froid 24h",
        "item_highlights": ["Matériau inox 18/8", "Sans BPA", "Anse de transport"],
        "bullets": [
            "ISOLATION DOUBLE PAROI - garde vos boissons fraîches jusqu'à 24h",
            "DESIGN ROBUSTE - inox 18/8, résistant aux chocs du quotidien",
            "BOUCHON ÉTANCHE - anti-fuite, parfait pour le sac de sport",
            "FACILE À NETTOYER - large ouverture compatible lave-vaisselle",
            "FORMAT NOMADE - 750ml, idéal randonnée, bureau, sport",
        ],
        "description": "Gourde isotherme en acier inoxydable, double paroi, "
                        "750ml. Idéale pour le sport, le bureau ou la randonnée.",
        "backend_keywords": "gourde sport randonnee bureau isotherme inox",
    }

    report = evaluate_listing(demo_listing)
    print(f"Score global : {report.score}/100 ({report.grade})\n")
    for c in report.checks:
        status = "OK " if c.passed else "FAIL"
        print(f"[{status}] {c.label} ({c.points_earned}/{c.points_max}) — {c.detail}")
