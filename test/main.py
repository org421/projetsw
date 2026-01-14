#!/usr/bin/env python3
"""
Main de test - Tolkien Knowledge Graph
Test de toutes les fonctionnalités implémentées avec LIMIT=20

Ce script teste:
1. API MediaWiki (récupération des entités)
2. Parsing des infoboxes (wikitext → données structurées)
3. Génération RDF (données → triplets)
4. Intégration CSV (lotr_characters.csv)
5. Intégration MECCG (cards.json)
6. Labels multilingues (via Fandom API)
7. Alignements externes (DBpedia, Wikidata, YAGO)
8. Liens internes entre pages wiki
9. Génération du vocabulaire/ontologie
10. Génération des shapes SHACL
11. Validation SHACL du KG
"""

import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD, FOAF
from urllib.parse import quote

# Imports des modules du projet
from tolkien_kg.api import MediaWikiClient
from tolkien_kg.parsers import GenericInfoboxParser, WikitextParser
from tolkien_kg.rdf import RDFGenerator, VocabularyGenerator
from tolkien_kg.external import (
    MECCGCardParser, MECCGRDFGenerator, MECCGMatcher,
    LOTRCharacterCSVParser, LOTRCSVMatcher,
)
from tolkien_kg.alignments import *
from tolkien_kg.shacl import SHACLGenerator, SHACLValidator
from tolkien_kg.links import LinkExtractor, add_links_to_rdf
from tolkien_kg.multilingual import FandomEnricher


# =============================================================================
# CONFIGURATION
# =============================================================================

LIMIT = 300  # 20 entités par type d'infobox

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


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def print_header(title: str):
    """Affiche un en-tête formaté."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70 + "\n")


def print_subheader(title: str):
    """Affiche un sous-en-tête."""
    print(f"\n--- {title} ---\n")


def check_file_exists(filepath: str) -> bool:
    """Vérifie si un fichier existe."""
    if os.path.exists(filepath):
        print(f"  ✓ Fichier trouvé: {filepath}")
        return True
    else:
        print(f"  ✗ Fichier manquant: {filepath}")
        return False


# =============================================================================
# ÉTAPE 1: TEST DE L'API MEDIAWIKI
# =============================================================================

def test_api(client: MediaWikiClient) -> dict:
    """Teste l'API MediaWiki et récupère les statistiques du wiki."""
    print_header("ÉTAPE 1: TEST DE L'API MEDIAWIKI")
    
    print("📡 Connexion à l'API Tolkien Gateway...")
    
    try:
        stats = client.get_wiki_statistics()
        print(f"  ✓ Connexion réussie!")
        print(f"  📊 Statistiques du wiki:")
        print(f"     - Pages: {stats.get('pages', 'N/A')}")
        print(f"     - Articles: {stats.get('articles', 'N/A')}")
        print(f"     - Edits: {stats.get('edits', 'N/A')}")
        return stats
    except Exception as e:
        print(f"  ✗ Erreur de connexion: {e}")
        return {}


# =============================================================================
# ÉTAPE 2: RÉCUPÉRATION DES ENTITÉS PAR INFOBOX
# =============================================================================

def get_entities_by_template(client: MediaWikiClient, limit: int) -> dict:
    """Récupère les entités wiki groupées par type d'infobox."""
    print_header("ÉTAPE 2: RÉCUPÉRATION DES ENTITÉS PAR TYPE D'INFOBOX")
    
    # Templates à traiter (les plus importants)
    # Templates à traiter (les plus importants)
    templates = [
        ("Infobox character", limit),
        ("Location infobox", limit),
        ("Kingdom", limit ),
        ("Object infobox", limit),
        ("Battle", limit),
        ("Race infobox", limit),
    ]
    
    entities_by_type = {}
    all_entities = set()
    
    for template_name, template_limit in templates:
        print(f"  📥 {template_name}...", end=" ", flush=True)
        entities = []
        try:
            for page in client.get_pages_using_template(template_name, limit=template_limit):
                entities.append(page['title'])
                all_entities.add(page['title'])
        except Exception as e:
            print(f"Erreur: {e}")
            continue
        
        entities_by_type[template_name] = entities
        print(f"{len(entities)} entités")
    
    print(f"\n  ✓ Total: {len(all_entities)} entités uniques récupérées")
    return entities_by_type, all_entities


# =============================================================================
# ÉTAPE 3: PARSING DES INFOBOXES ET GÉNÉRATION RDF
# =============================================================================

def parse_and_generate_rdf(client: MediaWikiClient, parser: GenericInfoboxParser,
                           rdf_gen: RDFGenerator, entities_by_type: dict) -> list:
    """Parse les infoboxes et génère les triplets RDF."""
    print_header("ÉTAPE 3: PARSING DES INFOBOXES → RDF")
    
    pages_processed = []
    errors = []
    
    for template_name, entities in entities_by_type.items():
        print(f"\n  📝 Traitement de {template_name}...")
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
        
        print(f"     ✓ {count}/{len(entities)} entités parsées")
    
    print(f"\n  📊 Résultat:")
    print(f"     - Entités traitées: {len(pages_processed)}")
    print(f"     - Triplets générés: {len(rdf_gen.graph)}")
    print(f"     - Erreurs: {len(errors)}")
    
    if errors and len(errors) <= 5:
        print(f"\n  ⚠️ Erreurs détaillées:")
        for title, err in errors[:5]:
            print(f"     - {title}: {err[:50]}...")
    
    return pages_processed


# =============================================================================
# ÉTAPE 4: INTÉGRATION DES DONNÉES CSV
# =============================================================================

def integrate_csv(csv_file: str, wiki_entities: set, rdf_gen: RDFGenerator):
    """Intègre les données du fichier CSV."""
    print_header("ÉTAPE 4: INTÉGRATION DES DONNÉES CSV")
    
    if not check_file_exists(csv_file):
        return None
    
    try:
        parser = LOTRCharacterCSVParser(csv_file)
        parser.load()
        print(f"  📊 {len(parser.characters)} personnages chargés du CSV")
        
        # Afficher quelques stats
        stats = parser.get_statistics()
        print(f"     - Avec naissance: {stats.get('with_birth', 0)}")
        print(f"     - Avec décès: {stats.get('with_death', 0)}")
        print(f"     - Avec race: {stats.get('with_race', 0)}")
        
        # Matching
        matcher = LOTRCSVMatcher(parser)
        matcher.match_with_wiki_entities(wiki_entities)
        
        match_stats = matcher.get_match_statistics()
        print(f"\n  🔗 Matching:")
        print(f"     - Matchés: {match_stats['matched']}/{match_stats['total_csv']}")
        print(f"     - Taux: {match_stats['match_rate']:.1f}%")
        
        # Enrichissement
        triplets_before = len(rdf_gen.graph)
        triplets_added = matcher.enrich_kg(rdf_gen.graph)
        print(f"\n  ✓ {triplets_added} triplets ajoutés au KG")
        
        return matcher
        
    except Exception as e:
        print(f"  ✗ Erreur: {e}")
        return None


# =============================================================================
# ÉTAPE 5: INTÉGRATION DES CARTES MECCG
# =============================================================================

def integrate_meccg(json_file: str, wiki_entities: set, rdf_gen: RDFGenerator):
    """Intègre les cartes MECCG."""
    print_header("ÉTAPE 5: INTÉGRATION DES CARTES MECCG")
    
    if not check_file_exists(json_file):
        return None, None
    
    try:
        # Parser les cartes
        card_parser = MECCGCardParser(json_file)
        card_parser.load()
        
        stats = card_parser.get_statistics()
        print(f"  📊 Statistiques des cartes:")
        print(f"     - Total: {stats['total_cards']} cartes")
        print(f"     - Sets: {stats['sets']}")
        print(f"     - Langues: {stats['languages']}")
        
        # Types de cartes
        print(f"     - Types: ", end="")
        type_strs = [f"{t}={c}" for t, c in list(stats['by_type'].items())[:5]]
        print(", ".join(type_strs))
        
        # Générer RDF pour les cartes
        meccg_rdf = MECCGRDFGenerator()
        meccg_rdf.add_cards(card_parser.cards)
        print(f"\n  📝 {len(meccg_rdf.graph)} triplets MECCG générés")
        
        # Matching avec wiki
        matcher = MECCGMatcher(card_parser)
        matcher.match_with_wiki_entities(wiki_entities)
        
        match_stats = matcher.get_match_statistics()
        print(f"\n  🔗 Matching:")
        print(f"     - Cartes matchées: {match_stats['total_matches']}")
        print(f"     - Taux: {match_stats['match_rate']:.1f}%")
        
        # Ajouter les liens au graphe
        links = matcher.add_links_to_graph(meccg_rdf, kg_graph=rdf_gen.graph)
        print(f"\n  ✓ {links} liens créés entre cartes et entités wiki")
        
        return meccg_rdf, card_parser
        
    except Exception as e:
        print(f"  ✗ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return None, None


# =============================================================================
# ÉTAPE 6: LABELS MULTILINGUES
# =============================================================================

def add_multilingual_labels(graph: Graph, wiki_entities: set, limit: int = None):
    """Ajoute les labels multilingues via l'API Fandom."""
    print_header("ÉTAPE 6: LABELS MULTILINGUES (via Fandom API)")
    
    enricher = FandomEnricher()
    
    stats = {
        "scanned": 0,
        "enriched": 0,
        "labels_added": 0
    }
    
    # Limiter pour le test si nécessaire
    entities_to_process = list(wiki_entities)
    if limit:
        entities_to_process = entities_to_process[:limit]
    
    print(f"  🌍 Enrichissement de {len(entities_to_process)} entités...")
    
    for i, entity_name in enumerate(entities_to_process):
        if (i + 1) % 10 == 0:
            print(f"     Progression: {i + 1}/{len(entities_to_process)}")
        
        stats["scanned"] += 1
        
        try:
            translations = enricher.get_translations(entity_name)
            
            if translations:
                stats["enriched"] += 1
                
                # Créer l'URI de l'entité
                safe_name = quote(entity_name.replace(' ', '_'), safe='')
                entity_uri = URIRef(f"https://tolkiengateway.net/wiki/{safe_name}")
                
                for lang_code, label_text in translations.items():
                    # Nettoyer le label
                    clean_label = label_text.split('(')[0].strip()
                    if clean_label:
                        literal = Literal(clean_label, lang=lang_code)
                        graph.add((entity_uri, RDFS.label, literal))
                        stats["labels_added"] += 1
                        
        except Exception as e:
            pass  # Ignorer les erreurs silencieusement
    
    # Sauvegarder le cache
    enricher.save_cache()
    
    print(f"\n  📊 Résultat:")
    print(f"     - Entités scannées: {stats['scanned']}")
    print(f"     - Entités enrichies: {stats['enriched']}")
    print(f"     - Labels ajoutés: {stats['labels_added']}")
    
    return stats["labels_added"]


# =============================================================================
# ÉTAPE 7: ALIGNEMENTS EXTERNES (owl:sameAs)
# =============================================================================

def add_external_alignments(graph: Graph, entities: set, client: MediaWikiClient):
    """Ajoute les alignements externes AUTOMATIQUEMENT via Wikipedia externallinks."""
    print_header("ÉTAPE 7: ALIGNEMENTS EXTERNES (Automatique)")
    
    from tolkien_kg.alignments import add_alignments_to_kg
    
    # Tout est automatique !
    count = add_alignments_to_kg(graph, client, list(entities), verbose=True)
    
    return count

# =============================================================================
# ÉTAPE 8: LIENS INTERNES ENTRE PAGES WIKI
# =============================================================================

def add_internal_links(client: MediaWikiClient, rdf_gen: RDFGenerator, 
                       pages: list, limit_per_page: int = None):
    """Ajoute les liens internes entre pages wiki."""
    print_header("ÉTAPE 8: LIENS INTERNES ENTRE PAGES WIKI")
    
    link_extractor = LinkExtractor(client)
    
    print(f"  🔗 Extraction des liens pour {len(pages)} pages...")
    print(f"     (limité à {limit_per_page} liens par page)")
    
    try:
        total_links, total_images = add_links_to_rdf(
            rdf_gen, 
            link_extractor, 
            pages,
            limit_per_page=limit_per_page,
            show_progress=False
        )
        
        print(f"\n  ✓ Résultat:")
        print(f"     - Liens ajoutés: {total_links}")
        print(f"     - Images ajoutées: {total_images}")
        
        return total_links
        
    except Exception as e:
        print(f"  ✗ Erreur: {e}")
        return 0


# =============================================================================
# ÉTAPE 9: GÉNÉRATION DU VOCABULAIRE/ONTOLOGIE
# =============================================================================

def generate_vocabulary():
    """Génère le vocabulaire RDFS/OWL."""
    print_header("ÉTAPE 9: GÉNÉRATION DU VOCABULAIRE")
    
    vocab_gen = VocabularyGenerator()
    vocab_gen.generate_vocabulary()
    
    print(f"  📝 Vocabulaire généré: {len(vocab_gen.graph)} triplets")
    
    # Sauvegarder
    output_file = "tolkien_vocabulary.ttl"
    vocab_gen.save(output_file)
    print(f"  ✓ Sauvegardé: {output_file}")
    
    return vocab_gen


# =============================================================================
# ÉTAPE 10: GÉNÉRATION DES SHAPES SHACL
# =============================================================================

def generate_shacl_shapes():
    """Génère les shapes SHACL pour la validation."""
    print_header("ÉTAPE 10: GÉNÉRATION DES SHAPES SHACL")
    
    shacl_gen = SHACLGenerator()
    shacl_gen.create_all_shapes()
    
    print(f"  📝 Shapes générés: {len(shacl_gen.graph)} triplets")
    
    # Sauvegarder
    output_file = "tolkien_shapes.ttl"
    shacl_gen.save(output_file)
    print(f"  ✓ Sauvegardé: {output_file}")
    
    return shacl_gen


# =============================================================================
# ÉTAPE 11: VALIDATION SHACL (optionnelle)
# =============================================================================

def validate_kg(data_graph: Graph, shapes_graph: Graph):
    """Valide le KG contre les shapes SHACL."""
    print_header("ÉTAPE 11: VALIDATION SHACL")
    
    try:
        validator = SHACLValidator(shapes_graph=shapes_graph)
        report = validator.validate_and_report(data_graph)
        
        if report['valid'] is None:
            print("  ⚠️ pyshacl non installé - validation ignorée")
            print("     Installez avec: pip install pyshacl")
            return None
        
        validator.print_report(report, max_details=5)
        return report
        
    except Exception as e:
        print(f"  ⚠️ Erreur de validation: {e}")
        return None


# =============================================================================
# ÉTAPE 12: SAUVEGARDE ET STATISTIQUES FINALES
# =============================================================================

def save_and_show_stats(rdf_gen: RDFGenerator, meccg_rdf, vocab_gen, shacl_gen):
    """Sauvegarde tous les graphes et affiche les statistiques."""
    print_header("ÉTAPE 12: SAUVEGARDE ET STATISTIQUES FINALES")
    
    # Créer le graphe fusionné
    merged = Graph()
    
    # Copier les namespaces
    for prefix, ns in rdf_gen.graph.namespaces():
        merged.bind(prefix, ns)
    
    # Ajouter les triplets du KG principal
    for triple in rdf_gen.graph:
        merged.add(triple)
    
    # Ajouter les triplets MECCG
    if meccg_rdf:
        for prefix, ns in meccg_rdf.graph.namespaces():
            try:
                merged.bind(prefix, ns)
            except:
                pass
        for triple in meccg_rdf.graph:
            merged.add(triple)
    
    # Sauvegarder
    print("  💾 Sauvegarde des fichiers...")
    
    # KG principal
    rdf_gen.save("tolkien_kg.ttl", format="turtle")
    print(f"     ✓ tolkien_kg.ttl ({len(rdf_gen.graph)} triplets)")
    
    # Cartes MECCG
    if meccg_rdf:
        meccg_rdf.save("meccg_cards.ttl", format="turtle")
        print(f"     ✓ meccg_cards.ttl ({len(meccg_rdf.graph)} triplets)")
    
    # Graphe fusionné
    merged.serialize(destination="tolkien_kg_complete.ttl", format="turtle")
    print(f"     ✓ tolkien_kg_complete.ttl ({len(merged)} triplets)")
    
    # Format N-Triples (pour Fuseki)
    merged.serialize(destination="tolkien_kg_complete.nt", format="nt")
    print(f"     ✓ tolkien_kg_complete.nt (N-Triples)")
    
    # Statistiques finales
    print_subheader("STATISTIQUES FINALES")
    
    stats = rdf_gen.get_statistics()
    print(f"  📊 Knowledge Graph principal:")
    print(f"     - Triplets: {stats['total_triples']}")
    print(f"     - Sujets uniques: {stats['subjects']}")
    print(f"     - Prédicats uniques: {stats['predicates']}")
    
    # Types d'entités
    print(f"\n  📊 Par type d'entité:")
    type_counts = {}
    for s, p, o in merged.triples((None, RDF.type, None)):
        type_name = str(o).split('/')[-1].split('#')[-1]
        type_counts[type_name] = type_counts.get(type_name, 0) + 1
    
    for type_name, count in sorted(type_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"     - {type_name}: {count}")
    
    # Alignements
    alignment_count = len(list(merged.triples((None, OWL.sameAs, None))))
    print(f"\n  📊 Alignements owl:sameAs: {alignment_count}")
    
    # Labels par langue
    lang_counts = {}
    for s, p, o in merged.triples((None, RDFS.label, None)):
        lang = getattr(o, 'language', 'none') or 'none'
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    
    if lang_counts:
        print(f"\n  📊 Labels par langue:")
        for lang, count in sorted(lang_counts.items(), key=lambda x: -x[1])[:8]:
            print(f"     - {lang}: {count}")
    
    print(f"\n  📊 TOTAL GRAPHE FUSIONNÉ: {len(merged)} triplets")
    
    return merged


# =============================================================================
# AFFICHAGE D'EXEMPLES
# =============================================================================

def show_examples(graph: Graph, entities: set, limit: int = 3):
    """Affiche quelques exemples d'entités enrichies."""
    print_header("EXEMPLES D'ENTITÉS ENRICHIES")
    
    count = 0
    for entity_name in list(entities)[:50]:  # Chercher parmi les 50 premières
        uri = URIRef(f"https://tolkiengateway.net/wiki/{quote(entity_name.replace(' ', '_'), safe='')}")
        triples = list(graph.triples((uri, None, None)))
        
        if len(triples) >= 5:  # Entités avec assez de données
            print(f"\n  📖 {entity_name}")
            print("  " + "-" * 50)
            
            # Grouper par type
            for s, p, o in triples[:15]:
                pred = str(p).split('/')[-1].split('#')[-1]
                obj = str(o)
                if len(obj) > 50:
                    obj = obj[:47] + "..."
                print(f"     {pred}: {obj}")
            
            if len(triples) > 15:
                print(f"     ... et {len(triples) - 15} autres propriétés")
            
            count += 1
            if count >= limit:
                break


# =============================================================================
# FONCTION PRINCIPALE
# =============================================================================

def main():
    """Pipeline complet de test du Knowledge Graph."""
    
    print("\n" + "#" * 70)
    print("#" + " " * 68 + "#")
    print("#     TOLKIEN KNOWLEDGE GRAPH - TEST COMPLET                         #")
    print(f"#     Configuration: LIMIT = {LIMIT} entités par infobox" + " " * (38 - len(str(LIMIT))) + "#")
    print("#" + " " * 68 + "#")
    print("#" * 70)
    
    # Vérifier les fichiers requis
    print("\n📁 Vérification des fichiers requis...")
    check_file_exists(CSV_FILE)
    check_file_exists(JSON_FILE)
    
    # Initialiser les composants
    client = MediaWikiClient()
    parser = GenericInfoboxParser()
    rdf_gen = RDFGenerator()
    
    # ÉTAPE 1: Test API
    api_stats = test_api(client)
    if not api_stats:
        print("\n❌ Impossible de se connecter à l'API. Abandon.")
        return
    
    # ÉTAPE 2: Récupérer les entités
    entities_by_type, all_entities = get_entities_by_template(client, LIMIT)
    if not all_entities:
        print("\n❌ Aucune entité récupérée. Abandon.")
        return
    
    # ÉTAPE 3: Parser et générer RDF
    pages_processed = parse_and_generate_rdf(client, parser, rdf_gen, entities_by_type)
    
    # ÉTAPE 4: Intégrer CSV
    csv_matcher = integrate_csv(CSV_FILE, all_entities, rdf_gen)
    
    # ÉTAPE 5: Intégrer MECCG
    meccg_rdf, meccg_parser = integrate_meccg(JSON_FILE, all_entities, rdf_gen)
    
    # ÉTAPE 6: Labels multilingues (limité pour le test)
    labels_added = add_multilingual_labels(rdf_gen.graph, all_entities, limit=None)
    
    alignments_added = add_external_alignments(rdf_gen.graph, all_entities, client)
    # ÉTAPE 8: Liens internes
    links_added = add_internal_links(client, rdf_gen, pages_processed, limit_per_page=10)
    
    # ÉTAPE 9: Vocabulaire
    vocab_gen = generate_vocabulary()
    
    # ÉTAPE 10: Shapes SHACL
    shacl_gen = generate_shacl_shapes()
    
    # ÉTAPE 11: Validation (optionnelle)
    validate_kg(rdf_gen.graph, shacl_gen.graph)
    
    # ÉTAPE 12: Sauvegarder et statistiques
    merged_graph = save_and_show_stats(rdf_gen, meccg_rdf, vocab_gen, shacl_gen)
    
    # Exemples
    show_examples(merged_graph, all_entities, limit=3)
    
    # Résumé final
    print_header("RÉSUMÉ FINAL")
    
    print("  📁 Fichiers générés:")
    print("     • tolkien_vocabulary.ttl - Vocabulaire/Ontologie")
    print("     • tolkien_shapes.ttl - Shapes SHACL")
    print(f"     • tolkien_kg.ttl - KG principal ({len(rdf_gen.graph)} triplets)")
    if meccg_rdf:
        print(f"     • meccg_cards.ttl - Cartes MECCG ({len(meccg_rdf.graph)} triplets)")
    print(f"     • tolkien_kg_complete.ttl - Graphe fusionné ({len(merged_graph)} triplets)")
    print("     • tolkien_kg_complete.nt - Format N-Triples (pour Fuseki)")
    
    print(f"\n  📊 Récapitulatif:")
    print(f"     • Entités wiki traitées: {len(pages_processed)}")
    print(f"     • Labels multilingues: {labels_added}")
    print(f"     • Alignements externes: {alignments_added}")
    print(f"     • Liens internes: {links_added}")
    
    print("\n" + "=" * 70)
    print(" ✅ TEST COMPLET TERMINÉ AVEC SUCCÈS")
    print("=" * 70)
    
    print("\n🚀 Prochaines étapes (non implémentées):")
    print("   1. Charger tolkien_kg_complete.ttl dans Fuseki")
    print("   2. Créer l'interface Linked Data (serveur web)")
    print("   3. Implémenter les requêtes SPARQL avec raisonnement")
    print("   4. Rédiger le rapport")


if __name__ == "__main__":
    main()