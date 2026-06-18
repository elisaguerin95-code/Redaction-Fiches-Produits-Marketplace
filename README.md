# Marketplace Listing Copilot

Copilote pour vendeurs marketplace : à partir d'une **matrice Excel à
5 colonnes**, facile à remplir par les équipes, génère une fiche Amazon
optimisée (titre, Item Highlights, bullet points, description marketing,
mots-clés back-end), un score de conformité, **et** les attributs
techniques propres à la catégorie Amazon détectée (ex : Autonomie et
Connectivité pour le High-Tech, Capacité et Compatible lave-vaisselle
pour la Cuisine).

Génération 100% déterministe : aucun appel à une IA externe, aucune clé
API requise.

## Architecture

- `rules.py` — moteur de conformité : vérifie une fiche par rapport aux
  règles Amazon (titre 75 car., bullets, description, mots-clés...) et
  calcule un score /100.
- `generator.py` — génère la fiche + détecte catégorie/genre grammatical
  + devine les attributs techniques spécifiques à la catégorie.
- `app.py` — interface Streamlit (fiche unique + traitement par lot Excel).
- `sample_data/produits_demo.xlsx` — 5 produits pour la démo du pitch
  (un par catégorie détectée : Cuisine & Maison, High-Tech, Bagagerie &
  Plein air, Maison & Luminaire, Animalerie).

## Format de la matrice (colonnes attendues)

`marque`, `type_produit`, `materiau`, `couleur`, `infos_produits`
(infos libres séparées par des virgules dans la cellule, ex :
"750ml, garde le froid 24h, sans BPA, anse de transport"). Un modèle
Excel est téléchargeable directement depuis l'application (onglet "Lot").

## Pourquoi la description gère "le/la" correctement (ou pas)

Le générateur n'est pas une IA : il ne "comprend" pas le français, il
applique des règles écrites à l'avance. Pour deviner le genre
grammatical d'un produit, il s'appuie sur `data/genre_noms_fr.csv` —
un dictionnaire de **41 902 noms communs français avec leur genre**,
extrait du lexique linguistique libre LEFFF (aucune IA, aucun appel
réseau, juste une table de correspondance chargée une fois au
démarrage). Le premier mot de `type_produit` est recherché dans ce
dictionnaire (tolérant aux accents manquants et au pluriel simple).

Si le mot n'est pas reconnu, la description bascule sur un style
"accroche publicitaire" qui évite tout risque de faute d'accord.
Limite connue : si `type_produit` est mis au pluriel ET que le terme
exact n'existe qu'au singulier dans le dictionnaire pour une raison
quelconque, l'article peut rester singulier ("un écouteurs") — mineur,
mais à savoir pour la démo.

## Lancer en local

```bash
python -m venv venv
source venv/bin/activate          # ou venv\Scripts\activate sous Windows
pip install -r requirements.txt
streamlit run app.py
```

## Déployer sur Streamlit Cloud

Même pipeline que pour WildFlix :

1. Pousse ce dossier sur un repo GitHub
2. Sur https://share.streamlit.io, "New app" > sélectionne le repo et `app.py`
3. Déploie — pas de secrets à configurer, l'app n'a aucune dépendance externe

## Tester un module seul

```bash
python rules.py        # exemple de fiche notée par le moteur de conformité
python generator.py    # deux exemples (genre connu / inconnu)
```

## Pistes Vision V2 (pour le pitch)

- Étendre `MOTS_CLES_PRODUIT` et `ATTRIBUTS_BOOLEENS_PAR_CATEGORIE` à
  davantage de catégories et de produits
- Support multi-marketplace (Cdiscount, Fnac Darty...)
- Remplacer le dictionnaire de catégories par un vrai modèle de
  classification entraîné (V1 volontairement simple et explicable)
- Suggestions de mots-clés SEO par analyse concurrentielle
