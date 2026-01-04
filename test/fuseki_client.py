#!/usr/bin/env python3
"""
Script d'interaction avec Apache Fuseki
Étape 13 : Chargement et requêtes SPARQL

Ce script permet de :
- Vérifier si Fuseki est en ligne
- Charger des données RDF
- Exécuter des requêtes SPARQL
- Tester l'intégrité du KG
"""

import requests
import json
from typing import Optional, Dict, List, Any


# =============================================================================
# CONFIGURATION
# =============================================================================

FUSEKI_URL = "http://localhost:3030"
DATASET_NAME = "tolkien"

# Endpoints
SPARQL_ENDPOINT = f"{FUSEKI_URL}/{DATASET_NAME}/sparql"
UPDATE_ENDPOINT = f"{FUSEKI_URL}/{DATASET_NAME}/update"
DATA_ENDPOINT = f"{FUSEKI_URL}/{DATASET_NAME}/data"
UPLOAD_ENDPOINT = f"{FUSEKI_URL}/{DATASET_NAME}/data"


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def check_fuseki_status() -> bool:
    """Vérifie si Fuseki est en ligne."""
    try:
        response = requests.get(f"{FUSEKI_URL}/$/ping", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def check_dataset_exists() -> bool:
    """Vérifie si le dataset existe."""
    try:
        response = requests.get(f"{FUSEKI_URL}/$/datasets/{DATASET_NAME}", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def get_dataset_stats() -> Optional[Dict]:
    """Récupère les statistiques du dataset."""
    try:
        response = requests.get(
            f"{FUSEKI_URL}/$/datasets/{DATASET_NAME}/stats",
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except requests.exceptions.RequestException:
        return None


# =============================================================================
# CHARGEMENT DES DONNÉES
# =============================================================================

def upload_rdf_file(filepath: str, content_type: str = "text/turtle") -> bool:
    """
    Charge un fichier RDF dans Fuseki.
    
    Args:
        filepath: Chemin vers le fichier RDF
        content_type: Type MIME (text/turtle, application/n-triples, etc.)
    
    Returns:
        True si le chargement a réussi
    """
    print(f"📤 Chargement de {filepath}...")
    
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
        
        headers = {
            'Content-Type': content_type
        }
        
        response = requests.post(
            UPLOAD_ENDPOINT,
            data=data,
            headers=headers,
            timeout=300  # 5 minutes pour les gros fichiers
        )
        
        if response.status_code in (200, 201, 204):
            print(f"✅ Fichier chargé avec succès!")
            return True
        else:
            print(f"❌ Erreur: {response.status_code} - {response.text}")
            return False
            
    except FileNotFoundError:
        print(f"❌ Fichier non trouvé: {filepath}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur de connexion: {e}")
        return False


def upload_all_files():
    """Charge tous les fichiers RDF du projet."""
    files = [
        ("tolkien_vocabulary.ttl", "text/turtle"),
        ("tolkien_kg_complete.ttl", "text/turtle"),
    ]
    
    for filepath, content_type in files:
        upload_rdf_file(filepath, content_type)


# =============================================================================
# REQUÊTES SPARQL
# =============================================================================

def execute_sparql_query(query: str, format: str = "json") -> Optional[Dict]:
    """
    Exécute une requête SPARQL SELECT.
    
    Args:
        query: Requête SPARQL
        format: Format de sortie (json, xml, csv)
    
    Returns:
        Résultats de la requête ou None
    """
    accept_types = {
        "json": "application/sparql-results+json",
        "xml": "application/sparql-results+xml",
        "csv": "text/csv"
    }
    
    headers = {
        "Accept": accept_types.get(format, "application/sparql-results+json")
    }
    
    try:
        response = requests.post(
            SPARQL_ENDPOINT,
            data={"query": query},
            headers=headers,
            timeout=60
        )
        
        if response.status_code == 200:
            if format == "json":
                return response.json()
            else:
                return {"raw": response.text}
        else:
            print(f"❌ Erreur SPARQL: {response.status_code}")
            print(response.text)
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur de connexion: {e}")
        return None


def execute_sparql_update(update: str) -> bool:
    """
    Exécute une requête SPARQL UPDATE (INSERT/DELETE).
    
    Args:
        update: Requête SPARQL UPDATE
    
    Returns:
        True si la mise à jour a réussi
    """
    try:
        response = requests.post(
            UPDATE_ENDPOINT,
            data={"update": update},
            timeout=60
        )
        
        return response.status_code in (200, 201, 204)
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur de connexion: {e}")
        return False


def print_results(results: Dict, limit: int = 20):
    """Affiche les résultats d'une requête SPARQL de manière lisible."""
    if not results or "results" not in results:
        print("Aucun résultat")
        return
    
    bindings = results["results"]["bindings"]
    vars = results["head"]["vars"]
    
    if not bindings:
        print("Aucun résultat")
        return
    
    # Calculer la largeur des colonnes
    widths = {var: len(var) for var in vars}
    for binding in bindings[:limit]:
        for var in vars:
            if var in binding:
                value = binding[var]["value"]
                # Tronquer les URIs longues
                if len(value) > 50:
                    value = "..." + value[-47:]
                widths[var] = max(widths[var], len(value))
    
    # En-tête
    header = " | ".join(var.ljust(widths[var]) for var in vars)
    print(header)
    print("-" * len(header))
    
    # Lignes
    for binding in bindings[:limit]:
        row = []
        for var in vars:
            if var in binding:
                value = binding[var]["value"]
                if len(value) > 50:
                    value = "..." + value[-47:]
            else:
                value = ""
            row.append(value.ljust(widths[var]))
        print(" | ".join(row))
    
    if len(bindings) > limit:
        print(f"\n... et {len(bindings) - limit} autres résultats")
    
    print(f"\nTotal: {len(bindings)} résultats")


# =============================================================================
# REQUÊTES DE TEST
# =============================================================================

def test_count_triples():
    """Compte le nombre total de triplets."""
    print("\n" + "=" * 60)
    print(" TEST 1: Nombre de triplets")
    print("=" * 60)
    
    query = "SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o . }"
    results = execute_sparql_query(query)
    
    if results:
        count = results["results"]["bindings"][0]["count"]["value"]
        print(f"\n📊 Nombre total de triplets: {count}")
    return results


def test_count_by_type():
    """Compte les entités par type."""
    print("\n" + "=" * 60)
    print(" TEST 2: Entités par type")
    print("=" * 60)
    
    query = """
    SELECT ?type (COUNT(?s) AS ?count)
    WHERE {
      ?s a ?type .
    }
    GROUP BY ?type
    ORDER BY DESC(?count)
    LIMIT 15
    """
    results = execute_sparql_query(query)
    
    if results:
        print("\n📊 Types d'entités:")
        print_results(results)
    return results


def test_characters():
    """Liste quelques personnages."""
    print("\n" + "=" * 60)
    print(" TEST 3: Personnages")
    print("=" * 60)
    
    query = """
    PREFIX tolkien_class: <https://tolkiengateway.net/wiki/Class:>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?name
    WHERE {
      ?character a tolkien_class:Character .
      ?character rdfs:label ?name .
      FILTER(lang(?name) = "en" || lang(?name) = "")
    }
    ORDER BY ?name
    LIMIT 20
    """
    results = execute_sparql_query(query)
    
    if results:
        print("\n👤 Personnages:")
        print_results(results)
    return results


def test_multilingual_labels():
    """Compte les labels par langue."""
    print("\n" + "=" * 60)
    print(" TEST 4: Labels multilingues")
    print("=" * 60)
    
    query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?lang (COUNT(*) AS ?count)
    WHERE {
      ?s rdfs:label ?label .
      BIND(lang(?label) AS ?lang)
    }
    GROUP BY ?lang
    ORDER BY DESC(?count)
    """
    results = execute_sparql_query(query)
    
    if results:
        print("\n🌍 Labels par langue:")
        print_results(results)
    return results


def test_external_alignments():
    """Vérifie les alignements externes."""
    print("\n" + "=" * 60)
    print(" TEST 5: Alignements externes (owl:sameAs)")
    print("=" * 60)
    
    query = """
    PREFIX owl: <http://www.w3.org/2002/07/owl#>

    SELECT ?source (COUNT(*) AS ?count)
    WHERE {
      ?s owl:sameAs ?ext .
      BIND(
        IF(CONTAINS(STR(?ext), "dbpedia"), "DBpedia",
        IF(CONTAINS(STR(?ext), "wikidata"), "Wikidata",
        IF(CONTAINS(STR(?ext), "yago"), "YAGO", "Other")))
        AS ?source
      )
    }
    GROUP BY ?source
    ORDER BY DESC(?count)
    """
    results = execute_sparql_query(query)
    
    if results:
        print("\n🔗 Alignements par source:")
        print_results(results)
    return results


def test_meccg_cards():
    """Compte les cartes MECCG."""
    print("\n" + "=" * 60)
    print(" TEST 6: Cartes MECCG")
    print("=" * 60)
    
    query = """
    PREFIX meccg_prop: <https://meccg.net/property/>

    SELECT ?cardType (COUNT(?card) AS ?count)
    WHERE {
      ?card meccg_prop:cardType ?cardType .
    }
    GROUP BY ?cardType
    ORDER BY DESC(?count)
    """
    results = execute_sparql_query(query)
    
    if results:
        print("\n🎴 Cartes MECCG par type:")
        print_results(results)
    return results


def test_linked_entities():
    """Entités liées entre Wiki et MECCG."""
    print("\n" + "=" * 60)
    print(" TEST 7: Entités Wiki ↔ MECCG")
    print("=" * 60)
    
    query = """
    PREFIX meccg_prop: <https://meccg.net/property/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?wikiName ?cardName
    WHERE {
      ?card meccg_prop:depicts ?wikiEntity .
      ?wikiEntity rdfs:label ?wikiName .
      ?card rdfs:label ?cardName .
      FILTER(lang(?wikiName) = "en" || lang(?wikiName) = "")
      FILTER(lang(?cardName) = "en" || lang(?cardName) = "")
    }
    ORDER BY ?wikiName
    LIMIT 20
    """
    results = execute_sparql_query(query)
    
    if results:
        print("\n🔗 Entités liées Wiki ↔ MECCG:")
        print_results(results)
    return results


# =============================================================================
# FONCTION PRINCIPALE
# =============================================================================

def run_all_tests():
    """Exécute tous les tests d'intégrité."""
    print("\n" + "#" * 60)
    print("#" + " " * 58 + "#")
    print("#     TESTS D'INTÉGRITÉ DU KNOWLEDGE GRAPH                #")
    print("#" + " " * 58 + "#")
    print("#" * 60)
    
    # Vérifier Fuseki
    print("\n🔍 Vérification de Fuseki...")
    if not check_fuseki_status():
        print("❌ Fuseki n'est pas accessible sur http://localhost:3030")
        print("   Lancez Fuseki avec: ./fuseki-server --update --mem /tolkien")
        return False
    print("✅ Fuseki est en ligne")
    
    # Vérifier le dataset
    print("\n🔍 Vérification du dataset...")
    if not check_dataset_exists():
        print(f"❌ Le dataset '{DATASET_NAME}' n'existe pas")
        print("   Créez-le via l'interface web ou rechargez les données")
        return False
    print(f"✅ Dataset '{DATASET_NAME}' existe")
    
    # Exécuter les tests
    test_count_triples()
    test_count_by_type()
    test_characters()
    test_multilingual_labels()
    test_external_alignments()
    test_meccg_cards()
    test_linked_entities()
    
    print("\n" + "=" * 60)
    print(" ✅ TOUS LES TESTS TERMINÉS")
    print("=" * 60)
    
    return True


def main():
    """Point d'entrée principal."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python fuseki_client.py [command]")
        print("\nCommandes disponibles:")
        print("  status    - Vérifier le statut de Fuseki")
        print("  upload    - Charger tolkien_kg_complete.ttl")
        print("  test      - Exécuter les tests d'intégrité")
        print("  query     - Mode interactif pour requêtes SPARQL")
        return
    
    command = sys.argv[1].lower()
    
    if command == "status":
        if check_fuseki_status():
            print("✅ Fuseki est en ligne")
            stats = get_dataset_stats()
            if stats:
                print(f"📊 Stats: {json.dumps(stats, indent=2)}")
        else:
            print("❌ Fuseki n'est pas accessible")
    
    elif command == "upload":
        if not check_fuseki_status():
            print("❌ Fuseki n'est pas accessible")
            return
        upload_rdf_file("tolkien_kg_complete.ttl")
    
    elif command == "test":
        run_all_tests()
    
    elif command == "query":
        print("Mode requête SPARQL (tapez 'exit' pour quitter)")
        while True:
            print("\n" + "-" * 40)
            query = input("SPARQL> ").strip()
            if query.lower() == 'exit':
                break
            if query:
                results = execute_sparql_query(query)
                if results:
                    print_results(results)
    
    else:
        print(f"Commande inconnue: {command}")


if __name__ == "__main__":
    main()
