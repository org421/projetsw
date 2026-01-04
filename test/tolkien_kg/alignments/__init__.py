"""
Module d'alignements externes - Étape 12
Crée des triplets owl:sameAs vers DBpedia, YAGO et Wikidata
"""

import re
from typing import Dict, List, Set, Tuple, Any, Optional
from urllib.parse import quote, unquote
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD


# Namespaces
TOLKIEN = Namespace("https://tolkiengateway.net/wiki/")
TOLKIEN_PROP = Namespace("https://tolkiengateway.net/wiki/Property:")
SCHEMA = Namespace("http://schema.org/")

# Namespaces externes
DBPEDIA = Namespace("http://dbpedia.org/resource/")
DBPEDIA_FR = Namespace("http://fr.dbpedia.org/resource/")
DBPEDIA_DE = Namespace("http://de.dbpedia.org/resource/")
YAGO = Namespace("http://yago-knowledge.org/resource/")
WIKIDATA = Namespace("http://www.wikidata.org/entity/")
WIKIPEDIA = Namespace("https://en.wikipedia.org/wiki/")


# =============================================================================
# MAPPINGS MANUELS VERS WIKIDATA
# Source: Wikidata QIDs pour les entités Tolkien principales
# =============================================================================

WIKIDATA_MAPPINGS = {
    # Personnages principaux
    'Gandalf': 'Q177858',
    'Frodo Baggins': 'Q10862',
    'Bilbo Baggins': 'Q11767',
    'Samwise Gamgee': 'Q193449',
    'Aragorn': 'Q10853',
    'Legolas': 'Q219786',
    'Gimli': 'Q217261',
    'Boromir': 'Q270859',
    'Meriadoc Brandybuck': 'Q506568',
    'Peregrin Took': 'Q286543',
    'Elrond': 'Q182264',
    'Galadriel': 'Q192827',
    'Saruman': 'Q192802',
    'Sauron': 'Q152035',
    'Gollum': 'Q185147',
    'Théoden': 'Q284963',
    'Éowyn': 'Q199551',
    'Éomer': 'Q275986',
    'Faramir': 'Q274818',
    'Denethor II': 'Q275038',
    'Arwen': 'Q214093',
    'Celeborn': 'Q1052752',
    'Thranduil': 'Q583119',
    'Thorin Oakenshield': 'Q220140',
    'Smaug': 'Q276534',
    'Morgoth': 'Q173414',
    'Fëanor': 'Q1354996',
    'Beren': 'Q2483251',
    'Lúthien': 'Q932119',
    'Túrin Turambar': 'Q2579024',
    'Tom Bombadil': 'Q2426953',
    'Treebeard': 'Q673704',
    'Shelob': 'Q683813',
    'Balrog': 'Q188816',
    'Nazgûl': 'Q217062',
    'Witch-king of Angmar': 'Q580523',
    
    # Lieux
    'Middle-earth': 'Q81735',
    'The Shire': 'Q208593',
    'Rivendell': 'Q208640',
    'Mordor': 'Q208655',
    'Gondor': 'Q208674',
    'Rohan': 'Q208711',
    'Isengard': 'Q738691',
    'Minas Tirith': 'Q208648',
    'Moria': 'Q750568',
    'Lothlórien': 'Q579959',
    'Erebor': 'Q1081756',
    'Helm\'s Deep': 'Q693920',
    'Bag End': 'Q1754940',
    'Valinor': 'Q692930',
    'Númenor': 'Q595382',
    'Aman': 'Q579881',
    'Beleriand': 'Q587936',
    'Khazad-dûm': 'Q750568',  # Same as Moria
    'Fangorn': 'Q1352310',
    'Mirkwood': 'Q2587851',
    'Bree': 'Q1737296',
    
    # Objets
    'One Ring': 'Q188727',
    'The One Ring': 'Q188727',
    'Sting': 'Q2608044',
    'Glamdring': 'Q1144802',
    'Andúril': 'Q1777839',
    'Narsil': 'Q1780050',
    'Palantír': 'Q846687',
    'Silmarils': 'Q569697',
    
    # Races/Peuples
    'Elves': 'Q212479',  # Elf (Middle-earth)
    'Dwarves': 'Q2406549',  # Dwarf (Middle-earth)
    'Hobbits': 'Q189988',
    'Orcs': 'Q862463',  # Orc (Middle-earth)
    'Ents': 'Q848696',
    'Maiar': 'Q2529740',
    'Valar': 'Q738030',
    'Ainur': 'Q384073',
    'Uruk-hai': 'Q1761085',
    'Balrogs': 'Q188816',
    
    # Livres
    'The Lord of the Rings': 'Q15228',
    'The Hobbit': 'Q74287',
    'The Silmarillion': 'Q76092',
    'The Fellowship of the Ring': 'Q191058',
    'The Two Towers': 'Q164137',
    'The Return of the King': 'Q166673',
    
    # Auteur
    'J.R.R. Tolkien': 'Q892',
}


# =============================================================================
# MAPPINGS VERS DBPEDIA (noms Wikipedia anglais)
# Ces noms correspondent aux pages Wikipedia/DBpedia
# =============================================================================

DBPEDIA_MAPPINGS = {
    # Personnages
    'Gandalf': 'Gandalf',
    'Frodo Baggins': 'Frodo_Baggins',
    'Bilbo Baggins': 'Bilbo_Baggins',
    'Samwise Gamgee': 'Samwise_Gamgee',
    'Aragorn': 'Aragorn',
    'Legolas': 'Legolas',
    'Gimli': 'Gimli_(Middle-earth)',
    'Boromir': 'Boromir',
    'Meriadoc Brandybuck': 'Meriadoc_Brandybuck',
    'Peregrin Took': 'Peregrin_Took',
    'Elrond': 'Elrond',
    'Galadriel': 'Galadriel',
    'Saruman': 'Saruman',
    'Sauron': 'Sauron',
    'Gollum': 'Gollum',
    'Théoden': 'Théoden',
    'Éowyn': 'Éowyn',
    'Éomer': 'Éomer',
    'Faramir': 'Faramir',
    'Denethor II': 'Denethor',
    'Arwen': 'Arwen',
    'Celeborn': 'Celeborn',
    'Thranduil': 'Thranduil',
    'Thorin Oakenshield': 'Thorin_Oakenshield',
    'Smaug': 'Smaug',
    'Morgoth': 'Morgoth',
    'Fëanor': 'Fëanor',
    'Beren': 'Beren_(Middle-earth)',
    'Lúthien': 'Lúthien',
    'Túrin Turambar': 'Túrin_Turambar',
    'Tom Bombadil': 'Tom_Bombadil',
    'Treebeard': 'Treebeard',
    'Shelob': 'Shelob',
    'Witch-king of Angmar': 'Witch-king_of_Angmar',
    
    # Lieux
    'Middle-earth': 'Middle-earth',
    'The Shire': 'The_Shire',
    'Rivendell': 'Rivendell',
    'Mordor': 'Mordor',
    'Gondor': 'Gondor',
    'Rohan': 'Rohan_(Middle-earth)',
    'Isengard': 'Isengard',
    'Minas Tirith': 'Minas_Tirith',
    'Moria': 'Moria_(Middle-earth)',
    'Lothlórien': 'Lothlórien',
    'Erebor': 'Lonely_Mountain',
    'Helm\'s Deep': 'Helm%27s_Deep',
    'Bag End': 'Bag_End',
    'Valinor': 'Valinor',
    'Númenor': 'Númenor',
    'Aman': 'Aman_(Tolkien)',
    'Beleriand': 'Beleriand',
    'Fangorn': 'Fangorn',
    'Mirkwood': 'Mirkwood',
    'Bree': 'Bree_(Middle-earth)',
    
    # Objets
    'One Ring': 'One_Ring',
    'The One Ring': 'One_Ring',
    'Sting': 'Sting_(Middle-earth)',
    'Glamdring': 'Glamdring',
    'Andúril': 'Andúril',
    'Narsil': 'Narsil',
    'Palantír': 'Palantír',
    'Silmarils': 'Silmarils',
    
    # Races
    'Elves': 'Elf_(Middle-earth)',
    'Dwarves': 'Dwarf_(Middle-earth)',
    'Hobbits': 'Hobbit',
    'Orcs': 'Orc_(Middle-earth)',
    'Ents': 'Ent',
    'Maiar': 'Maia_(Middle-earth)',
    'Valar': 'Vala_(Middle-earth)',
    'Ainur': 'Ainur_(Middle-earth)',
    'Uruk-hai': 'Uruk-hai',
    'Balrog': 'Balrog',
    'Balrogs': 'Balrog',
    'Nazgûl': 'Nazgûl',
    
    # Livres
    'The Lord of the Rings': 'The_Lord_of_the_Rings',
    'The Hobbit': 'The_Hobbit',
    'The Silmarillion': 'The_Silmarillion',
    'The Fellowship of the Ring': 'The_Fellowship_of_the_Ring',
    'The Two Towers': 'The_Two_Towers',
    'The Return of the King': 'The_Return_of_the_King',
}


class ExternalAlignmentGenerator:
    """
    Génère des alignements owl:sameAs vers des sources externes.
    """
    
    def __init__(self):
        self.graph = Graph()
        self._bind_namespaces()
        self.alignments_created = {
            'dbpedia': 0,
            'wikidata': 0,
            'yago': 0,
            'wikipedia': 0,
            'dbpedia_fr': 0,
            'dbpedia_de': 0,
        }
        self.entities_aligned = set()
    
    def _bind_namespaces(self):
        """Lie les préfixes aux namespaces."""
        self.graph.bind("tolkien", TOLKIEN)
        self.graph.bind("owl", OWL)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("dbpedia", DBPEDIA)
        self.graph.bind("dbpedia_fr", DBPEDIA_FR)
        self.graph.bind("dbpedia_de", DBPEDIA_DE)
        self.graph.bind("yago", YAGO)
        self.graph.bind("wikidata", WIKIDATA)
        self.graph.bind("wikipedia", WIKIPEDIA)
    
    def _make_tolkien_uri(self, name: str) -> URIRef:
        """Crée une URI Tolkien Gateway."""
        return TOLKIEN[quote(name.replace(" ", "_"), safe="")]
    
    def add_dbpedia_alignment(self, entity_name: str, dbpedia_name: str = None) -> bool:
        """
        Ajoute un alignement vers DBpedia.
        
        Args:
            entity_name: Nom de l'entité Tolkien
            dbpedia_name: Nom DBpedia (optionnel, déduit si absent)
            
        Returns:
            True si ajouté, False sinon
        """
        tolkien_uri = self._make_tolkien_uri(entity_name)
        
        # Utiliser le mapping ou déduire le nom
        if dbpedia_name is None:
            dbpedia_name = DBPEDIA_MAPPINGS.get(entity_name)
            if dbpedia_name is None:
                # Essayer de déduire
                dbpedia_name = entity_name.replace(" ", "_")
        
        dbpedia_uri = DBPEDIA[dbpedia_name]
        
        # Ajouter le triplet
        self.graph.add((tolkien_uri, OWL.sameAs, dbpedia_uri))
        self.alignments_created['dbpedia'] += 1
        self.entities_aligned.add(entity_name)
        
        return True
    
    def add_wikidata_alignment(self, entity_name: str, qid: str = None) -> bool:
        """
        Ajoute un alignement vers Wikidata.
        
        Args:
            entity_name: Nom de l'entité Tolkien
            qid: QID Wikidata (ex: Q177858 pour Gandalf)
            
        Returns:
            True si ajouté, False sinon
        """
        tolkien_uri = self._make_tolkien_uri(entity_name)
        
        # Utiliser le mapping ou le QID fourni
        if qid is None:
            qid = WIKIDATA_MAPPINGS.get(entity_name)
        
        if qid is None:
            return False
        
        wikidata_uri = WIKIDATA[qid]
        
        self.graph.add((tolkien_uri, OWL.sameAs, wikidata_uri))
        self.alignments_created['wikidata'] += 1
        self.entities_aligned.add(entity_name)
        
        return True
    
    def add_yago_alignment(self, entity_name: str, yago_name: str = None) -> bool:
        """
        Ajoute un alignement vers YAGO.
        YAGO utilise généralement les mêmes noms que DBpedia/Wikipedia.
        
        Args:
            entity_name: Nom de l'entité Tolkien
            yago_name: Nom YAGO (optionnel)
            
        Returns:
            True si ajouté, False sinon
        """
        tolkien_uri = self._make_tolkien_uri(entity_name)
        
        # YAGO utilise souvent le même format que DBpedia
        if yago_name is None:
            yago_name = DBPEDIA_MAPPINGS.get(entity_name)
            if yago_name is None:
                yago_name = entity_name.replace(" ", "_")
        
        yago_uri = YAGO[yago_name]
        
        self.graph.add((tolkien_uri, OWL.sameAs, yago_uri))
        self.alignments_created['yago'] += 1
        self.entities_aligned.add(entity_name)
        
        return True
    
    def add_wikipedia_link(self, entity_name: str, wiki_title: str = None) -> bool:
        """
        Ajoute un lien vers Wikipedia (foaf:page ou schema:sameAs).
        
        Args:
            entity_name: Nom de l'entité Tolkien
            wiki_title: Titre Wikipedia (optionnel)
            
        Returns:
            True si ajouté, False sinon
        """
        from rdflib.namespace import FOAF
        self.graph.bind("foaf", FOAF)
        
        tolkien_uri = self._make_tolkien_uri(entity_name)
        
        if wiki_title is None:
            wiki_title = DBPEDIA_MAPPINGS.get(entity_name)
            if wiki_title is None:
                wiki_title = entity_name.replace(" ", "_")
        
        wiki_uri = WIKIPEDIA[wiki_title]
        
        self.graph.add((tolkien_uri, FOAF.isPrimaryTopicOf, wiki_uri))
        self.alignments_created['wikipedia'] += 1
        
        return True
    
    def add_all_alignments_for_entity(self, entity_name: str) -> Dict[str, bool]:
        """
        Ajoute tous les alignements possibles pour une entité.
        
        Args:
            entity_name: Nom de l'entité
            
        Returns:
            Dict indiquant quels alignements ont été créés
        """
        results = {}
        
        # DBpedia
        if entity_name in DBPEDIA_MAPPINGS:
            results['dbpedia'] = self.add_dbpedia_alignment(entity_name)
            results['yago'] = self.add_yago_alignment(entity_name)
            results['wikipedia'] = self.add_wikipedia_link(entity_name)
        
        # Wikidata
        if entity_name in WIKIDATA_MAPPINGS:
            results['wikidata'] = self.add_wikidata_alignment(entity_name)
        
        return results
    
    def add_alignments_from_mappings(self) -> int:
        """
        Ajoute tous les alignements des mappings prédéfinis.
        
        Returns:
            Nombre total d'alignements créés
        """
        count = 0
        
        # DBpedia (inclut YAGO et Wikipedia)
        for entity_name in DBPEDIA_MAPPINGS.keys():
            self.add_dbpedia_alignment(entity_name)
            self.add_yago_alignment(entity_name)
            self.add_wikipedia_link(entity_name)
            count += 3
        
        # Wikidata
        for entity_name in WIKIDATA_MAPPINGS.keys():
            if self.add_wikidata_alignment(entity_name):
                count += 1
        
        return count
    
    def add_alignments_for_entities(self, entity_names: Set[str]) -> int:
        """
        Ajoute des alignements pour une liste d'entités.
        Tente de créer des alignements même pour les entités non mappées.
        
        Args:
            entity_names: Set de noms d'entités
            
        Returns:
            Nombre d'alignements créés
        """
        count = 0
        
        for name in entity_names:
            # Essayer les mappings existants
            if name in DBPEDIA_MAPPINGS or name in WIKIDATA_MAPPINGS:
                results = self.add_all_alignments_for_entity(name)
                count += sum(1 for v in results.values() if v)
            else:
                # Tenter de créer un alignement DBpedia automatique
                # (peut ne pas être valide, mais utile pour le matching)
                safe_name = name.replace(" ", "_")
                self.add_dbpedia_alignment(name, safe_name)
                count += 1
        
        return count
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques des alignements."""
        return {
            'total_triples': len(self.graph),
            'entities_aligned': len(self.entities_aligned),
            'by_source': self.alignments_created.copy(),
        }
    
    def save(self, filename: str, format: str = "turtle"):
        """Sauvegarde le graphe."""
        self.graph.serialize(destination=filename, format=format)
        print(f"✓ Sauvegardé: {filename} ({len(self.graph)} triplets)")


def print_alignment_examples(graph: Graph, limit: int = 5):
    """Affiche des exemples d'alignements."""
    print("\n📝 Exemples d'alignements:\n")
    
    count = 0
    seen_entities = set()
    
    for s, p, o in graph.triples((None, OWL.sameAs, None)):
        entity = str(s).split('/')[-1].replace('_', ' ').replace('%20', ' ')
        
        if entity in seen_entities:
            continue
        
        seen_entities.add(entity)
        
        # Récupérer tous les alignements pour cette entité
        alignments = list(graph.triples((s, OWL.sameAs, None)))
        
        print(f"   {unquote(entity)}:")
        for _, _, obj in alignments:
            obj_str = str(obj)
            if 'dbpedia.org' in obj_str:
                print(f"     → DBpedia: {obj_str}")
            elif 'wikidata.org' in obj_str:
                print(f"     → Wikidata: {obj_str}")
            elif 'yago' in obj_str:
                print(f"     → YAGO: {obj_str}")
        
        count += 1
        if count >= limit:
            break


def demo_alignments():
    """Démo des alignements externes."""
    print("\n" + "=" * 60)
    print(" DÉMO: Alignements Externes")
    print("=" * 60)
    
    gen = ExternalAlignmentGenerator()
    
    # Ajouter les alignements
    count = gen.add_alignments_from_mappings()
    
    print(f"\n✓ {count} alignements créés")
    
    # Statistiques
    stats = gen.get_statistics()
    print(f"\n📊 Par source:")
    for source, c in stats['by_source'].items():
        if c > 0:
            print(f"   {source}: {c}")
    
    print(f"\n   Total entités: {stats['entities_aligned']}")
    
    # Exemples
    print_alignment_examples(gen.graph)
    
    return gen


if __name__ == "__main__":
    gen = demo_alignments()
    gen.save("tolkien_alignments.ttl")
