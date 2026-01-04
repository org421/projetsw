#!/usr/bin/env python3
"""
Main script - Étapes 9-12 COMPLÈTES
Pipeline complet de construction du Knowledge Graph Tolkien

Ce script:
- Récupère les entités via l'API Tolkien Gateway
- Parse les infoboxes et génère le KG de base (RDF)
- Intègre les cartes MECCG (JSON)
- Intègre les données CSV
- Ajoute les labels multilingues (étape 11)
- Ajoute les alignements externes DBpedia/Wikidata/YAGO (étape 12)
"""

from tolkien_kg.api import MediaWikiClient
from tolkien_kg.parsers import GenericInfoboxParser
from tolkien_kg.rdf import RDFGenerator, VocabularyGenerator
from tolkien_kg.external import (
    MECCGCardParser, MECCGRDFGenerator, MECCGMatcher,
    LOTRCharacterCSVParser, LOTRCSVMatcher,
)
from tolkien_kg.multilingual import MULTILINGUAL_LABELS
from tolkien_kg.alignments import DBPEDIA_MAPPINGS, WIKIDATA_MAPPINGS

from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD, FOAF
from urllib.parse import quote


# =============================================================================
# CONFIGURATION - MODIFIEZ ICI
# =============================================================================

LIMIT = 5  # Nombre d'entités par infobox (5, 10, 50, 100...)

CSV_FILE = "lotr_characters.csv"
JSON_FILE = "cards.json"

# =============================================================================


# Namespaces
TOLKIEN = Namespace("https://tolkiengateway.net/wiki/")
TOLKIEN_PROP = Namespace("https://tolkiengateway.net/wiki/Property:")
TOLKIEN_CLASS = Namespace("https://tolkiengateway.net/wiki/Class:")
SCHEMA = Namespace("http://schema.org/")
DBPEDIA = Namespace("http://dbpedia.org/resource/")
WIKIDATA = Namespace("http://www.wikidata.org/entity/")
YAGO = Namespace("http://yago-knowledge.org/resource/")
MECCG = Namespace("https://meccg.net/card/")
MECCG_PROP = Namespace("https://meccg.net/property/")


def print_separator(title: str):
    """Affiche un séparateur visuel."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70 + "\n")


# =============================================================================
# ÉTAPE 9-10: API + CSV + MECCG
# =============================================================================

def get_wiki_entities(client: MediaWikiClient, limit_per_template: int) -> set:
    """Récupère les noms des entités du wiki via l'API."""
    print("📡 Récupération des entités du wiki via l'API...")
    
    entities = set()
    
    templates = [
        ("Infobox character", limit_per_template * 2),
        ("Location infobox", limit_per_template),
        ("Kingdom", limit_per_template),
        ("Object infobox", limit_per_template),
    ]
    
    for template_name, limit in templates:
        print(f"  {template_name}...", end=" ", flush=True)
        count = 0
        try:
            for page in client.get_pages_using_template(template_name, limit=limit):
                entities.add(page['title'])
                count += 1
        except Exception as e:
            print(f"Erreur: {e}")
            continue
        print(f"{count} entités")
    
    print(f"\n✓ Total: {len(entities)} entités wiki récupérées")
    return entities


def generate_base_kg(client: MediaWikiClient, parser: GenericInfoboxParser,
                     rdf_gen: RDFGenerator, limit_per_template: int) -> list:
    """Génère le KG de base à partir des entités du wiki."""
    print_separator("ÉTAPE 9: GÉNÉRATION DU KG DE BASE (API)")
    
    templates = [
        ("Infobox character", limit_per_template),
        ("Location infobox", limit_per_template // 2),
        ("Kingdom", limit_per_template // 2),
        ("Object infobox", limit_per_template // 2),
    ]
    
    pages_processed = []
    
    for template_name, limit in templates:
        print(f"  {template_name}...", end=" ", flush=True)
        count = 0
        try:
            for page in client.get_pages_using_template(template_name, limit=limit):
                title = page['title']
                try:
                    wikitext = client.get_page_wikitext(title)
                    if wikitext:
                        entity = parser.parse_any(wikitext, page_title=title)
                        if entity:
                            rdf_gen.add_entity(entity)
                            pages_processed.append(title)
                            count += 1
                except:
                    pass
        except Exception as e:
            print(f"Erreur: {e}")
            continue
        print(f"{count} OK")
    
    print(f"\n✓ Total: {len(pages_processed)} entités parsées, {len(rdf_gen.graph)} triplets")
    return pages_processed


def integrate_csv_data(csv_file: str, wiki_entities: set, rdf_gen: RDFGenerator):
    """Intègre les données du CSV au KG."""
    print_separator("ÉTAPE 10a: INTÉGRATION DES DONNÉES CSV")
    
    try:
        parser = LOTRCharacterCSVParser(csv_file)
        parser.load()
    except Exception as e:
        print(f"⚠️ Erreur chargement CSV: {e}")
        return None
    
    print(f"📊 Chargé {len(parser.characters)} personnages du CSV")
    
    matcher = LOTRCSVMatcher(parser)
    matcher.match_with_wiki_entities(wiki_entities)
    
    # Statistiques
    match_stats = matcher.get_match_statistics()
    print(f"\n📈 Résultats du matching:")
    print(f"   Personnages CSV: {match_stats['total_csv']}")
    print(f"   Matchés avec wiki: {match_stats['matched']}")
    print(f"   Taux de match: {match_stats['match_rate']:.1f}%")
    
    # Enrichir le KG
    triplets_added = matcher.enrich_kg(rdf_gen.graph)
    print(f"\n✓ {triplets_added} triplets ajoutés au KG")
    
    return matcher


def integrate_meccg_data(json_file: str, wiki_entities: set, rdf_gen: RDFGenerator):
    """Intègre les cartes MECCG."""
    print_separator("ÉTAPE 10b: INTÉGRATION DES CARTES MECCG")
    
    try:
        card_parser = MECCGCardParser(json_file)
        card_parser.load()
    except Exception as e:
        print(f"⚠️ Erreur chargement MECCG: {e}")
        return None, None
    
    print(f"📊 Chargé {len(card_parser.cards)} cartes")
    
    meccg_rdf = MECCGRDFGenerator()
    meccg_rdf.add_cards(card_parser.cards)
    
    matcher = MECCGMatcher(card_parser)
    matcher.match_with_wiki_entities(wiki_entities)
    
    # Ajouter les liens
    links = matcher.add_links_to_graph(meccg_rdf, kg_graph=rdf_gen.graph)
    
    match_stats = matcher.get_match_statistics()
    print(f"   Cartes parsées: {len(card_parser.cards)}")
    print(f"   Matchées avec wiki: {match_stats['total_matches']}")
    print(f"   Liens créés: {links}")
    print(f"\n✓ Triplets MECCG: {len(meccg_rdf.graph)}")
    
    return meccg_rdf, card_parser


# =============================================================================
# ÉTAPE 11: LABELS MULTILINGUES
# =============================================================================

def add_multilingual_labels(graph: Graph, wiki_entities: set, meccg_cards=None) -> int:
    """
    Ajoute les labels multilingues aux entités.
    Utilise les données du dictionnaire MULTILINGUAL_LABELS
    et les noms multilingues des cartes MECCG.
    """
    print_separator("ÉTAPE 11: LABELS MULTILINGUES")
    
    labels_added = 0
    entities_with_labels = 0
    
    # 1. Labels depuis le dictionnaire MULTILINGUAL_LABELS
    print("📚 Ajout des labels depuis le dictionnaire multilingue...")
    
    for entity_name in wiki_entities:
        if entity_name in MULTILINGUAL_LABELS:
            uri = URIRef(f"https://tolkiengateway.net/wiki/{quote(entity_name.replace(' ', '_'), safe='')}")
            entity_labels = 0
            
            for lang, label in MULTILINGUAL_LABELS[entity_name].items():
                if label and lang != 'en':  # Le label anglais est déjà là
                    graph.add((uri, RDFS.label, Literal(label, lang=lang)))
                    labels_added += 1
                    entity_labels += 1
            
            if entity_labels > 0:
                entities_with_labels += 1
    
    print(f"   Labels du dictionnaire: {labels_added} (pour {entities_with_labels} entités)")
    
    # 2. Labels depuis les cartes MECCG (noms multilingues)
    meccg_labels = 0
    if meccg_cards:
        print("🎴 Ajout des labels depuis les cartes MECCG...")
        
        for card in meccg_cards:
            if card.get('type') not in ('Character', 'Site', 'Region'):
                continue
            
            names = card.get('name', {})
            en_name = names.get('en', '')
            
            if not en_name:
                continue
            
            # Chercher si cette entité existe dans le wiki
            matched = None
            for wiki_name in wiki_entities:
                if wiki_name.lower() == en_name.lower():
                    matched = wiki_name
                    break
            
            if matched:
                uri = URIRef(f"https://tolkiengateway.net/wiki/{quote(matched.replace(' ', '_'), safe='')}")
                
                for lang, name in names.items():
                    if name and len(lang) == 2 and lang != 'en':
                        graph.add((uri, RDFS.label, Literal(name, lang=lang)))
                        meccg_labels += 1
        
        print(f"   Labels MECCG: {meccg_labels}")
    
    total = labels_added + meccg_labels
    print(f"\n✓ Total labels multilingues ajoutés: {total}")
    
    # Statistiques par langue
    lang_stats = {}
    for s, p, o in graph.triples((None, RDFS.label, None)):
        if hasattr(o, 'language') and o.language:
            lang = o.language
            lang_stats[lang] = lang_stats.get(lang, 0) + 1
    
    if lang_stats:
        print("\n📊 Labels par langue:")
        for lang, count in sorted(lang_stats.items(), key=lambda x: -x[1]):
            print(f"   {lang}: {count}")
    
    return total


# =============================================================================
# ÉTAPE 12: ALIGNEMENTS EXTERNES
# =============================================================================

def add_external_alignments(graph: Graph, wiki_entities: set) -> int:
    """
    Ajoute les alignements owl:sameAs vers DBpedia, Wikidata et YAGO.
    """
    print_separator("ÉTAPE 12: ALIGNEMENTS EXTERNES")
    
    # Bind namespaces
    graph.bind("dbpedia", DBPEDIA)
    graph.bind("wikidata", WIKIDATA)
    graph.bind("yago", YAGO)
    graph.bind("foaf", FOAF)
    
    alignments = 0
    entities_aligned = 0
    
    dbpedia_count = 0
    wikidata_count = 0
    yago_count = 0
    
    print("🔗 Ajout des alignements owl:sameAs...")
    
    for entity_name in wiki_entities:
        uri = URIRef(f"https://tolkiengateway.net/wiki/{quote(entity_name.replace(' ', '_'), safe='')}")
        entity_alignments = 0
        
        # DBpedia
        if entity_name in DBPEDIA_MAPPINGS:
            dbpedia_name = DBPEDIA_MAPPINGS[entity_name]
            graph.add((uri, OWL.sameAs, DBPEDIA[dbpedia_name]))
            dbpedia_count += 1
            entity_alignments += 1
            
            # YAGO utilise les mêmes identifiants que DBpedia
            graph.add((uri, OWL.sameAs, YAGO[dbpedia_name]))
            yago_count += 1
            entity_alignments += 1
        
        # Wikidata
        if entity_name in WIKIDATA_MAPPINGS:
            qid = WIKIDATA_MAPPINGS[entity_name]
            graph.add((uri, OWL.sameAs, WIKIDATA[qid]))
            wikidata_count += 1
            entity_alignments += 1
        
        if entity_alignments > 0:
            entities_aligned += 1
            alignments += entity_alignments
    
    print(f"   DBpedia: {dbpedia_count} alignements")
    print(f"   Wikidata: {wikidata_count} alignements")
    print(f"   YAGO: {yago_count} alignements")
    print(f"\n✓ Total: {alignments} alignements pour {entities_aligned} entités")
    
    return alignments


# =============================================================================
# AFFICHAGE ET SAUVEGARDE
# =============================================================================

def show_enriched_entity_examples(graph: Graph, wiki_entities: set, limit: int = 5):
    """Affiche des exemples d'entités enrichies."""
    print_separator("EXEMPLES D'ENTITÉS ENRICHIES")
    
    count = 0
    for entity_name in wiki_entities:
        uri = URIRef(f"https://tolkiengateway.net/wiki/{quote(entity_name.replace(' ', '_'), safe='')}")
        triples = list(graph.triples((uri, None, None)))
        
        if len(triples) > 5:  # Entités avec assez de données
            print(f"\n📖 {entity_name} ({len(triples)} triplets)")
            print("-" * 50)
            
            # Grouper par type de propriété
            labels = []
            types = []
            alignments = []
            properties = []
            
            for s, p, o in triples:
                pred = str(p)
                if 'label' in pred:
                    lang = getattr(o, 'language', '') or ''
                    labels.append(f"{o}@{lang}" if lang else str(o))
                elif 'type' in pred or 'rdf-syntax' in pred:
                    types.append(str(o).split('/')[-1].split('#')[-1])
                elif 'sameAs' in pred:
                    alignments.append(str(o).split('/')[-1])
                else:
                    pred_name = pred.split('/')[-1].split('#')[-1]
                    obj_str = str(o)[:40]
                    properties.append(f"{pred_name}: {obj_str}")
            
            if types:
                print(f"   Types: {', '.join(types[:5])}")
            if labels:
                print(f"   Labels: {', '.join(labels[:5])}")
            if alignments:
                print(f"   Alignements: {', '.join(alignments[:3])}")
            if properties:
                for prop in properties[:5]:
                    print(f"   {prop}")
            
            count += 1
            if count >= limit:
                break


def show_final_statistics(rdf_gen: RDFGenerator, meccg_rdf, merged_graph: Graph):
    """Affiche les statistiques finales."""
    print_separator("STATISTIQUES FINALES")
    
    print("📊 Knowledge Graph principal:")
    stats = rdf_gen.get_statistics()
    print(f"   Triplets: {stats['total_triples']}")
    print(f"   Sujets uniques: {stats['subjects']}")
    print(f"   Prédicats uniques: {stats['predicates']}")
    
    if meccg_rdf:
        print(f"\n📊 Graphe MECCG:")
        print(f"   Triplets: {len(meccg_rdf.graph)}")
    
    print(f"\n📊 Graphe fusionné complet:")
    print(f"   Triplets: {len(merged_graph)}")
    
    # Compter les types
    print(f"\n📊 Par type d'entité:")
    type_counts = {}
    for s, p, o in merged_graph.triples((None, RDF.type, None)):
        type_name = str(o).split('/')[-1].split('#')[-1]
        type_counts[type_name] = type_counts.get(type_name, 0) + 1
    
    for type_name, count in sorted(type_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"   {type_name}: {count}")
    
    # Compter les alignements
    alignment_count = len(list(merged_graph.triples((None, OWL.sameAs, None))))
    print(f"\n📊 Alignements owl:sameAs: {alignment_count}")
    
    # Compter les labels par langue
    lang_counts = {}
    for s, p, o in merged_graph.triples((None, RDFS.label, None)):
        lang = getattr(o, 'language', 'none') or 'none'
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    
    if lang_counts:
        print(f"\n📊 Labels par langue:")
        for lang, count in sorted(lang_counts.items(), key=lambda x: -x[1]):
            print(f"   {lang}: {count}")


def save_all_graphs(rdf_gen: RDFGenerator, meccg_rdf, merged_graph: Graph):
    """Sauvegarde tous les graphes."""
    print_separator("SAUVEGARDE")
    
    # KG principal
    rdf_gen.save("tolkien_kg.ttl", format="turtle")
    print(f"✓ tolkien_kg.ttl ({len(rdf_gen.graph)} triplets)")
    
    # Cartes MECCG séparément
    if meccg_rdf:
        meccg_rdf.save("meccg_cards.ttl", format="turtle")
        print(f"✓ meccg_cards.ttl ({len(meccg_rdf.graph)} triplets)")
    
    # Graphe fusionné complet
    merged_graph.serialize(destination="tolkien_kg_complete.ttl", format="turtle")
    print(f"✓ tolkien_kg_complete.ttl ({len(merged_graph)} triplets)")
    
    # Version N-Triples (pour Fuseki)
    merged_graph.serialize(destination="tolkien_kg_complete.nt", format="nt")
    print(f"✓ tolkien_kg_complete.nt (format N-Triples pour Fuseki)")


# =============================================================================
# FONCTION PRINCIPALE
# =============================================================================

def main():
    """Pipeline complet de construction du Knowledge Graph."""
    print("\n" + "#" * 70)
    print("#" + " " * 68 + "#")
    print("#     TOLKIEN KNOWLEDGE GRAPH - Pipeline Complet                      #")
    print("#     Étapes 9-12: API + CSV + MECCG + Multilingue + Alignements       #")
    print("#" + " " * 68 + "#")
    print("#" * 70)
    
    print(f"\n⚙️  Configuration: LIMIT = {LIMIT} entités par infobox")
    print(f"    CSV: {CSV_FILE}")
    print(f"    JSON: {JSON_FILE}")
    
    # Initialiser les composants
    client = MediaWikiClient()
    entity_parser = GenericInfoboxParser()
    rdf_gen = RDFGenerator()
    
    # Générer le vocabulaire
    print_separator("VOCABULAIRE")
    vocab_gen = VocabularyGenerator()
    vocab_gen.generate_vocabulary()
    vocab_gen.save("tolkien_vocabulary.ttl")
    
    # =================================================================
    # ÉTAPE 9-10: Récupérer les entités et construire le KG de base
    # =================================================================
    
    # Récupérer les entités wiki
    wiki_entities = get_wiki_entities(client, limit_per_template=LIMIT)
    
    if not wiki_entities:
        print("❌ Aucune entité récupérée. Vérifiez la connexion API.")
        return
    
    # Générer le KG de base
    pages = generate_base_kg(client, entity_parser, rdf_gen, limit_per_template=LIMIT)
    
    print(f"\n📊 KG de base: {len(rdf_gen.graph)} triplets")
    
    # Intégrer les données CSV
    csv_matcher = integrate_csv_data(CSV_FILE, wiki_entities, rdf_gen)
    
    print(f"\n📊 KG après CSV: {len(rdf_gen.graph)} triplets")
    
    # Intégrer les cartes MECCG
    meccg_result = integrate_meccg_data(JSON_FILE, wiki_entities, rdf_gen)
    meccg_rdf = meccg_result[0] if meccg_result else None
    meccg_cards = meccg_result[1].cards if meccg_result and meccg_result[1] else None
    
    print(f"\n📊 KG après MECCG: {len(rdf_gen.graph)} triplets")
    
    # =================================================================
    # ÉTAPE 11: Labels multilingues
    # =================================================================
    
    labels_added = add_multilingual_labels(rdf_gen.graph, wiki_entities, meccg_cards)
    
    print(f"\n📊 KG après labels multilingues: {len(rdf_gen.graph)} triplets")
    
    # =================================================================
    # ÉTAPE 12: Alignements externes
    # =================================================================
    
    alignments_added = add_external_alignments(rdf_gen.graph, wiki_entities)
    
    print(f"\n📊 KG après alignements: {len(rdf_gen.graph)} triplets")
    
    # =================================================================
    # Fusionner les graphes et sauvegarder
    # =================================================================
    
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
    
    # Afficher des exemples
    show_enriched_entity_examples(rdf_gen.graph, wiki_entities, limit=5)
    
    # Statistiques finales
    show_final_statistics(rdf_gen, meccg_rdf, merged)
    
    # Sauvegarder
    save_all_graphs(rdf_gen, meccg_rdf, merged)
    
    # =================================================================
    # Résumé final
    # =================================================================
    
    print_separator("RÉSUMÉ FINAL - ÉTAPES 9-12 COMPLÉTÉES")
    
    print("📁 Fichiers générés:")
    print("   • tolkien_vocabulary.ttl - Vocabulaire/Ontologie")
    print(f"   • tolkien_kg.ttl - KG principal ({len(rdf_gen.graph)} triplets)")
    if meccg_rdf:
        print(f"   • meccg_cards.ttl - Cartes MECCG ({len(meccg_rdf.graph)} triplets)")
    print(f"   • tolkien_kg_complete.ttl - Graphe fusionné ({len(merged)} triplets)")
    print("   • tolkien_kg_complete.nt - Format N-Triples (pour Fuseki)")
    
    print(f"\n📊 Récapitulatif:")
    print(f"   • Entités wiki: {len(wiki_entities)}")
    print(f"   • Labels multilingues: {labels_added}")
    print(f"   • Alignements externes: {alignments_added}")
    
    print("\n" + "=" * 70)
    print(" ✅ ÉTAPES 9-12 TERMINÉES")
    print("=" * 70)
    print("\n🚀 Prochaine étape: Charger tolkien_kg_complete.ttl dans Fuseki (étape 13)")
    print("   Commandes:")
    print("   $ fuseki-server --update --mem /tolkien")
    print("   Puis charger le fichier via l'interface web http://localhost:3030")


if __name__ == "__main__":
    main()
