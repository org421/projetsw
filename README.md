# Tolkien Knowledge Graph

Semantic Web Project - Building a Knowledge Graph from the **Tolkien Gateway** wiki.

---

## Project Description

This project builds a **Knowledge Graph (KG)** from data on the [Tolkien Gateway](https://tolkiengateway.net/) wiki, following the DBpedia and YAGO approach. The KG captures entities and their relationships, with alignments to external sources.

---

## File Structure

```
code/
  main.py             - launches the KG construction
  interface.py        - launches the web server
  fuseki_client.py    - manages the Fuseki connection
  tolkien_kg/
    api/              - MediaWiki client
    parsers/          - infobox extraction
    rdf/              - RDF triple generation
    external/         - MECCG data + CSV
    alignments/       - DBpedia/Wikidata links
    multilingual/     - multilingual labels
    links/            - internal wiki links
    shacl/            - SHACL validation

source data:          cards.json, lotr_characters.csv
generated files:      tolkien_kg.ttl, tolkien_kg_complete.ttl, meccg_cards.ttl
ontology:             tolkien_vocabulary.ttl, tolkien_shapes.ttl
cache:                alignment_cache.json, fandom_lang_cache.json
```

---

## Installation

### 1. Prerequisites

- **Python 3.8+**
- **Apache Jena Fuseki**

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```


### 3. Install and launch Fuseki

```bash
# Start Fuseki (from the Fuseki folder)
./fuseki-server --update --mem /tolkien

```

Fuseki will be accessible at `http://localhost:3030`

---

## Launch the Main Pipeline

The `main.py` script executes all the KG construction steps:

```bash
cd code
python main.py
```

### Modify the entity limit per infobox type

By default, the pipeline processes **300 entities per infobox type**. To increase or decrease this number, modify the `LIMIT` variable in `main.py` (line 30):

```python
# Line 30 in main.py
LIMIT = 300  # Change this value (e.g.: 500, 1000, or None to retrieve all)
```

### Pipeline Steps

1. **API connection test** - Verifies access to Tolkien Gateway
2. **Entity retrieval** - Lists pages by infobox type
3. **Parsing & RDF generation** - Infobox extraction → RDF triples
4. **CSV integration** - Enrichment with `lotr_characters.csv`
5. **MECCG integration** - Linking with `cards.json` cards
6. **Multilingual labels** - Addition via Fandom wiki (FR, DE, ES, IT, etc.)
7. **External alignments** - `owl:sameAs` links to DBpedia/Wikidata
8. **Internal links** - Relationships between wiki pages
9. **Vocabulary** - RDFS/OWL ontology generation
10. **SHACL shapes** - Validation constraint creation
11. **Validation** - KG verification with pyshacl
12. **Export & Fuseki loading** - `.ttl` saving and upload

---

## Launch the Web Interface

The web interface allows browsing the Knowledge Graph via a Linked Data interface.

### Prerequisites
- Fuseki must be running with the `tolkien` dataset loaded
- The KG must have been generated and uploaded (via `main.py`)

### Launch the Flask server

```bash
cd code
python interface.py
```

The interface will be accessible at: **http://localhost:5000**

### Interface features

| Route | Description |
|-------|-------------|
| `/` | Homepage with KG statistics |
| `/resource/<name>` | Entity description (e.g.: `/resource/Elrond`) |
| `/browse/<type>` | List of entities by type (Character, Location, etc.) |
| `/search?q=<term>` | Entity search |

### Content negotiation

The interface supports **content negotiation**:
- `Accept: text/html` → HTML page
- `Accept: text/turtle` → RDF Turtle data

---

## Direct SPARQL Access

Once Fuseki is running with the data, you can query the KG via SPARQL:

**Endpoint:** `http://localhost:3030/tolkien/query`

---

## Utility Scripts

### Check Fuseki status

```bash
cd code
python fuseki_client.py
```

---

## Technologies Used

| Technology | Usage |
|------------|-------|
| **rdflib** | Python RDF manipulation |
| **SPARQLWrapper** | SPARQL queries |
| **mwparserfromhell** | MediaWiki wikitext parsing |
| **mwclient** | MediaWiki API client |
| **Flask** | Web interface |
| **pyshacl** | SHACL validation |
| **Apache Jena Fuseki** | SPARQL triplestore |

---

## Data Sources

1. **Tolkien Gateway** - Main wiki (MediaWiki API)
2. **MECCG Cards** (`cards.json`) - Middle Earth CCG game cards
3. **LOTR Characters** (`lotr_characters.csv`) - Characters dataset
4. **Fandom Wiki** - Multilingual labels
5. **DBpedia / Wikidata** - External alignments

---

## Authors

Project completed as part of the **Semantic Web** course - EMSE by Aymane Zennouhi & Ozan Gunes.

---

