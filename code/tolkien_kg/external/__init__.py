"""
Intégration des cartes MECCG et données CSV des personnages LOTR.
Crée des liens RDF entre les cartes/données externes et le Knowledge Graph.
"""

import json
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from urllib.parse import quote
from rdflib import Graph, Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, XSD, OWL, FOAF, DC, DCTERMS


TOLKIEN = Namespace("https://tolkiengateway.net/wiki/")
TOLKIEN_PROP = Namespace("https://tolkiengateway.net/wiki/Property:")
TOLKIEN_CLASS = Namespace("https://tolkiengateway.net/wiki/Class:")
MECCG = Namespace("https://tolkiengateway.net/wiki/MECCG/")
MECCG_PROP = Namespace("https://tolkiengateway.net/wiki/MECCG/Property:")
MECCG_CLASS = Namespace("https://tolkiengateway.net/wiki/MECCG/Class:")
SCHEMA = Namespace("http://schema.org/")


class MECCGCardParser:
    """Parse les cartes du jeu Middle-earth: The Wizards depuis cards.json."""
    
    NAME_CORRECTIONS = {
        'Aragorn II': 'Aragorn',
        'Boromir II': 'Boromir',
        'Sam Gamgee': 'Samwise Gamgee',
        'Mouth of Sauron': 'Mouth of Sauron',
        'Gandalf the White Rider': 'Gandalf',
        'Saruman the Wise': 'Saruman',
        'Phial of Galadriel': 'Phial of Galadriel',
        'Bilbo': 'Bilbo Baggins',
        'Frodo': 'Frodo Baggins',
    }
    
    ENTITY_TYPES = {'Character', 'Site', 'Region'}
    
    def __init__(self, json_file: str):
        self.json_file = json_file
        self.data = None
        self.cards = []
        self.sets = {}
    
    def load(self):
        """Charge et parse le fichier JSON."""
        with open(self.json_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        for set_id, set_data in self.data.items():
            self.sets[set_id] = {
                'id': set_id,
                'name': set_data.get('name', {}),
                'card_count': 0
            }
            
            if 'cards' in set_data:
                for card_id, card in set_data['cards'].items():
                    card['_set_id'] = set_id
                    card['_set_name'] = set_data.get('name', {}).get('en', set_id)
                    self.cards.append(card)
                    self.sets[set_id]['card_count'] += 1
        
        print(f"Charge {len(self.cards)} cartes de {len(self.sets)} sets")
        return self
    
    def get_cards_by_type(self, card_type: str) -> List[Dict]:
        return [c for c in self.cards if c.get('type') == card_type]
    
    def get_character_cards(self) -> List[Dict]:
        return self.get_cards_by_type('Character')
    
    def get_site_cards(self) -> List[Dict]:
        return self.get_cards_by_type('Site')
    
    def get_all_entity_cards(self) -> List[Dict]:
        return [c for c in self.cards if c.get('type') in self.ENTITY_TYPES]
    
    def normalize_name(self, name: str) -> str:
        """Normalise un nom de carte pour le matching."""
        if name in self.NAME_CORRECTIONS:
            return self.NAME_CORRECTIONS[name]
        
        normalized = re.sub(r'\s+II$', '', name)
        normalized = re.sub(r'\s*\([^)]+\)\s*$', '', normalized)
        
        return normalized.strip()
    
    def get_statistics(self) -> Dict[str, Any]:
        stats = {
            'total_cards': len(self.cards),
            'sets': len(self.sets),
            'by_type': {},
            'by_alignment': {},
            'by_race': {},
            'languages': set()
        }
        
        for card in self.cards:
            t = card.get('type', 'Unknown')
            stats['by_type'][t] = stats['by_type'].get(t, 0) + 1
            
            a = card.get('alignment', 'Unknown')
            stats['by_alignment'][a] = stats['by_alignment'].get(a, 0) + 1
            
            if t == 'Character':
                race = card.get('attributes', {}).get('race', 'Unknown')
                stats['by_race'][race] = stats['by_race'].get(race, 0) + 1
            
            for lang in card.get('name', {}).keys():
                stats['languages'].add(lang)
        
        stats['languages'] = list(stats['languages'])
        return stats


class MECCGRDFGenerator:
    """Génère des triplets RDF pour les cartes MECCG."""
    
    def __init__(self):
        self.graph = Graph()
        self._bind_namespaces()
    
    def _bind_namespaces(self):
        self.graph.bind("tolkien", TOLKIEN)
        self.graph.bind("tolkien_prop", TOLKIEN_PROP)
        self.graph.bind("tolkien_class", TOLKIEN_CLASS)
        self.graph.bind("meccg", MECCG)
        self.graph.bind("meccg_prop", MECCG_PROP)
        self.graph.bind("meccg_class", MECCG_CLASS)
        self.graph.bind("schema", SCHEMA)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("owl", OWL)
        self.graph.bind("foaf", FOAF)
        self.graph.bind("dc", DC)
    
    def _make_card_uri(self, card_id: str) -> URIRef:
        return MECCG[quote(card_id, safe="")]
    
    def _make_wiki_uri(self, name: str) -> URIRef:
        clean_name = name.replace(" ", "_")
        return TOLKIEN[quote(clean_name, safe="")]
    
    def add_card(self, card: Dict[str, Any]) -> URIRef:
        """Ajoute une carte au graphe RDF."""
        card_id = card.get('id', 'unknown')
        uri = self._make_card_uri(card_id)
        card_type = card.get('type', 'Card')
        
        self.graph.add((uri, RDF.type, MECCG_CLASS.Card))
        
        type_uri = MECCG_CLASS[card_type]
        self.graph.add((uri, RDF.type, type_uri))
        
        if card_type == 'Character':
            self.graph.add((uri, RDF.type, SCHEMA.Person))
        elif card_type == 'Site':
            self.graph.add((uri, RDF.type, SCHEMA.Place))
        
        self.graph.add((uri, DC.identifier, Literal(card_id)))
        
        names = card.get('name', {})
        for lang, name in names.items():
            if name:
                self.graph.add((uri, RDFS.label, Literal(name, lang=lang)))
                if lang == 'en':
                    self.graph.add((uri, SCHEMA.name, Literal(name)))
        
        set_id = card.get('_set_id', '')
        set_name = card.get('_set_name', '')
        if set_id:
            self.graph.add((uri, MECCG_PROP.cardSet, Literal(set_id)))
            self.graph.add((uri, MECCG_PROP.cardSetName, Literal(set_name)))
        
        alignment = card.get('alignment', '')
        if alignment:
            self.graph.add((uri, MECCG_PROP.alignment, Literal(alignment)))
        
        rarity = card.get('rarity', '')
        if rarity:
            self.graph.add((uri, MECCG_PROP.rarity, Literal(rarity)))
        
        artist = card.get('artist', '')
        if artist:
            self.graph.add((uri, DC.creator, Literal(artist)))
            self.graph.add((uri, SCHEMA.creator, Literal(artist)))
        
        image = card.get('image', '')
        if image:
            self.graph.add((uri, MECCG_PROP.cardImage, Literal(image)))
        
        attrs = card.get('attributes', {})
        if attrs:
            race = attrs.get('race', '')
            if race:
                self.graph.add((uri, MECCG_PROP.race, Literal(race)))
            
            skills = attrs.get('skills', '')
            if skills:
                self.graph.add((uri, MECCG_PROP.skills, Literal(skills)))
            
            for stat in ['prowess', 'body', 'mind', 'directInfluence', 'marshallingPoints']:
                value = attrs.get(stat, '')
                if value:
                    self.graph.add((uri, MECCG_PROP[stat], Literal(value)))
            
            home_site = attrs.get('homeSite', {})
            if isinstance(home_site, dict) and home_site.get('en'):
                self.graph.add((uri, MECCG_PROP.homeSite, Literal(home_site['en'])))
            elif isinstance(home_site, str) and home_site:
                self.graph.add((uri, MECCG_PROP.homeSite, Literal(home_site)))
        
        texts = card.get('text', {})
        for lang, text in texts.items():
            if text:
                clean_text = re.sub(r'<[^>]+>', '', text)
                self.graph.add((uri, MECCG_PROP.cardText, Literal(clean_text, lang=lang)))
        
        quotes = card.get('quote', {})
        for lang, quote_text in quotes.items():
            if quote_text:
                clean_quote = re.sub(r'<[^>]+>', '', quote_text)
                self.graph.add((uri, MECCG_PROP.quote, Literal(clean_quote, lang=lang)))
        
        return uri
    
    def add_cards(self, cards: List[Dict[str, Any]]) -> int:
        """Ajoute plusieurs cartes au graphe."""
        count = 0
        for card in cards:
            self.add_card(card)
            count += 1
        return count
    
    def serialize(self, format: str = "turtle") -> str:
        return self.graph.serialize(format=format)
    
    def save(self, filename: str, format: str = "turtle"):
        self.graph.serialize(destination=filename, format=format)
        print(f"Graphe MECCG sauvegarde dans {filename} ({len(self.graph)} triplets)")


class MECCGMatcher:
    """Match les cartes MECCG avec les entités du wiki Tolkien Gateway."""
    
    def __init__(self, card_parser: MECCGCardParser):
        self.parser = card_parser
        self.matches = []
        self.unmatched = []
    
    def match_with_wiki_entities(self, wiki_entities: Set[str]) -> List[Dict]:
        """Match les cartes avec les entités du wiki."""
        self.matches = []
        self.unmatched = []
        
        wiki_index = {name.lower(): name for name in wiki_entities}
        
        for card in self.parser.get_all_entity_cards():
            card_name = card.get('name', {}).get('en', '')
            if not card_name:
                continue
            
            normalized = self.parser.normalize_name(card_name)
            
            match = None
            
            if normalized.lower() in wiki_index:
                match = wiki_index[normalized.lower()]
            
            elif card_name.lower() in wiki_index:
                match = wiki_index[card_name.lower()]
            
            else:
                for wiki_name_lower, wiki_name in wiki_index.items():
                    if normalized.lower() in wiki_name_lower or wiki_name_lower in normalized.lower():
                        match = wiki_name
                        break
            
            if match:
                self.matches.append({
                    'card_id': card['id'],
                    'card_name': card_name,
                    'card_type': card['type'],
                    'wiki_name': match,
                    'alignment': card.get('alignment', ''),
                    'set': card.get('_set_id', '')
                })
            else:
                self.unmatched.append({
                    'card_id': card['id'],
                    'card_name': card_name,
                    'card_type': card['type'],
                    'alignment': card.get('alignment', ''),
                    'set': card.get('_set_id', '')
                })
        
        return self.matches
    
    def add_links_to_graph(self, rdf_gen: MECCGRDFGenerator, 
                           kg_graph: Graph = None) -> int:
        """Ajoute les liens entre cartes et entités wiki au graphe RDF."""
        count = 0
        
        for match in self.matches:
            card_uri = MECCG[quote(match['card_id'], safe="")]
            wiki_uri = TOLKIEN[quote(match['wiki_name'].replace(" ", "_"), safe="")]
            
            rdf_gen.graph.add((card_uri, TOLKIEN_PROP.depicts, wiki_uri))
            rdf_gen.graph.add((card_uri, SCHEMA.about, wiki_uri))
            
            if kg_graph is not None:
                kg_graph.add((wiki_uri, MECCG_PROP.hasCard, card_uri))
            
            if match['card_type'] == 'Character':
                rdf_gen.graph.add((card_uri, OWL.sameAs, wiki_uri))
            
            count += 1
        
        return count
    
    def get_match_statistics(self) -> Dict[str, Any]:
        stats = {
            'total_matches': len(self.matches),
            'total_unmatched': len(self.unmatched),
            'match_rate': len(self.matches) / (len(self.matches) + len(self.unmatched)) * 100 if (len(self.matches) + len(self.unmatched)) > 0 else 0,
            'by_type': {},
            'by_alignment': {}
        }
        
        for m in self.matches:
            t = m['card_type']
            stats['by_type'][t] = stats['by_type'].get(t, 0) + 1
            
            a = m['alignment']
            stats['by_alignment'][a] = stats['by_alignment'].get(a, 0) + 1
        
        return stats
    
    def print_matches(self, limit: int = 20):
        print(f"\nMATCHES TROUVES ({len(self.matches)} total)\n")
        
        for i, m in enumerate(self.matches[:limit], 1):
            print(f"{i:3}. {m['card_name']} ({m['card_type']})")
            print(f"     -> {m['wiki_name']}")
            print(f"     [Set: {m['set']}, {m['alignment']}]")
        
        if len(self.matches) > limit:
            print(f"\n... et {len(self.matches) - limit} autres matches")
    
    def print_unmatched(self, limit: int = 20):
        print(f"\nCARTES NON MATCHEES ({len(self.unmatched)} total)\n")
        
        for i, u in enumerate(self.unmatched[:limit], 1):
            print(f"{i:3}. {u['card_name']} ({u['card_type']}, {u['alignment']})")
        
        if len(self.unmatched) > limit:
            print(f"\n... et {len(self.unmatched) - limit} autres")


class LOTRCharacterCSVParser:
    """Parse le fichier CSV des personnages LOTR."""
    
    NAME_CORRECTIONS = {
        'Aragorn II Elessar': 'Aragorn',
        'Frodo Baggins': 'Frodo Baggins',
        'Samwise Gamgee': 'Samwise Gamgee',
        'Bilbo Baggins': 'Bilbo Baggins',
        'Gimli (Elf)': None,
        'Legolas (elf of Gondolin)': None,
    }
    
    RACE_NORMALIZATION = {
        'Hobbit': 'Hobbits',
        'Elf': 'Elves',
        'Dwarf': 'Dwarves',
        'Orc': 'Orcs',
        'Dragon': 'Dragons',
        'Eagle': 'Eagles',
        'Balrog': 'Balrogs',
        'Dwarven': 'Dwarves',
    }
    
    def __init__(self, csv_file: str):
        self.csv_file = csv_file
        self.characters = []
    
    def load(self):
        """Charge et parse le fichier CSV."""
        import csv
        
        with open(self.csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                char = {
                    'name': row.get('name', '').strip(),
                    'birth': self._clean_date(row.get('birth', '')),
                    'death': self._clean_date(row.get('death', '')),
                    'gender': self._clean_gender(row.get('gender', '')),
                    'hair': row.get('hair', '').strip(),
                    'height': row.get('height', '').strip(),
                    'race': self._normalize_race(row.get('race', '')),
                    'realm': row.get('realm', '').strip(),
                    'spouse': row.get('spouse', '').strip(),
                }
                
                if char['name'] and self.NAME_CORRECTIONS.get(char['name']) is not None:
                    self.characters.append(char)
                elif char['name'] and char['name'] not in self.NAME_CORRECTIONS:
                    self.characters.append(char)
        
        print(f"Charge {len(self.characters)} personnages du CSV")
        return self
    
    def _clean_date(self, date_str: str) -> str:
        if not date_str:
            return ''
        cleaned = date_str.strip()
        cleaned = re.sub(r'\s*,\s*', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned
    
    def _clean_gender(self, gender: str) -> str:
        gender = gender.strip().lower()
        if gender in ('male', 'males', 'most likely male'):
            return 'Male'
        elif gender == 'female':
            return 'Female'
        return ''
    
    def _normalize_race(self, race: str) -> str:
        race = race.strip()
        if ',' in race:
            race = race.split(',')[0].strip()
        return self.RACE_NORMALIZATION.get(race, race)
    
    def normalize_name(self, name: str) -> str:
        """Normalise un nom pour le matching."""
        if name in self.NAME_CORRECTIONS:
            corrected = self.NAME_CORRECTIONS[name]
            return corrected if corrected else name
        
        normalized = re.sub(r'\s+II\s+', ' ', name)
        normalized = re.sub(r'\s*\([^)]+\)\s*', '', normalized)
        normalized = normalized.strip()
        
        return normalized
    
    def get_statistics(self) -> Dict[str, Any]:
        stats = {
            'total': len(self.characters),
            'by_race': {},
            'by_gender': {},
            'by_realm': {},
            'with_birth': 0,
            'with_death': 0,
            'with_hair': 0,
            'with_height': 0,
            'with_spouse': 0,
        }
        
        for char in self.characters:
            race = char.get('race', 'Unknown') or 'Unknown'
            stats['by_race'][race] = stats['by_race'].get(race, 0) + 1
            
            gender = char.get('gender', 'Unknown') or 'Unknown'
            stats['by_gender'][gender] = stats['by_gender'].get(gender, 0) + 1
            
            realm = char.get('realm', '')
            if realm:
                first_realm = realm.split(',')[0].strip()
                stats['by_realm'][first_realm] = stats['by_realm'].get(first_realm, 0) + 1
            
            if char.get('birth'):
                stats['with_birth'] += 1
            if char.get('death'):
                stats['with_death'] += 1
            if char.get('hair'):
                stats['with_hair'] += 1
            if char.get('height'):
                stats['with_height'] += 1
            if char.get('spouse') and char['spouse'].lower() not in ('none', 'unnamed wife'):
                stats['with_spouse'] += 1
        
        return stats


class LOTRCSVMatcher:
    """Match les personnages du CSV avec les entités du wiki."""
    
    def __init__(self, csv_parser: LOTRCharacterCSVParser):
        self.parser = csv_parser
        self.matches = []
        self.unmatched = []
        self.enrichments = []
    
    def match_with_wiki_entities(self, wiki_entities: Set[str]) -> List[Dict]:
        """Match les personnages CSV avec les entités wiki."""
        self.matches = []
        self.unmatched = []
        
        wiki_index = {name.lower(): name for name in wiki_entities}
        
        for char in self.parser.characters:
            csv_name = char.get('name', '')
            if not csv_name:
                continue
            
            normalized = self.parser.normalize_name(csv_name)
            
            match = None
            
            if normalized.lower() in wiki_index:
                match = wiki_index[normalized.lower()]
            
            elif csv_name.lower() in wiki_index:
                match = wiki_index[csv_name.lower()]
            
            else:
                for wiki_lower, wiki_name in wiki_index.items():
                    if len(normalized) > 3:
                        if normalized.lower() in wiki_lower:
                            match = wiki_name
                            break
            
            if match:
                self.matches.append({
                    'csv_name': csv_name,
                    'wiki_name': match,
                    'data': char
                })
            else:
                self.unmatched.append(char)
        
        return self.matches
    
    def enrich_kg(self, kg_graph: Graph) -> int:
        """Enrichit le KG avec les données du CSV."""
        count = 0
        
        for match in self.matches:
            wiki_name = match['wiki_name']
            data = match['data']
            
            wiki_uri = TOLKIEN[quote(wiki_name.replace(" ", "_"), safe="")]
            
            if data.get('hair') and data['hair'].lower() not in ('various', 'uncertain'):
                hair = data['hair'].split('(')[0].strip()
                if hair:
                    kg_graph.add((wiki_uri, TOLKIEN_PROP.hairColor, Literal(hair)))
                    count += 1
            
            if data.get('height'):
                height = data['height']
                if height.lower() not in ('various', 'tall'):
                    kg_graph.add((wiki_uri, SCHEMA.height, Literal(height)))
                    count += 1
                elif height.lower() == 'tall':
                    kg_graph.add((wiki_uri, TOLKIEN_PROP.heightDescription, Literal("Tall")))
                    count += 1
            
            if data.get('realm'):
                realms = [r.strip() for r in data['realm'].split(',')]
                for realm in realms:
                    if realm:
                        realm_uri = TOLKIEN[quote(realm.replace(" ", "_"), safe="")]
                        kg_graph.add((wiki_uri, TOLKIEN_PROP.realm, realm_uri))
                        kg_graph.add((wiki_uri, SCHEMA.nationality, Literal(realm)))
                        count += 1
            
            spouse = data.get('spouse', '')
            if spouse and spouse.lower() not in ('none', 'unnamed wife', 'unnamed husband', ''):
                spouse_clean = re.sub(r'\s*then\s*,.*', '', spouse)
                spouse_clean = re.sub(r'^Loved\s*,.*', '', spouse_clean)
                spouse_clean = spouse_clean.strip()
                if spouse_clean and 'unnamed' not in spouse_clean.lower():
                    spouse_uri = TOLKIEN[quote(spouse_clean.replace(" ", "_"), safe="")]
                    kg_graph.add((wiki_uri, SCHEMA.spouse, spouse_uri))
                    count += 1
            
            if data.get('race'):
                race = data['race']
                race_uri = TOLKIEN[quote(race.replace(" ", "_"), safe="")]
                kg_graph.add((wiki_uri, TOLKIEN_PROP.race, race_uri))
                count += 1
            
            self.enrichments.append({
                'entity': wiki_name,
                'added': {
                    'hair': data.get('hair'),
                    'height': data.get('height'),
                    'realm': data.get('realm'),
                    'spouse': data.get('spouse'),
                    'race': data.get('race'),
                }
            })
        
        return count
    
    def get_match_statistics(self) -> Dict[str, Any]:
        total = len(self.matches) + len(self.unmatched)
        return {
            'total_csv': total,
            'matched': len(self.matches),
            'unmatched': len(self.unmatched),
            'match_rate': len(self.matches) / total * 100 if total > 0 else 0,
            'enrichments': len(self.enrichments)
        }
    
    def print_matches(self, limit: int = 20):
        print(f"\nMATCHES CSV <-> WIKI ({len(self.matches)} total)\n")
        
        for i, m in enumerate(self.matches[:limit], 1):
            csv_name = m['csv_name']
            wiki_name = m['wiki_name']
            data = m['data']
            
            extras = []
            if data.get('race'):
                extras.append(f"race={data['race']}")
            if data.get('realm'):
                extras.append(f"realm={data['realm'][:20]}")
            if data.get('hair'):
                extras.append(f"hair={data['hair'][:15]}")
            
            extras_str = ", ".join(extras) if extras else "no extra data"
            
            print(f"{i:3}. {csv_name}")
            if csv_name != wiki_name:
                print(f"     -> {wiki_name}")
            print(f"     [{extras_str}]")
        
        if len(self.matches) > limit:
            print(f"\n... et {len(self.matches) - limit} autres matches")


def integrate_lotr_csv(csv_file: str, wiki_entities: Set[str], 
                       kg_graph: Graph = None) -> Tuple[LOTRCSVMatcher, Dict]:
    """Intègre les données du CSV LOTR dans le KG."""
    parser = LOTRCharacterCSVParser(csv_file)
    parser.load()
    
    stats = parser.get_statistics()
    print(f"\nStatistiques CSV:")
    print(f"Total: {stats['total']} personnages")
    print(f"Avec naissance: {stats['with_birth']}")
    print(f"Avec deces: {stats['with_death']}")
    print(f"Avec cheveux: {stats['with_hair']}")
    print(f"Avec taille: {stats['with_height']}")
    print(f"Avec conjoint: {stats['with_spouse']}")
    
    matcher = LOTRCSVMatcher(parser)
    matcher.match_with_wiki_entities(wiki_entities)
    
    match_stats = matcher.get_match_statistics()
    print(f"\nMatching:")
    print(f"Matches: {match_stats['matched']}")
    print(f"Non matches: {match_stats['unmatched']}")
    print(f"Taux: {match_stats['match_rate']:.1f}%")
    
    if kg_graph is not None:
        print(f"\nEnrichissement du KG...")
        triplets = matcher.enrich_kg(kg_graph)
        print(f"{triplets} triplets ajoutes")
    
    return matcher, {
        'csv_stats': stats,
        'match_stats': match_stats
    }


def integrate_meccg_cards(json_file: str, wiki_entities: Set[str], 
                          output_file: str = "meccg_cards.ttl") -> Tuple[Graph, Dict]:
    """Intègre les cartes MECCG dans le KG."""
    parser = MECCGCardParser(json_file)
    parser.load()
    
    stats = parser.get_statistics()
    print(f"\nStatistiques des cartes:")
    print(f"Total: {stats['total_cards']} cartes")
    print(f"Sets: {stats['sets']}")
    print(f"Types: {stats['by_type']}")
    print(f"Langues: {stats['languages']}")
    
    rdf_gen = MECCGRDFGenerator()
    rdf_gen.add_cards(parser.cards)
    
    matcher = MECCGMatcher(parser)
    matcher.match_with_wiki_entities(wiki_entities)
    
    matcher.print_matches()
    match_stats = matcher.get_match_statistics()
    print(f"\nTaux de match: {match_stats['match_rate']:.1f}%")
    print(f"Matches: {match_stats['total_matches']}")
    print(f"Non matches: {match_stats['total_unmatched']}")
    
    links = matcher.add_links_to_graph(rdf_gen)
    print(f"\nLiens crees: {links}")
    
    rdf_gen.save(output_file)
    
    return rdf_gen.graph, {
        'card_stats': stats,
        'match_stats': match_stats,
        'links_created': links
    }