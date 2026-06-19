"""
image_check.py
----------------
Vérifie qu'une image produit (donnée par URL déjà hébergée) respecte les
exigences Amazon pour l'image principale (vérifiées en 2026) : format,
poids, dimensions, ratio, fond blanc.

Aucune IA ici non plus : on télécharge l'image et on mesure ses
propriétés avec Pillow (bibliothèque de traitement d'image classique).

Règles encodées (sources : documentation et guides vendeurs Amazon 2026) :
- Format accepté : JPEG, PNG, TIFF, GIF (non animé)
- Poids maximum : 10 Mo
- Dimension minimale : 1000 px sur le plus petit côté (zoom désactivé sinon)
- Dimension recommandée : 2000 px (qualité de zoom optimale)
- Format carré recommandé (1:1), maximum 5:1
- Fond blanc pur (RGB 255,255,255) pour l'image principale -> on
  approxime ça en testant les coins de l'image (pas une garantie à 100%,
  mais un bon indicateur sans avoir besoin de vision par ordinateur).
"""

import io
import requests
from PIL import Image

FORMATS_ACCEPTES = {"JPEG", "PNG", "TIFF", "GIF"}
POIDS_MAX_OCTETS = 10 * 1024 * 1024  # 10 Mo
DIMENSION_MIN = 1000
DIMENSION_RECOMMANDEE = 2000
TOLERANCE_BLANC = 12  # écart toléré par canal de couleur par rapport à 255


HEADERS_REQUETE = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


def _telecharger_image(url: str) -> tuple[bytes, str]:
    """Télécharge le contenu de l'image. Retourne (contenu, erreur)."""
    try:
        reponse = requests.get(url, timeout=10, headers=HEADERS_REQUETE)
        reponse.raise_for_status()
    except Exception as e:
        return None, f"Impossible de récupérer l'image ({e})"

    type_contenu = reponse.headers.get("content-type", "")
    if not type_contenu.startswith("image/"):
        return None, (
            f"Cette URL ne renvoie pas une image directe (type reçu : '{type_contenu}'). "
            "C'est probablement l'adresse d'une page produit et non celle du fichier image : "
            "fais un clic droit sur la photo elle-même puis 'Copier l'adresse de l'image'."
        )

    return reponse.content, None


def _fond_est_blanc(image: Image.Image) -> bool:
    """
    Échantillonne plusieurs points sur les bords de l'image et vérifie
    qu'ils sont proches du blanc pur. Heuristique simple, pas une
    détection parfaite (un produit blanc qui touche le bord pourrait
    fausser le résultat), mais un bon indicateur pour une démo.
    """
    image_rgb = image.convert("RGB")
    largeur, hauteur = image_rgb.size
    points_a_tester = [
        (0, 0), (largeur - 1, 0), (0, hauteur - 1), (largeur - 1, hauteur - 1),
        (largeur // 2, 0), (0, hauteur // 2), (largeur - 1, hauteur // 2), (largeur // 2, hauteur - 1),
    ]
    for x, y in points_a_tester:
        r, g, b = image_rgb.getpixel((x, y))[:3]
        if abs(r - 255) > TOLERANCE_BLANC or abs(g - 255) > TOLERANCE_BLANC or abs(b - 255) > TOLERANCE_BLANC:
            return False
    return True


def _verifier_proprietes_de_base(image: Image.Image, contenu: bytes) -> list[dict]:
    """Vérifications communes à toutes les images (principale ou secondaire)."""
    largeur, hauteur = image.size
    poids = len(contenu)
    format_image = image.format

    checks = []

    format_ok = format_image in FORMATS_ACCEPTES
    checks.append({
        "label": "Format de fichier",
        "passed": format_ok,
        "detail": f"{format_image} ({'accepté' if format_ok else 'non accepté, JPEG/PNG/TIFF/GIF attendu'})",
    })

    poids_ok = poids <= POIDS_MAX_OCTETS
    checks.append({
        "label": "Poids du fichier",
        "passed": poids_ok,
        "detail": f"{poids / 1_000_000:.1f} Mo (max 10 Mo)",
    })

    dimension_min_actuelle = min(largeur, hauteur)
    dimension_ok = dimension_min_actuelle >= DIMENSION_MIN
    checks.append({
        "label": "Résolution minimale",
        "passed": dimension_ok,
        "detail": f"{largeur}x{hauteur}px (minimum {DIMENSION_MIN}px, "
                  f"recommandé {DIMENSION_RECOMMANDEE}px pour activer le zoom)",
    })

    return checks


def analyser_image(contenu: bytes, image_principale: bool = True) -> dict:
    """
    Analyse le contenu binaire d'une image déjà téléchargée et retourne
    un rapport de conformité. Séparée de _telecharger_image pour pouvoir
    être testée sans connexion réseau (utile pour les tests unitaires).

    image_principale=True applique en plus les règles strictes (fond
    blanc, format carré) qui ne s'appliquent qu'à l'image principale.
    Amazon est beaucoup plus souple sur les images secondaires (pas de
    fond blanc requis) -> on ne vérifie alors que format/poids/résolution.
    """
    try:
        image = Image.open(io.BytesIO(contenu))
        image.load()
    except Exception as e:
        return {
            "url_valide": False, "erreur": f"Fichier image illisible : {e}",
            "format": None, "dimensions": None, "poids_octets": len(contenu),
            "checks": [], "score": 0.0,
        }

    largeur, hauteur = image.size
    checks = _verifier_proprietes_de_base(image, contenu)

    if image_principale:
        ratio = max(largeur, hauteur) / min(largeur, hauteur)
        ratio_ok = ratio <= 1.1
        checks.append({
            "label": "Format carré (recommandé)",
            "passed": ratio_ok,
            "detail": f"ratio {ratio:.2f}:1 ({'proche du carré' if ratio_ok else 'non carré, risque de recadrage automatique'})",
        })

        fond_blanc_ok = _fond_est_blanc(image)
        checks.append({
            "label": "Fond blanc (estimation, image principale uniquement)",
            "passed": fond_blanc_ok,
            "detail": "Bords de l'image proches du blanc pur" if fond_blanc_ok else
                      "Bords non blancs détectés -> vérifier le fond manuellement (estimation, pas garanti à 100%)",
        })

    points_max = len(checks)
    points_ok = sum(1 for c in checks if c["passed"])
    score = round(points_ok / points_max * 100, 1)

    return {
        "url_valide": True, "erreur": None, "format": image.format,
        "dimensions": (largeur, hauteur), "poids_octets": len(contenu),
        "checks": checks, "score": score,
    }


def verifier_image(url: str, image_principale: bool = True) -> dict:
    """
    Télécharge puis analyse l'image d'une URL. Fonction principale du
    module. image_principale=False applique les règles plus souples des
    images secondaires (pas de fond blanc requis).
    """
    if not url:
        return {
            "url_valide": False, "erreur": "Aucune URL fournie",
            "format": None, "dimensions": None, "poids_octets": None,
            "checks": [], "score": 0.0,
        }

    contenu, erreur = _telecharger_image(url)
    if contenu is None:
        return {
            "url_valide": False, "erreur": erreur, "format": None,
            "dimensions": None, "poids_octets": None, "checks": [], "score": 0.0,
        }

    return analyser_image(contenu, image_principale=image_principale)


if __name__ == "__main__":
    # Test sans réseau : on génère 2 images de test directement avec
    # Pillow (une conforme, une non conforme) pour vérifier la logique
    # d'analyse indépendamment de la connexion internet.
    print("=== Image 1 : carrée, blanche, 1200x1200 (devrait bien passer) ===")
    img_ok = Image.new("RGB", (1200, 1200), (255, 255, 255))
    buffer_ok = io.BytesIO()
    img_ok.save(buffer_ok, format="JPEG")
    rapport_ok = analyser_image(buffer_ok.getvalue())
    print(f"Score : {rapport_ok['score']}/100")
    for c in rapport_ok["checks"]:
        print(f"  [{'OK' if c['passed'] else 'FAIL'}] {c['label']} : {c['detail']}")

    print("\n=== Image 2 : rectangle gris, 400x800 (devrait échouer) ===")
    img_bad = Image.new("RGB", (400, 800), (180, 180, 180))
    buffer_bad = io.BytesIO()
    img_bad.save(buffer_bad, format="JPEG")
    rapport_bad = analyser_image(buffer_bad.getvalue())
    print(f"Score : {rapport_bad['score']}/100")
    for c in rapport_bad["checks"]:
        print(f"  [{'OK' if c['passed'] else 'FAIL'}] {c['label']} : {c['detail']}")

    print("\n=== Image 3 : même rectangle gris, mais en image SECONDAIRE (pas de fond blanc requis) ===")
    rapport_secondaire = analyser_image(buffer_bad.getvalue(), image_principale=False)
    print(f"Score : {rapport_secondaire['score']}/100")
    for c in rapport_secondaire["checks"]:
        print(f"  [{'OK' if c['passed'] else 'FAIL'}] {c['label']} : {c['detail']}")
