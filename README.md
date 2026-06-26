# 🏷️ Création Fiche Produit Marketplace

Outil d'aide à la création de fiches produits pour vendeurs marketplace, développé lors d'un datathon de 48h (Mission Data — Wild Code School / Simplon).

**Une saisie, plusieurs exports.** À partir d'une matrice Excel simple, génère en quelques secondes des fiches optimisées et conformes pour Amazon, Cdiscount et Fnac Darty — avec score de conformité instantané et un fichier d'export par marketplace.

> 🔗 **Application en ligne** : [lien du site](https://redaction-fiches-pdt-marketplace.streamlit.app/)

---

## 📋 Description

La valeur ajoutée n'est pas sur un seul produit — c'est à l'**échelle** et sur **plusieurs marketplaces** que l'outil prend tout son sens. Un vendeur remplit sa matrice une fois, et l'outil génère automatiquement les exports dans le bon format pour chaque canal de distribution ciblé.

**Génération 100% déterministe** — aucun appel à une IA générative externe, aucune clé API requise. Le moteur applique des règles de texte, un pipeline NLP (nltk + lexique LEFFF), et des données officielles Amazon (Browse Tree Mappings FR) pour produire des résultats reproductibles et explicables.

---

## 📁 Structure du projet

| Fichier | Description |
|---------|-------------|
| `app.py` | Interface Streamlit (fiche unique + lot Excel + historique) |
| `generator.py` | Génération de la fiche (titre, bullets, description, mots-clés) |
| `rules.py` | Moteur de conformité Amazon (score /100) |
| `nlp_extractor.py` | Pipeline NLP pour parser le texte libre sans virgules |
| `image_check.py` | Vérification de conformité image (format, résolution, fond blanc) |
| `marketplace_registry.py` | Mapping catégories → marketplaces suggérées |
| `export_amazon.py` | Export au format flat-file Amazon |
| `export_cdiscount.py` | Export au format Cdiscount Marketplace (Octopia) |
| `export_fnac_darty.py` | Export au format Fnac Darty Portail Catalogue |
| `data/genre_noms_fr.csv` | Lexique LEFFF — 41 902 noms français avec genre grammatical |
| `data/categories_amazon_fr.json` | 6 700+ mots-clés → catégorie Amazon (Browse Tree Mappings FR) |
| `sample_data/produits_demo.xlsx` | 5 produits de démonstration (un par catégorie) |
| `requirements.txt` | Dépendances Python |

---

## ⚙️ Comment ça marche ?

### 1. Saisie des données

Deux modes d'entrée :
- **Fiche unique** : formulaire Streamlit (Marque\* et Type de produit\* obligatoires, reste optionnel dans une zone dépliable)
- **Lot Excel** : matrice à 6 colonnes (`marque`, `type_produit`, `materiau`, `couleur`, `infos_produits`, `image_url`, `images_secondaires`)

Le champ `infos_produits` accepte **deux formats** :
- Virgules : `750ml, garde le froid 24h, sans BPA, anse de transport`
- Texte libre : `gourde isotherme 750ml garde le froid 24h sans BPA` → le pipeline NLP extrait automatiquement les caractéristiques

### 2. Pipeline de génération

```
infos brutes
    │
    ├─ NLP (nltk + LEFFF)          → extraction si texte libre
    ├─ detecter_categorie_et_genre → catégorie Amazon + genre grammatical
    ├─ generer_titre               → 75 car. max (règle 2026)
    ├─ generer_bullets             → 5 bullets (variantes par catégorie)
    ├─ generer_description         → framework Amazon Problème→Solution→Conclusion
    ├─ generer_backend_keywords    → 249 octets max, sans doublon titre
    └─ generer_attributs_specifiques → attributs techniques par catégorie
```

### 3. Moteur de conformité

`rules.py` vérifie chaque fiche contre les règles Amazon et retourne un score /100 avec le détail de chaque vérification (titre, highlights, bullets, description, mots-clés back-end, caractères interdits, mots promotionnels interdits).

### 4. NLP maison (sans modèle externe)

`nlp_extractor.py` combine :
- **nltk** — tokenisation française
- **Lexique LEFFF** (déjà chargé pour les genres) — identification des noms communs
- **Regex** — patterns techniques (dimensions, capacités, certifications, origines)

Pas de spaCy, pas de modèle à télécharger : le pipeline est léger et fonctionne sur l'offre gratuite Streamlit Cloud.

---

## 🚀 Installation et lancement

### En local

```bash
git clone <url-du-repo>
cd marketplace_copilot
python -m venv venv
source venv/bin/activate   # Windows : venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

### Déployer sur Streamlit Cloud

1. Pousser le repo sur GitHub
2. Sur [share.streamlit.io](https://share.streamlit.io) : **New app** → sélectionner le repo → fichier `app.py`
3. Déployer — pas de secrets à configurer, aucune clé API nécessaire

---

## 📊 Catégories couvertes

Détection automatique depuis le fichier officiel Amazon Browse Tree Mappings FR (24 univers, 16 386 chemins de catégorie) :

| Catégorie | Exemples de produits |
|-----------|---------------------|
| Cuisine & Maison | Bouilloire, gourde, ustensile |
| Électroménager | Aspirateur, four, climatiseur |
| High-Tech | Écouteurs, casque, câble |
| Sport & Plein air | Sac de randonnée, gourde sport |
| Bagagerie & Voyage | Valise, sac à dos de ville |
| Animalerie | Gamelle, jouet, laisse |
| Maison & Luminaire | Lampe, ampoule, plafonnier |
| Beauté & Santé | Shampoing, crème, brosse |
| Mode & Vêtements | T-shirt, robe, veste |
| … | 15 autres univers |

> ⚠️ **Limite connue** : le mobilier (tables, chaises, canapés) n'est pas dans le fichier Amazon fourni → ces produits tombent dans la catégorie "Autre".

---

## ⚠️ Limites connues (V1)

| Limite | Explication |
|--------|-------------|
| Genre grammatical | Le programme ne comprend pas le français : il consulte un dictionnaire (LEFFF). Si le mot n'y est pas, il bascule sur un style accroche sans accord. |
| NLP texte libre | Le pipeline (nltk + LEFFF) extrait les noms communs reconnus. Les adjectifs seuls ou les termes très techniques peuvent être manqués. |
| Historique | Stocké en mémoire (session Streamlit) — perdu à la fermeture de l'onglet. |
| Images | La vérification du fond blanc est une heuristique (test des coins) — pas une garantie à 100%. |
| Export Amazon | Colonnes standards communes à la plupart des catégories. Le vrai flat file (propre à chaque catégorie) se télécharge sur Seller Central. |

---

## 🔭 Vision V2

- Étendre les templates marketing à toutes les catégories couvertes
- Support multi-marketplace (Cdiscount, Fnac Darty, Zalando...)
- Remplacer la détection de catégorie par un modèle de classification entraîné
- Suggestions de mots-clés SEO par analyse concurrentielle
- Historique persistant (base de données légère)

---

## 👩‍💻 Auteur

Projet réalisé par **Elisa Guérin** dans le cadre du datathon Mission Data — Wild Code School / Simplon (juin 2026).
