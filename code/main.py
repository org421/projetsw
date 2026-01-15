"""
Pipeline de construction du Tolkien Knowledge Graph.
Orchestration de l'extraction, de l'enrichissement et de la validation des données RDF.
"""

import sys
import os

# Configuration du path pour les imports locaux
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD, FOAF
from urllib.parse import quote

from tolkien_kg.api import MediaWikiClient
from tolkien_kg.parsers import GenericInfoboxParser
from tolkien_kg.rdf import RDFGenerator, VocabularyGenerator
from tolkien_kg.external import (
    MECCGCardParser, MECCGRDFGenerator, MECCGMatcher,
    LOTRCharacterCSVParser, LOTRCSVMatcher,
)
from tolkien_kg.alignments import add_alignments_to_kg
from tolkien_kg.shacl import SHACLGenerator, SHACLValidator
from tolkien_kg.links import LinkExtractor, add_links_to_rdf
from tolkien_kg.multilingual import FandomEnricher
from fuseki_client import upload_to_fuseki

# Configuration
LIMIT = 300
CSV_FILE = "lotr_characters.csv"
JSON_FILE = "cards.json"

# Namespaces
TOLKIEN = Namespace("https://tolkiengateway.net/wiki/")
TOLKIEN_PROP = Namespace("https://tolkiengateway.net/wiki/Property:")
TOLKIEN_CLASS = Namespace("https://tolkiengateway.net/wiki/Class:")
SCHEMA = Namespace("http://schema.org/")
DBPEDIA = Namespace("http://dbpedia.org/resource/")
WIKIDATA = Namespace("http://www.wikidata.org/entity/")
YAGO = Namespace("http://yago-knowledge.org/resource/")


def print_header(title: str):
    """Affiche un en-tête formaté."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70 + "\n")


def print_subheader(title: str):
    """Affiche un sous-titre."""
    print(f"\n--- {title} ---\n")


def check_file_exists(filepath: str) -> bool:
    """Vérifie la présence d'un fichier nécessaire."""
    if os.path.exists(filepath):
        print(f"Fichier trouvé : {filepath}")
        return True
    print(f"Attention : Fichier manquant ({filepath})")
    return False


def test_api(client: MediaWikiClient) -> dict:
    """Test de connexion à l'API MediaWiki."""
    print_header("ÉTAPE 1 : TEST CONNEXION API")
    print("Connexion à l'API Tolkien Gateway...")
    
    try:
        stats = client.get_wiki_statistics()
        print("Connexion établie.")
        print(f"Pages : {stats.get('pages', 'N/A')}")
        print(f"Articles : {stats.get('articles', 'N/A')}")
        return stats
    except Exception as e:
        print(f"Erreur de connexion : {e}")
        return {}


def get_entities_by_template(client: MediaWikiClient, limit: int) -> dict:
    """Récupération des titres de pages par type d'infobox."""
    print_header("ÉTAPE 2 : RÉCUPÉRATION DES ENTITÉS")
    
    templates = [
        ("Infobox character", limit),
        ("Location infobox", limit),
        ("Kingdom", limit),
        ("Object infobox", limit),
        ("Battle", limit),
        ("Race infobox", limit),
        ("Book", limit),
    ]
    
    entities_by_type = {}
    all_entities = set()
    
    for template_name, template_limit in templates:
        print(f"Récupération : {template_name}...", end=" ", flush=True)
        entities = []
        try:
            for page in client.get_pages_using_template(template_name, limit=template_limit):
                entities.append(page['title'])
                all_entities.add(page['title'])
        except Exception as e:
            print(f"Erreur : {e}")
            continue
        
        entities_by_type[template_name] = entities
        print(f"{len(entities)} entités.")
    
    print(f"\nTotal entités uniques : {len(all_entities)}")
    return entities_by_type, all_entities


def parse_and_generate_rdf(client: MediaWikiClient, parser: GenericInfoboxParser,
                           rdf_gen: RDFGenerator, entities_by_type: dict) -> list:
    """Parsing des pages et génération du graphe RDF initial."""
    print_header("ÉTAPE 3 : PARSING ET GÉNÉRATION RDF")
    
    pages_processed = []
    errors = []
    
    for template_name, entities in entities_by_type.items():
        print(f"\nTraitement : {template_name}")
        count = 0
        
        for title in entities:
            try:
                wikitext = client.get_page_wikitext(title)
                if wikitext:
                    entity_data = parser.parse_any(wikitext, page_title=title)
                    if entity_data:
                        rdf_gen.add_entity(entity_data)
                        pages_processed.append(title)
                        count += 1
            except Exception as e:
                errors.append((title, str(e)))
        
        print(f"Progression : {count}/{len(entities)}")
    
    print(f"\nBilan Parsing :")
    print(f"Pages traitées : {len(pages_processed)}")
    print(f"Triplets générés : {len(rdf_gen.graph)}")
    print(f"Erreurs : {len(errors)}")
    
    return pages_processed


def integrate_csv(csv_file: str, wiki_entities: set, rdf_gen: RDFGenerator):
    """Enrichissement du graphe via le dataset CSV."""
    print_header("ÉTAPE 4 : INTÉGRATION CSV")
    
    if not check_file_exists(csv_file):
        return None
    
    try:
        parser = LOTRCharacterCSVParser(csv_file)
        parser.load()
        print(f"Entrées CSV chargées : {len(parser.characters)}")
        
        matcher = LOTRCSVMatcher(parser)
        matcher.match_with_wiki_entities(wiki_entities)
        
        match_stats = matcher.get_match_statistics()
        print(f"Correspondances : {match_stats['matched']}/{match_stats['total_csv']} ({match_stats['match_rate']:.1f}%)")
        
        triplets_added = matcher.enrich_kg(rdf_gen.graph)
        print(f"Triplets ajoutés : {triplets_added}")
        return matcher
        
    except Exception as e:
        print(f"Erreur intégration CSV : {e}")
        return None


def integrate_meccg(json_file: str, wiki_entities: set, rdf_gen: RDFGenerator):
    """Intégration des données des cartes MECCG (JSON)."""
    print_header("ÉTAPE 5 : INTÉGRATION MECCG")
    
    if not check_file_exists(json_file):
        return None, None
    
    try:
        card_parser = MECCGCardParser(json_file)
        card_parser.load()
        
        stats = card_parser.get_statistics()
        print(f"Cartes chargées : {stats['total_cards']}")
        
        meccg_rdf = MECCGRDFGenerator()
        meccg_rdf.add_cards(card_parser.cards)
        print(f"Graphe MECCG : {len(meccg_rdf.graph)} triplets.")
        
        matcher = MECCGMatcher(card_parser)
        matcher.match_with_wiki_entities(wiki_entities)
        
        match_stats = matcher.get_match_statistics()
        print(f"Correspondances : {match_stats['total_matches']} ({match_stats['match_rate']:.1f}%)")
        
        links = matcher.add_links_to_graph(meccg_rdf, kg_graph=rdf_gen.graph)
        print(f"Liens inter-graphes : {links}")
        
        return meccg_rdf, card_parser
        
    except Exception as e:
        print(f"Erreur intégration MECCG : {e}")
        return None, None


def add_multilingual_labels(graph: Graph, wiki_entities: set, limit: int = None):
    """Enrichissement multilingue via API externe."""
    print_header("ÉTAPE 6 : LABELS MULTILINGUES")
    
    enricher = FandomEnricher()
    stats = {"enriched": 0, "labels_added": 0}
    
    entities = list(wiki_entities)
    if limit:
        entities = entities[:limit]
    
    print(f"Traitement de {len(entities)} entités...")
    
    for i, entity_name in enumerate(entities):
        if (i + 1) % 10 == 0:
            print(f"Progression : {i + 1}/{len(entities)}")
        
        try:
            translations = enricher.get_translations(entity_name)
            if translations:
                stats["enriched"] += 1
                safe_name = quote(entity_name.replace(' ', '_'), safe='')
                entity_uri = URIRef(f"https://tolkiengateway.net/wiki/{safe_name}")
                
                for lang_code, label_text in translations.items():
                    clean_label = label_text.split('(')[0].strip()
                    if clean_label:
                        graph.add((entity_uri, RDFS.label, Literal(clean_label, lang=lang_code)))
                        stats["labels_added"] += 1
        except Exception:
            pass
    
    enricher.save_cache()
    print(f"\nLabels ajoutés : {stats['labels_added']}")
    return stats["labels_added"]


def add_external_alignments(graph: Graph, entities: set, client: MediaWikiClient):
    """Alignement vers DBpedia/Wikidata (owl:sameAs)."""
    print_header("ÉTAPE 7 : ALIGNEMENTS EXTERNES")
    count = add_alignments_to_kg(graph, client, list(entities), verbose=True)
    print(f"Alignements générés : {count}")
    return count


def add_internal_links(client: MediaWikiClient, rdf_gen: RDFGenerator, 
                       pages: list, limit_per_page: int = None):
    """Extraction des liens internes entre pages Wiki."""
    print_header("ÉTAPE 8 : LIENS INTERNES")
    
    link_extractor = LinkExtractor(client)
    print(f"Extraction pour {len(pages)} pages (max {limit_per_page} liens/page).")
    
    try:
        links, images = add_links_to_rdf(
            rdf_gen, link_extractor, pages,
            limit_per_page=limit_per_page, show_progress=False
        )
        print(f"Liens ajoutés : {links}")
        print(f"Images ajoutées : {images}")
        return links
    except Exception as e:
        print(f"Erreur liens internes : {e}")
        return 0


def generate_vocabulary():
    """Génération de l'ontologie RDFS/OWL."""
    print_header("ÉTAPE 9 : VOCABULAIRE")
    
    vocab_gen = VocabularyGenerator()
    vocab_gen.generate_vocabulary()
    
    output_file = "tolkien_vocabulary.ttl"
    vocab_gen.save(output_file)
    print(f"Vocabulaire ({len(vocab_gen.graph)} triplets) sauvegardé : {output_file}")
    return vocab_gen


def generate_shacl_shapes():
    """Génération des shapes SHACL pour validation."""
    print_header("ÉTAPE 10 : SHAPES SHACL")
    
    shacl_gen = SHACLGenerator()
    shacl_gen.create_all_shapes()
    
    output_file = "tolkien_shapes.ttl"
    shacl_gen.save(output_file)
    print(f"Shapes ({len(shacl_gen.graph)} triplets) sauvegardés : {output_file}")
    return shacl_gen


def validate_kg(data_graph: Graph, shapes_graph: Graph):
    """Validation du graphe RDF par SHACL."""
    print_header("ÉTAPE 11 : VALIDATION")
    
    try:
        validator = SHACLValidator(shapes_graph=shapes_graph)
        report = validator.validate_and_report(data_graph)
        
        if report['valid'] is None:
            print("Validation impossible (pyshacl manquant).")
            return None
        
        validator.print_report(report, max_details=5)
        return report
    except Exception as e:
        print(f"Erreur validation : {e}")
        return None


def save_and_show_stats(rdf_gen: RDFGenerator, meccg_rdf, vocab_gen, shacl_gen):
    """Fusion, export et statistiques finales."""
    print_header("ÉTAPE 12 : EXPORT ET STATISTIQUES")
    
    merged = Graph()
    
    # Fusion graphe principal
    for prefix, ns in rdf_gen.graph.namespaces():
        merged.bind(prefix, ns)
    for triple in rdf_gen.graph:
        merged.add(triple)
    
    # Fusion graphe MECCG
    if meccg_rdf:
        for prefix, ns in meccg_rdf.graph.namespaces():
            try:
                merged.bind(prefix, ns)
            except:
                pass
        for triple in meccg_rdf.graph:
            merged.add(triple)
    
    print("Sauvegarde...")
    rdf_gen.save("tolkien_kg.ttl", format="turtle")
    
    if meccg_rdf:
        meccg_rdf.save("meccg_cards.ttl", format="turtle")
    
    merged.serialize(destination="tolkien_kg_complete.ttl", format="turtle")
    merged.serialize(destination="tolkien_kg_complete.nt", format="nt")
    print("Fichiers .ttl et .nt générés.")
    
    print_subheader("STATISTIQUES FINALES")
    
    stats = rdf_gen.get_statistics()
    print(f"Triplets (Principal) : {stats['total_triples']}")
    print(f"Triplets (Complet) : {len(merged)}")
    print(f"Sujets uniques : {stats['subjects']}")
    print(f"Prédicats uniques : {stats['predicates']}")
    
    # Stats par type
    type_counts = {}
    for s, p, o in merged.triples((None, RDF.type, None)):
        type_name = str(o).split('/')[-1].split('#')[-1]
        type_counts[type_name] = type_counts.get(type_name, 0) + 1
    
    print("\nTop Types :")
    for type_name, count in sorted(type_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  - {type_name}: {count}")
    
    alignment_count = len(list(merged.triples((None, OWL.sameAs, None))))
    print(f"\nAlignements (owl:sameAs) : {alignment_count}")
    
    return merged


def show_examples(graph: Graph, entities: set, limit: int = 3):
    """Affiche un échantillon de données."""
    print_header("ÉCHANTILLON")
    
    count = 0
    for entity_name in list(entities)[:50]:
        uri = URIRef(f"https://tolkiengateway.net/wiki/{quote(entity_name.replace(' ', '_'), safe='')}")
        triples = list(graph.triples((uri, None, None)))
        
        if len(triples) >= 5:
            print(f"\nEntité : {entity_name}")
            print("-" * 40)
            for s, p, o in triples[:10]:
                pred = str(p).split('/')[-1].split('#')[-1]
                obj = str(o)[:50] + "..." if len(str(o)) > 50 else str(o)
                print(f"  {pred}: {obj}")
            
            count += 1
            if count >= limit:
                break


def main():
    """Exécution du pipeline."""
    print("\n" + "=" * 70)
    print(f" PIPELINE TOLKIEN KG (Limit: {LIMIT})")
    print("=" * 70)
    
    # Vérifications
    print("\nFichiers sources :")
    check_file_exists(CSV_FILE)
    check_file_exists(JSON_FILE)
    
    # Initialisation
    client = MediaWikiClient()
    parser = GenericInfoboxParser()
    rdf_gen = RDFGenerator()
    
    # Pipeline
    if not test_api(client):
        return
    
    entities_by_type, all_entities = get_entities_by_template(client, LIMIT)
    if not all_entities:
        return
        
    pages = parse_and_generate_rdf(client, parser, rdf_gen, entities_by_type)
    integrate_csv(CSV_FILE, all_entities, rdf_gen)
    meccg_rdf, _ = integrate_meccg(JSON_FILE, all_entities, rdf_gen)
    add_multilingual_labels(rdf_gen.graph, all_entities)
    add_external_alignments(rdf_gen.graph, all_entities, client)
    add_internal_links(client, rdf_gen, pages, limit_per_page=10)
    
    vocab_gen = generate_vocabulary()
    shacl_gen = generate_shacl_shapes()
    
    validate_kg(rdf_gen.graph, shacl_gen.graph)
    merged_graph = save_and_show_stats(rdf_gen, meccg_rdf, vocab_gen, shacl_gen)
    
    show_examples(merged_graph, all_entities, limit=3)
    
    # Chargement Fuseki
    print_header("CHARGEMENT FUSEKI")
    try:
        upload_to_fuseki("tolkien_kg_complete.ttl", "http://localhost:3030/tolkien")
        print("Dataset chargé avec succès.")
    except Exception as e:
        print(f"Erreur chargement Fuseki : {e}")

    print("\n" + "=" * 70)
    print(" TRAITEMENT TERMINÉ")
    print("=" * 70)


if __name__ == "__main__":
    main()