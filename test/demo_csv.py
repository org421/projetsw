#!/usr/bin/env python3
"""
Démo Étape 10: Intégration du dataset CSV
(Version autonome sans API wiki)
"""

import csv
import re
from typing import Dict, List, Any, Set
from urllib.parse import quote
from rdflib import Graph, Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, XSD, OWL, FOAF


# Namespaces
TOLKIEN = Namespace("https://tolkiengateway.net/wiki/")
TOLKIEN_PROP = Namespace("https://tolkiengateway.net/wiki/Property:")
TOLKIEN_CLASS = Namespace("https://tolkiengateway.net/wiki/Class:")
SCHEMA = Namespace("http://schema.org/")


def print_separator(title: str):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70 + "\n")


class LOTRCharacterCSVParser:
    """Parser pour le fichier CSV des personnages LOTR."""
    
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
                if char['name']:
                    self.characters.append(char)
        
        print(f"✓ Chargé {len(self.characters)} personnages")
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
            race = char.get('race', '') or 'Unknown'
            stats['by_race'][race] = stats['by_race'].get(race, 0) + 1
            
            gender = char.get('gender', '') or 'Unknown'
            stats['by_gender'][gender] = stats['by_gender'].get(gender, 0) + 1
            
            realm = char.get('realm', '')
            if realm:
                first_realm = realm.split(',')[0].strip()
                stats['by_realm'][first_realm] = stats['by_realm'].get(first_realm, 0) + 1
            
            if char.get('birth'): stats['with_birth'] += 1
            if char.get('death'): stats['with_death'] += 1
            if char.get('hair'): stats['with_hair'] += 1
            if char.get('height'): stats['with_height'] += 1
            if char.get('spouse') and char['spouse'].lower() not in ('none', 'unnamed wife', ''):
                stats['with_spouse'] += 1
        
        return stats


class LOTRCSVRDFGenerator:
    """Génère le RDF à partir du CSV."""
    
    def __init__(self):
        self.graph = Graph()
        self._bind_namespaces()
    
    def _bind_namespaces(self):
        self.graph.bind("tolkien", TOLKIEN)
        self.graph.bind("tolkien_prop", TOLKIEN_PROP)
        self.graph.bind("tolkien_class", TOLKIEN_CLASS)
        self.graph.bind("schema", SCHEMA)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("owl", OWL)
        self.graph.bind("foaf", FOAF)
        self.graph.bind("xsd", XSD)
    
    def add_character(self, char: Dict[str, Any]) -> URIRef:
        """Ajoute un personnage au graphe."""
        name = char.get('name', '')
        if not name:
            return None
        
        uri = TOLKIEN[quote(name.replace(" ", "_"), safe="")]
        
        # Types
        self.graph.add((uri, RDF.type, TOLKIEN_CLASS.Character))
        self.graph.add((uri, RDF.type, SCHEMA.Person))
        
        # Nom
        self.graph.add((uri, SCHEMA.name, Literal(name)))
        self.graph.add((uri, RDFS.label, Literal(name)))
        
        # Genre
        if char.get('gender'):
            self.graph.add((uri, SCHEMA.gender, Literal(char['gender'])))
        
        # Race
        if char.get('race'):
            race_uri = TOLKIEN[quote(char['race'].replace(" ", "_"), safe="")]
            self.graph.add((uri, TOLKIEN_PROP.people, race_uri))
            self.graph.add((uri, TOLKIEN_PROP.race, Literal(char['race'])))
        
        # Naissance
        if char.get('birth'):
            self.graph.add((uri, SCHEMA.birthDate, Literal(char['birth'])))
        
        # Décès
        if char.get('death'):
            self.graph.add((uri, SCHEMA.deathDate, Literal(char['death'])))
        
        # Cheveux
        if char.get('hair') and char['hair'].lower() not in ('various', 'uncertain'):
            hair = char['hair'].split('(')[0].strip()
            if hair:
                self.graph.add((uri, TOLKIEN_PROP.hairColor, Literal(hair)))
        
        # Taille
        if char.get('height'):
            height = char['height']
            if height.lower() == 'tall':
                self.graph.add((uri, TOLKIEN_PROP.heightDescription, Literal("Tall")))
            elif height.lower() not in ('various',):
                self.graph.add((uri, SCHEMA.height, Literal(height)))
        
        # Royaume
        if char.get('realm'):
            realms = [r.strip() for r in char['realm'].split(',')]
            for realm in realms:
                if realm:
                    realm_uri = TOLKIEN[quote(realm.replace(" ", "_"), safe="")]
                    self.graph.add((uri, TOLKIEN_PROP.realm, realm_uri))
                    self.graph.add((uri, SCHEMA.nationality, Literal(realm)))
        
        # Conjoint
        spouse = char.get('spouse', '')
        if spouse and spouse.lower() not in ('none', 'unnamed wife', 'unnamed husband', ''):
            spouse_clean = re.sub(r'\s*then\s*,.*', '', spouse)
            spouse_clean = re.sub(r'^Loved\s*,.*', '', spouse_clean)
            spouse_clean = spouse_clean.strip()
            if spouse_clean and 'unnamed' not in spouse_clean.lower():
                spouse_uri = TOLKIEN[quote(spouse_clean.replace(" ", "_"), safe="")]
                self.graph.add((uri, SCHEMA.spouse, spouse_uri))
        
        return uri
    
    def add_all_characters(self, characters: List[Dict]) -> int:
        count = 0
        for char in characters:
            if self.add_character(char):
                count += 1
        return count
    
    def save(self, filename: str, format: str = "turtle"):
        self.graph.serialize(destination=filename, format=format)
        print(f"✓ Sauvegardé: {filename} ({len(self.graph)} triplets)")


def show_sample_characters(characters: List[Dict], limit: int = 10):
    """Affiche un échantillon de personnages."""
    print(f"\n📋 Échantillon de personnages ({limit} sur {len(characters)}):\n")
    
    # Sélectionner des personnages intéressants (avec beaucoup de données)
    interesting = sorted(characters, key=lambda c: sum([
        1 if c.get('birth') else 0,
        1 if c.get('death') else 0,
        1 if c.get('hair') else 0,
        1 if c.get('height') else 0,
        1 if c.get('spouse') and c['spouse'].lower() not in ('none', 'unnamed wife') else 0,
        1 if c.get('realm') else 0,
    ]), reverse=True)[:limit]
    
    for i, char in enumerate(interesting, 1):
        print(f"{i:2}. {char['name']}")
        details = []
        if char.get('race'):
            details.append(f"Race: {char['race']}")
        if char.get('gender'):
            details.append(f"Genre: {char['gender']}")
        if char.get('birth'):
            details.append(f"Né: {char['birth'][:30]}")
        if char.get('hair'):
            details.append(f"Cheveux: {char['hair'][:20]}")
        if char.get('height'):
            details.append(f"Taille: {char['height'][:20]}")
        if char.get('realm'):
            details.append(f"Royaume: {char['realm'][:25]}")
        if char.get('spouse') and char['spouse'].lower() not in ('none', 'unnamed wife'):
            details.append(f"Conjoint: {char['spouse'][:20]}")
        
        for d in details:
            print(f"    {d}")
        print()


def show_turtle_sample(graph: Graph, limit: int = 3000):
    """Affiche un aperçu du Turtle."""
    turtle = graph.serialize(format="turtle")
    print(turtle[:limit])
    if len(turtle) > limit:
        print(f"\n... ({len(turtle)} caractères au total)")


def main():
    print("\n" + "#" * 70)
    print("#" + " " * 68 + "#")
    print("#     TOLKIEN KNOWLEDGE GRAPH - Étape 10                              #")
    print("#     Intégration du dataset CSV des personnages LOTR                 #")
    print("#" + " " * 68 + "#")
    print("#" * 70)
    
    CSV_FILE = "/mnt/user-data/uploads/lotr_characters.csv"
    
    # 1. Parser le CSV
    print_separator("1. PARSING DU FICHIER CSV")
    parser = LOTRCharacterCSVParser(CSV_FILE)
    parser.load()
    
    # 2. Statistiques
    print_separator("2. STATISTIQUES DU DATASET")
    stats = parser.get_statistics()
    
    print(f"📊 Vue d'ensemble:")
    print(f"   Total personnages: {stats['total']}")
    
    print(f"\n👤 Par race (top 10):")
    for race, count in sorted(stats['by_race'].items(), key=lambda x: -x[1])[:10]:
        pct = count * 100 // stats['total']
        bar = "█" * (pct // 2)
        print(f"   {race:15} {count:4} ({pct:2}%) {bar}")
    
    print(f"\n⚥ Par genre:")
    for gender, count in sorted(stats['by_gender'].items(), key=lambda x: -x[1]):
        pct = count * 100 // stats['total']
        print(f"   {gender:15} {count:4} ({pct}%)")
    
    print(f"\n🏰 Par royaume (top 10):")
    for realm, count in sorted(stats['by_realm'].items(), key=lambda x: -x[1])[:10]:
        print(f"   {realm:20} {count:3}")
    
    print(f"\n📋 Complétude des données:")
    total = stats['total']
    print(f"   Avec date naissance:  {stats['with_birth']:4} ({stats['with_birth']*100//total}%)")
    print(f"   Avec date décès:      {stats['with_death']:4} ({stats['with_death']*100//total}%)")
    print(f"   Avec couleur cheveux: {stats['with_hair']:4} ({stats['with_hair']*100//total}%)")
    print(f"   Avec taille:          {stats['with_height']:4} ({stats['with_height']*100//total}%)")
    print(f"   Avec conjoint nommé:  {stats['with_spouse']:4} ({stats['with_spouse']*100//total}%)")
    
    # 3. Échantillon de personnages
    print_separator("3. ÉCHANTILLON DE PERSONNAGES")
    show_sample_characters(parser.characters, limit=10)
    
    # 4. Génération RDF
    print_separator("4. GÉNÉRATION RDF")
    rdf_gen = LOTRCSVRDFGenerator()
    count = rdf_gen.add_all_characters(parser.characters)
    print(f"   Personnages convertis: {count}")
    print(f"   Triplets générés: {len(rdf_gen.graph)}")
    
    # 5. Aperçu du Turtle
    print_separator("5. APERÇU DU TURTLE")
    show_turtle_sample(rdf_gen.graph, limit=3500)
    
    # 6. Statistiques RDF
    print_separator("6. STATISTIQUES RDF")
    
    predicates = {}
    for s, p, o in rdf_gen.graph:
        pred = str(p).split('/')[-1].split('#')[-1]
        predicates[pred] = predicates.get(pred, 0) + 1
    
    print(f"   Par prédicat:")
    for pred, count in sorted(predicates.items(), key=lambda x: -x[1]):
        print(f"     {pred}: {count}")
    
    # 7. Sauvegarde
    print_separator("7. SAUVEGARDE")
    rdf_gen.save("lotr_characters.ttl", format="turtle")
    rdf_gen.graph.serialize(destination="lotr_characters.nt", format="nt")
    print(f"✓ Sauvegardé: lotr_characters.nt")
    
    # 8. Exemples de personnages en Turtle
    print_separator("8. EXEMPLES DÉTAILLÉS")
    
    known_names = ['Gandalf', 'Elrond', 'Galadriel', 'Aragorn II Elessar', 'Frodo Baggins']
    
    for name in known_names:
        uri = TOLKIEN[quote(name.replace(" ", "_"), safe="")]
        triples = list(rdf_gen.graph.triples((uri, None, None)))
        if triples:
            print(f"\n📖 {name}:")
            for s, p, o in triples:
                pred = str(p).split('/')[-1].split('#')[-1]
                obj = str(o)
                if len(obj) > 50:
                    obj = obj[:50] + "..."
                print(f"   {pred}: {obj}")
    
    # 9. Résumé
    print_separator("RÉSUMÉ")
    print(f"✅ Étape 10 complétée!")
    print(f"\n📁 Fichiers générés:")
    print(f"   • lotr_characters.ttl - Format Turtle ({len(rdf_gen.graph)} triplets)")
    print(f"   • lotr_characters.nt  - Format N-Triples")
    
    print(f"\n📊 Données intégrées:")
    print(f"   • {stats['total']} personnages")
    print(f"   • {len(stats['by_race'])} races différentes")
    print(f"   • {len(stats['by_realm'])} royaumes différents")
    
    print(f"\n🔗 Propriétés ajoutées:")
    print(f"   • schema:name, rdfs:label (noms)")
    print(f"   • schema:gender (genre)")
    print(f"   • tolkien_prop:race, tolkien_prop:people (race)")
    print(f"   • schema:birthDate, schema:deathDate (dates)")
    print(f"   • tolkien_prop:hairColor (cheveux)")
    print(f"   • schema:height (taille)")
    print(f"   • tolkien_prop:realm, schema:nationality (royaume)")
    print(f"   • schema:spouse (conjoint)")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
