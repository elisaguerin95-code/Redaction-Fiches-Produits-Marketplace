# Création Fiche Produit Marketplace

Outil d'aide à la création de fiches produits pour vendeurs marketplace :
à partir d'une **matrice Excel à 6 colonnes**, facile à remplir par les
équipes, génère une fiche Amazon optimisée (titre, Item Highlights,
bullet points, description marketing, mots-clés back-end), un score de
conformité, les attributs techniques propres à la catégorie Amazon
détectée, une **vérification de conformité de l'image produit**, et un
**export prêt à copier-coller dans le vrai template Amazon**.

Génération 100% déterministe : aucun appel à une IA générative externe,
aucune clé API requise.

## Architecture

- `rules.py` — moteur de conformité texte : vérifie une fiche par rapport
  aux règles Amazon (titre 75 car., bullets, description, mots-clés...).
- `generator.py` — génère la fiche + détecte catégorie/genre grammatical
  + devine les attributs techniques spécifiques à la catégorie.
- `image_check.py` — vérifie la conformité d'une image produit (format,
  poids, dimensions, ratio, fond blanc) à partir de son URL.
- `export_amazon.py` — construit une ligne au format flat-file Amazon
  (colonnes standards), à partir d'une fiche déjà générée.
- `app.py` — interface Streamlit (fiche unique + traitement par lot Excel).
- `data/genre_noms_fr.csv` — dictionnaire de 41 902 noms français avec
  leur genre grammatical (lexique LEFFF), utilisé pour écrire "un"/"une"
  correctement dans la description.
- `sample_data/produits_demo.xlsx` — 5 produits pour la démo du pitch.

## Format de la matrice (colonnes attendues)

`marque`, `type_produit`, `materiau`, `couleur`, `infos_produits`
(infos libres séparées par des virgules), `image_url` (URL d'une image
déjà hébergée en ligne). Un modèle Excel est téléchargeable directement
depuis l'application (onglet "Lot").

**Important sur "infos_produits" :** chaque information distincte doit
être séparée par une virgule. Une phrase complète sans virgules sera
traitée comme une seule information, qui risque d'être masquée si elle
répète déjà le matériau, la couleur ou le type de produit (voir
`dedupliquer_caracteristiques` dans `generator.py`).

**Important sur "image_url" :** l'image doit être déjà hébergée en ligne
avec une URL d'accès direct. Un lien de partage Google Drive classique
(```drive.google.com/file/d/.../view```) ne fonctionne pas tel quel : il
faut un lien qui renvoie directement le fichier image.

## Vérification de conformité image

`image_check.py` télécharge l'image et vérifie (sans IA, juste de
l'analyse d'image avec Pillow) : le format (JPEG/PNG/TIFF/GIF), le poids
(max 10 Mo), la résolution minimale (1000px, idéalement 2000px pour le
zoom), le ratio carré recommandé, et une estimation du fond blanc en
testant les bords de l'image. Cette dernière vérification est une
heuristique (test des coins de l'image), pas une garantie à 100%.

## Export façon Amazon

**Point important :** les vrais flat files Amazon sont des templates
propres à chaque catégorie, téléchargés depuis Seller Central — il
n'existe pas de format universel qu'on puisse reproduire à l'identique
sans cet accès. `export_amazon.py` construit donc un fichier avec les
noms de colonnes standards communs à la plupart des templates
(item_sku, item_name, brand_name, bullet_point1-5, product_description,
generic_keywords, color_name, material_type, main_image_url,
feed_product_type, + les attributs spécifiques à la catégorie détectée).
Ce n'est pas un import direct, mais un fichier pensé pour être
copié-collé dans le vrai template une fois téléchargé pour la bonne
catégorie — c'est ce qui transforme le gain de temps en gain réel,
au-delà du simple texte généré.

## Pourquoi la description gère "le/la" correctement (ou pas)

L'outil n'est pas une IA générative : il ne "comprend" pas le français,
il applique des règles écrites à l'avance. Pour deviner le genre
grammatical d'un produit, il s'appuie sur `data/genre_noms_fr.csv` — un
dictionnaire de 41 902 noms communs français, extrait du lexique
linguistique libre LEFFF (aucun appel réseau, juste une table de
correspondance chargée une fois au démarrage). Si le mot n'est pas
reconnu, la description bascule sur un style "accroche publicitaire"
qui évite tout risque de faute d'accord.

## Lancer en local

```bash
python -m venv venv
source venv/bin/activate          # ou venv\Scripts\activate sous Windows
pip install -r requirements.txt
streamlit run app.py
```

## Déployer sur Streamlit Cloud

1. Pousse ce dossier sur un repo GitHub
2. Sur https://share.streamlit.io, "New app" > sélectionne le repo et `app.py`
3. Déploie — pas de secrets à configurer, l'app n'a aucune dépendance externe

## Tester un module seul

```bash
python rules.py          # exemple de fiche notée par le moteur de conformité texte
python generator.py      # deux exemples (genre connu / inconnu)
python image_check.py    # vérification image sur 2 images de test générées localement
python export_amazon.py  # exemple de ligne d'export Amazon
```

## Pistes Vision V2 (pour le pitch)

- Étendre `MOTS_CLES_PRODUIT` et `ATTRIBUTS_BOOLEENS_PAR_CATEGORIE` à
  davantage de catégories et de produits
- Support multi-marketplace (Cdiscount, Fnac Darty...)
- Remplacer le dictionnaire de catégories par un vrai modèle de
  classification entraîné (V1 volontairement simple et explicable)
- Suggestions de mots-clés SEO par analyse concurrentielle
