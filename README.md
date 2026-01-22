# Tolkien Knowledge Graph

Projet Semantic Web - Construction d'un Knowledge Graph à partir du wiki **Tolkien Gateway**.

---

## Description du Projet

Ce projet construit un **Knowledge Graph (KG)** à partir des données du wiki [Tolkien Gateway](https://tolkiengateway.net/), en suivant l'approche de DBpedia et YAGO. Le KG capture les entités et leurs relations, avec des alignements vers des sources externes.

---

## Structure des Fichiers

```
code/
  main.py             - lance la construction du KG
  interface.py        - lance le serveur web
  fuseki_client.py    - gère la connexion Fuseki
  tolkien_kg/
    api/              - client MediaWiki
    parsers/          - extraction infoboxes
    rdf/              - génération triplets RDF
    external/         - données MECCG + CSV
    alignments/       - liens DBpedia/Wikidata
    multilingual/     - labels multilingues
    links/            - liens internes wiki
    shacl/            - validation SHACL

données sources:      cards.json, lotr_characters.csv
fichiers générés:     tolkien_kg.ttl, tolkien_kg_complete.ttl, meccg_cards.ttl
ontologie:            tolkien_vocabulary.ttl, tolkien_shapes.ttl
cache:                alignment_cache.json, fandom_lang_cache.json
```

---

## Installation

### 1. Prérequis

- **Python 3.8+**
- **Apache Jena Fuseki**

### 2. Installer les dépendances Python

```bash
pip install -r requirements.txt
```


### 3. Installer et lancer Fuseki

```bash
# Démarrer Fuseki (depuis le dossier Fuseki)
./fuseki-server --update --mem /tolkien

```

Fuseki sera accessible sur `http://localhost:3030`

---

## Lancer le Pipeline Principal

Le script `main.py` exécute toutes les étapes de construction du KG :

```bash
cd code
python main.py
```

### Modifier la limite d'entités par type d'infobox

Par défaut, le pipeline traite **300 entités par type d'infobox**. Pour augmenter ou réduire ce nombre, modifiez la variable `LIMIT` dans `main.py` (ligne 30) :

```python
# Ligne 30 dans main.py
LIMIT = 300  # Changer cette valeur (ex: 500, 1000, ou None pour tout récupérer)
```

### Étapes du Pipeline

1. **Test connexion API** - Vérifie l'accès à Tolkien Gateway
2. **Récupération entités** - Liste les pages par type d'infobox
3. **Parsing & génération RDF** - Extraction des infoboxes → triplets RDF
4. **Intégration CSV** - Enrichissement avec `lotr_characters.csv`
5. **Intégration MECCG** - Liaison avec les cartes `cards.json`
6. **Labels multilingues** - Ajout via Fandom wiki (FR, DE, ES, IT, etc.)
7. **Alignements externes** - Liens `owl:sameAs` vers DBpedia/Wikidata
8. **Liens internes** - Relations entre pages du wiki
9. **Vocabulaire** - Génération de l'ontologie RDFS/OWL
10. **Shapes SHACL** - Création des contraintes de validation
11. **Validation** - Vérification du KG avec pyshacl
12. **Export & chargement Fuseki** - Sauvegarde `.ttl` et upload

---

## Lancer l'Interface Web

L'interface web permet de naviguer dans le Knowledge Graph via une interface Linked Data.

### Prérequis
- Fuseki doit être lancé avec le dataset `tolkien` chargé
- Le KG doit avoir été généré et uploadé (via `main.py`)

### Lancer le serveur Flask

```bash
cd code
python interface.py
```

L'interface sera accessible sur : **http://localhost:5000**

### Fonctionnalités de l'interface

| Route | Description |
|-------|-------------|
| `/` | Page d'accueil avec statistiques du KG |
| `/resource/<nom>` | Description d'une entité (ex: `/resource/Elrond`) |
| `/browse/<type>` | Liste des entités par type (Character, Location, etc.) |
| `/search?q=<terme>` | Recherche d'entités |

### Négociation de contenu

L'interface supporte la **négociation de contenu** :
- `Accept: text/html` → Page HTML
- `Accept: text/turtle` → Données RDF Turtle

---

## Accès SPARQL Direct

Une fois Fuseki lancé avec les données, vous pouvez interroger le KG via SPARQL :

**Endpoint :** `http://localhost:3030/tolkien/query`

---

## Scripts Utilitaires

### Vérifier le statut de Fuseki

```bash
cd code
python fuseki_client.py
```

---

## Technologies Utilisées

| Technologie | Usage |
|-------------|-------|
| **rdflib** | Manipulation RDF Python |
| **SPARQLWrapper** | Requêtes SPARQL |
| **mwparserfromhell** | Parsing wikitext MediaWiki |
| **mwclient** | Client API MediaWiki |
| **Flask** | Interface web |
| **pyshacl** | Validation SHACL |
| **Apache Jena Fuseki** | Triplestore SPARQL |

---

## Sources de Données

1. **Tolkien Gateway** - Wiki principal (API MediaWiki)
2. **MECCG Cards** (`cards.json`) - Cartes du jeu Middle Earth CCG
3. **LOTR Characters** (`lotr_characters.csv`) - Dataset personnages
4. **Fandom Wiki** - Labels multilingues
5. **DBpedia / Wikidata** - Alignements externes

---

##  Auteurs

Projet réalisé dans le cadre du cours **Semantic Web** - EMSE par Aymane Zennouhi & Ozan Gunes.

---

