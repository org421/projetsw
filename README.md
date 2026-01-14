# Semantic Web Project: Tolkien Knowledge Graph

**Course:** Semantic Web  
**Date:** January 2026  
**Authors:** Ozan Gunes, Aymane Zennouhi

## Project Overview

This project focuses on the construction of a Tolkien Knowledge Graph based on data extracted from the Tolkien Gateway wiki.
It implements a complete pipeline to extract pages, parse wiki infoboxes, generate RDF data, and structure the knowledge according to Semantic Web standards.

The project aligns its vocabulary with well-known ontologies such as schema.org and integrates external datasets, including collectible card data.
It also provides a SPARQL interface through Apache Jena Fuseki and a Linked Data web interface for data exploration.

## Main turtle

tolkien_kg_complete.ttl

## Repository Structure

The repository is organized as follows:

- **code/**: Main source directory.
  - **main.py**: Entry point of the pipeline. Executes extraction, parsing, enrichment, validation, and export.
  - **interface.py**: Flask web server exposing a Linked Data interface.
  - **fuseki_client.py**: Client for interacting with the Apache Jena Fuseki triplestore.
  - **tolkien_kg/**: Core Python package containing all logic modules:
    - `alignments/`: Alignment logic with external vocabularies (schema.org, DBpedia, Wikidata).
    - `api/`: MediaWiki API client for data retrieval.
    - `external/`: Integration of external datasets (collectible cards, CSV files).
    - `links/`: Extraction and generation of internal links between entities.
    - `multilingual/`: Multilingual label enrichment.
    - `parsers/`: Wikitext and Infobox parsers.
    - `rdf/`: RDF and vocabulary generation logic.
    - `shacl/`: SHACL shapes and validation tools.
    - `config.py`: Global configuration settings.

- **requirements.txt**: Python dependencies.
- **README.md**: Project documentation.

## How to Run the Project

### 1. Prerequisites

- Python 3.8 or higher
- Apache Jena Fuseki running locally (default: `http://localhost:3030/`)

### 2. Installation

Install the required Python dependencies:

```bash
pip install -r requirements.txt