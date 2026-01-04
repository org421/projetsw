"""
Générateur RDF pour le Knowledge Graph Tolkien
Convertit les données parsées en triplets RDF
"""

from rdflib import Graph, Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, XSD, OWL, FOAF, DC, DCTERMS
from typing import Dict, List, Any, Optional
from urllib.parse import quote
import re


# Namespaces personnalisés
TOLKIEN = Namespace("https://tolkiengateway.net/wiki/")
TOLKIEN_PROP = Namespace("https://tolkiengateway.net/wiki/Property:")
TOLKIEN_CLASS = Namespace("https://tolkiengateway.net/wiki/Class:")
SCHEMA = Namespace("http://schema.org/")
DBPEDIA = Namespace("http://dbpedia.org/resource/")
DBPEDIA_ONT = Namespace("http://dbpedia.org/ontology/")


class RDFGenerator:
    """
    Générateur de triplets RDF à partir des données parsées du wiki.
    Utilise schema.org comme vocabulaire principal.
    """
    
    def __init__(self):
        self.graph = Graph()
        self._bind_namespaces()
        
    def _bind_namespaces(self):
        """Lie les préfixes aux namespaces."""
        self.graph.bind("tolkien", TOLKIEN)
        self.graph.bind("tolkien_prop", TOLKIEN_PROP)
        self.graph.bind("tolkien_class", TOLKIEN_CLASS)
        self.graph.bind("schema", SCHEMA)
        self.graph.bind("dbpedia", DBPEDIA)
        self.graph.bind("dbo", DBPEDIA_ONT)
        self.graph.bind("foaf", FOAF)
        self.graph.bind("dc", DC)
        self.graph.bind("dcterms", DCTERMS)
        self.graph.bind("owl", OWL)
    
    def _make_uri(self, name: str) -> URIRef:
        """
        Crée une URI à partir d'un nom.
        
        Args:
            name: Nom de l'entité
            
        Returns:
            URI de l'entité
        """
        # Nettoyer le nom pour l'URI
        clean_name = name.strip()
        # Encoder les caractères spéciaux mais garder les espaces comme underscores
        encoded = quote(clean_name.replace(" ", "_"), safe="")
        return TOLKIEN[encoded]
    
    def _make_property_uri(self, prop_name: str) -> URIRef:
        """Crée une URI pour une propriété."""
        clean_name = prop_name.strip().lower().replace(" ", "_")
        return TOLKIEN_PROP[clean_name]
    
    def _add_literal(self, subject: URIRef, predicate: URIRef, value: Any, 
                     datatype: Optional[URIRef] = None, lang: Optional[str] = None):
        """
        Ajoute un triplet avec un littéral.
        
        Args:
            subject: Sujet du triplet
            predicate: Prédicat du triplet
            value: Valeur littérale
            datatype: Type de données XSD optionnel
            lang: Tag de langue optionnel
        """
        if value is None or value == "":
            return
            
        if lang:
            self.graph.add((subject, predicate, Literal(str(value), lang=lang)))
        elif datatype:
            self.graph.add((subject, predicate, Literal(value, datatype=datatype)))
        else:
            self.graph.add((subject, predicate, Literal(str(value))))
    
    def _add_link(self, subject: URIRef, predicate: URIRef, target_name: str):
        """
        Ajoute un triplet avec un lien vers une autre entité.
        
        Args:
            subject: Sujet du triplet
            predicate: Prédicat du triplet
            target_name: Nom de l'entité cible
        """
        if target_name and target_name.strip():
            target_uri = self._make_uri(target_name)
            self.graph.add((subject, predicate, target_uri))
    
    def add_character(self, character_data: Dict[str, Any]) -> URIRef:
        """
        Ajoute un personnage au graphe RDF.
        
        Args:
            character_data: Dictionnaire avec les données du personnage
            
        Returns:
            URI du personnage créé
        """
        name = character_data.get('name', 'Unknown')
        uri = self._make_uri(name)
        
        # Type
        self.graph.add((uri, RDF.type, SCHEMA.Person))
        self.graph.add((uri, RDF.type, TOLKIEN_CLASS.Character))
        
        # Nom et label
        self._add_literal(uri, SCHEMA.name, name)
        self._add_literal(uri, RDFS.label, name, lang="en")
        
        # Lien vers la page wiki
        wiki_page = URIRef(f"https://tolkiengateway.net/wiki/{quote(name.replace(' ', '_'))}")
        self.graph.add((uri, FOAF.isPrimaryTopicOf, wiki_page))
        self.graph.add((uri, SCHEMA.mainEntityOfPage, wiki_page))
        
        # People/Race
        if 'people' in character_data:
            people = character_data['people']
            if isinstance(people, str):
                self._add_link(uri, TOLKIEN_PROP.people, people)
                self._add_literal(uri, SCHEMA.memberOf, people)
        
        # Image
        if 'image' in character_data:
            image_name = character_data['image']
            image_url = f"https://tolkiengateway.net/wiki/File:{quote(image_name)}"
            self.graph.add((uri, SCHEMA.image, URIRef(image_url)))
            self.graph.add((uri, FOAF.depiction, URIRef(image_url)))
        
        # Description/Caption
        if 'caption' in character_data:
            self._add_literal(uri, SCHEMA.description, character_data['caption'])
        
        # Autres noms
        if 'othernames' in character_data:
            othernames = character_data['othernames']
            if isinstance(othernames, list):
                for othername in othernames:
                    self._add_literal(uri, SCHEMA.alternateName, othername)
            else:
                self._add_literal(uri, SCHEMA.alternateName, othernames)
        
        # Titres
        if 'titles' in character_data:
            titles = character_data['titles']
            if isinstance(titles, list):
                for title in titles:
                    self._add_literal(uri, SCHEMA.jobTitle, title)
            else:
                self._add_literal(uri, SCHEMA.jobTitle, titles)
        
        # Position
        if 'position' in character_data:
            self._add_literal(uri, SCHEMA.jobTitle, character_data['position'])
        
        # Lieux
        if 'location' in character_data:
            locations = character_data['location']
            if isinstance(locations, list):
                for loc in locations:
                    self._add_link(uri, SCHEMA.homeLocation, loc)
            else:
                self._add_link(uri, SCHEMA.homeLocation, locations)
        
        # Naissance
        if 'birth' in character_data:
            birth_data = character_data['birth']
            if isinstance(birth_data, dict):
                if birth_data.get('dates'):
                    date_info = birth_data['dates'][0]
                    # Créer un noeud pour la date structurée
                    birth_node = BNode()
                    self.graph.add((uri, SCHEMA.birthDate, birth_node))
                    self._add_literal(birth_node, TOLKIEN_PROP.age, date_info['age'])
                    self._add_literal(birth_node, TOLKIEN_PROP.ageName, date_info['age_name'])
                    self._add_literal(birth_node, TOLKIEN_PROP.year, date_info['year'], XSD.integer)
                    self._add_literal(birth_node, RDFS.label, birth_data.get('text', ''))
                elif birth_data.get('text'):
                    self._add_literal(uri, SCHEMA.birthDate, birth_data['text'])
            else:
                self._add_literal(uri, SCHEMA.birthDate, birth_data)
        
        # Lieu de naissance
        if 'birthlocation' in character_data:
            self._add_link(uri, SCHEMA.birthPlace, character_data['birthlocation'])
        
        # Décès
        if 'death' in character_data:
            death_data = character_data['death']
            if isinstance(death_data, dict):
                if death_data.get('dates'):
                    date_info = death_data['dates'][0]
                    death_node = BNode()
                    self.graph.add((uri, SCHEMA.deathDate, death_node))
                    self._add_literal(death_node, TOLKIEN_PROP.age, date_info['age'])
                    self._add_literal(death_node, TOLKIEN_PROP.ageName, date_info['age_name'])
                    self._add_literal(death_node, TOLKIEN_PROP.year, date_info['year'], XSD.integer)
                    self._add_literal(death_node, RDFS.label, death_data.get('text', ''))
                elif death_data.get('text'):
                    self._add_literal(uri, SCHEMA.deathDate, death_data['text'])
            else:
                self._add_literal(uri, SCHEMA.deathDate, death_data)
        
        # Lieu de décès
        if 'deathlocation' in character_data:
            self._add_link(uri, SCHEMA.deathPlace, character_data['deathlocation'])
        
        # Âge
        if 'age' in character_data:
            age = character_data['age']
            if isinstance(age, int):
                self._add_literal(uri, TOLKIEN_PROP.age, age, XSD.integer)
            else:
                self._add_literal(uri, TOLKIEN_PROP.age, age)
        
        # Genre
        if 'gender' in character_data:
            gender = character_data['gender']
            self._add_literal(uri, SCHEMA.gender, gender)
            if gender.lower() == 'male':
                self.graph.add((uri, FOAF.gender, Literal("male")))
            elif gender.lower() == 'female':
                self.graph.add((uri, FOAF.gender, Literal("female")))
        
        # Famille - Parenté
        if 'parentage' in character_data:
            parents = character_data['parentage']
            if isinstance(parents, list):
                for parent in parents:
                    self._add_link(uri, SCHEMA.parent, parent)
                    self._add_link(uri, TOLKIEN_PROP.parentage, parent)
            else:
                self._add_link(uri, SCHEMA.parent, parents)
        
        # Famille - Fratrie
        if 'siblings' in character_data:
            siblings = character_data['siblings']
            if isinstance(siblings, list):
                for sibling in siblings:
                    self._add_link(uri, SCHEMA.sibling, sibling)
            else:
                self._add_link(uri, SCHEMA.sibling, siblings)
        
        # Famille - Conjoint
        if 'spouse' in character_data:
            spouses = character_data['spouse']
            if isinstance(spouses, list):
                for spouse in spouses:
                    if spouse.lower() not in ['never married', 'none', 'unknown']:
                        self._add_link(uri, SCHEMA.spouse, spouse)
            else:
                if spouses.lower() not in ['never married', 'none', 'unknown']:
                    self._add_link(uri, SCHEMA.spouse, spouses)
        
        # Famille - Enfants
        if 'children' in character_data:
            children = character_data['children']
            if isinstance(children, list):
                for child in children:
                    if child.lower() not in ['none', 'unknown']:
                        self._add_link(uri, SCHEMA.children, child)
            else:
                if children.lower() not in ['none', 'unknown']:
                    self._add_link(uri, SCHEMA.children, children)
        
        # Maison/Famille noble
        if 'house' in character_data:
            self._add_link(uri, TOLKIEN_PROP.house, character_data['house'])
            self._add_literal(uri, SCHEMA.familyName, character_data['house'])
        
        # Affiliation
        if 'affiliation' in character_data:
            affiliations = character_data['affiliation']
            if isinstance(affiliations, list):
                for aff in affiliations:
                    self._add_link(uri, SCHEMA.memberOf, aff)
                    self._add_link(uri, TOLKIEN_PROP.affiliation, aff)
            else:
                self._add_link(uri, SCHEMA.memberOf, affiliations)
        
        # Langues
        if 'language' in character_data:
            languages = character_data['language']
            if isinstance(languages, list):
                for lang in languages:
                    self._add_literal(uri, SCHEMA.knowsLanguage, lang)
            else:
                self._add_literal(uri, SCHEMA.knowsLanguage, languages)
        
        # Notable pour
        if 'notablefor' in character_data:
            self._add_literal(uri, TOLKIEN_PROP.notableFor, character_data['notablefor'])
        
        # Armes
        if 'weapons' in character_data:
            weapons = character_data['weapons']
            if isinstance(weapons, list):
                for weapon in weapons:
                    self._add_link(uri, TOLKIEN_PROP.weapon, weapon)
            else:
                self._add_link(uri, TOLKIEN_PROP.weapon, weapons)
        
        # Monture
        if 'steed' in character_data:
            self._add_link(uri, TOLKIEN_PROP.steed, character_data['steed'])
        
        return uri
    
    def add_location(self, location_data: Dict[str, Any]) -> URIRef:
        """
        Ajoute un lieu au graphe RDF.
        
        Args:
            location_data: Dictionnaire avec les données du lieu
            
        Returns:
            URI du lieu créé
        """
        name = location_data.get('name', 'Unknown')
        uri = self._make_uri(name)
        
        # Type
        self.graph.add((uri, RDF.type, SCHEMA.Place))
        self.graph.add((uri, RDF.type, TOLKIEN_CLASS.Location))
        
        template = location_data.get('_template', '').lower()
        if 'kingdom' in template:
            self.graph.add((uri, RDF.type, TOLKIEN_CLASS.Kingdom))
            self.graph.add((uri, RDF.type, SCHEMA.Country))
        
        # Nom et label
        self._add_literal(uri, SCHEMA.name, name)
        self._add_literal(uri, RDFS.label, name, lang="en")
        
        # Lien vers la page wiki
        wiki_page = URIRef(f"https://tolkiengateway.net/wiki/{quote(name.replace(' ', '_'))}")
        self.graph.add((uri, FOAF.isPrimaryTopicOf, wiki_page))
        self.graph.add((uri, SCHEMA.mainEntityOfPage, wiki_page))
        
        # Image
        if 'image' in location_data:
            image_name = location_data['image']
            image_url = f"https://tolkiengateway.net/wiki/File:{quote(image_name)}"
            self.graph.add((uri, SCHEMA.image, URIRef(image_url)))
        
        # Description/Caption
        if 'caption' in location_data:
            self._add_literal(uri, SCHEMA.description, location_data['caption'])
        
        # Autres noms
        if 'othernames' in location_data:
            othernames = location_data['othernames']
            if isinstance(othernames, list):
                for othername in othernames:
                    self._add_literal(uri, SCHEMA.alternateName, othername)
            else:
                self._add_literal(uri, SCHEMA.alternateName, othernames)
        
        # Localisation (contenu dans)
        if 'location' in location_data:
            locations = location_data['location']
            if isinstance(locations, list):
                for loc in locations:
                    self._add_link(uri, SCHEMA.containedInPlace, loc)
            else:
                self._add_link(uri, SCHEMA.containedInPlace, locations)
        
        # Capitale
        if 'capital' in location_data:
            self._add_link(uri, TOLKIEN_PROP.capital, location_data['capital'])
        
        # Régions
        if 'regions' in location_data:
            regions = location_data['regions']
            if isinstance(regions, list):
                for region in regions:
                    self._add_link(uri, SCHEMA.containsPlace, region)
            else:
                self._add_link(uri, SCHEMA.containsPlace, regions)
        
        # Population
        if 'population' in location_data:
            self._add_literal(uri, TOLKIEN_PROP.inhabitants, location_data['population'])
        
        # Langue
        if 'language' in location_data:
            self._add_literal(uri, TOLKIEN_PROP.language, location_data['language'])
        
        # Gouvernement
        if 'govern1' in location_data:
            self._add_literal(uri, TOLKIEN_PROP.governance, location_data['govern1'])
        
        return uri
    
    def add_entity(self, entity_data: Dict[str, Any]) -> URIRef:
        """
        Ajoute une entité générique au graphe RDF.
        Détecte automatiquement le type et applique le mapping approprié.
        
        Args:
            entity_data: Dictionnaire avec les données de l'entité (_type requis)
            
        Returns:
            URI de l'entité créée
        """
        entity_type = entity_data.get('_type', 'Thing')
        
        # Router vers les méthodes spécialisées si disponibles
        if entity_type == 'Character':
            return self.add_character(entity_data)
        elif entity_type in ('Location', 'Kingdom', 'Mountain'):
            return self.add_location(entity_data)
        
        # Sinon, traitement générique
        name = entity_data.get('name', 'Unknown')
        uri = self._make_uri(name)
        
        # Mapping des types vers schema.org
        TYPE_MAPPING = {
            'Book': (SCHEMA.Book, TOLKIEN_CLASS.Book),
            'Chapter': (SCHEMA.Chapter, TOLKIEN_CLASS.Chapter),
            'Film': (SCHEMA.Movie, TOLKIEN_CLASS.Film),
            'VideoGame': (SCHEMA.VideoGame, TOLKIEN_CLASS.VideoGame),
            'Actor': (SCHEMA.Person, TOLKIEN_CLASS.Actor),
            'Director': (SCHEMA.Person, TOLKIEN_CLASS.Director),
            'Author': (SCHEMA.Person, TOLKIEN_CLASS.Author),
            'Artist': (SCHEMA.Person, TOLKIEN_CLASS.Artist),
            'Battle': (SCHEMA.Event, TOLKIEN_CLASS.Battle),
            'War': (SCHEMA.Event, TOLKIEN_CLASS.War),
            'Song': (SCHEMA.MusicComposition, TOLKIEN_CLASS.Song),
            'Poem': (SCHEMA.CreativeWork, TOLKIEN_CLASS.Poem),
            'Letter': (SCHEMA.Message, TOLKIEN_CLASS.Letter),
            'Object': (SCHEMA.Thing, TOLKIEN_CLASS.Object),
            'Weapon': (SCHEMA.Thing, TOLKIEN_CLASS.Weapon),
            'Race': (SCHEMA.Thing, TOLKIEN_CLASS.Race),
            'Organization': (SCHEMA.Organization, TOLKIEN_CLASS.Organization),
            'NobleHouse': (SCHEMA.Organization, TOLKIEN_CLASS.NobleHouse),
            'Plant': (SCHEMA.Thing, TOLKIEN_CLASS.Plant),
            'Episode': (SCHEMA.Episode, TOLKIEN_CLASS.Episode),
            'Album': (SCHEMA.MusicAlbum, TOLKIEN_CLASS.Album),
            'Band': (SCHEMA.MusicGroup, TOLKIEN_CLASS.Band),
            'Convention': (SCHEMA.Event, TOLKIEN_CLASS.Convention),
            'Event': (SCHEMA.Event, TOLKIEN_CLASS.Event),
            'Thing': (SCHEMA.Thing, TOLKIEN_CLASS.Thing),
        }
        
        # Ajouter les types
        schema_type, tolkien_type = TYPE_MAPPING.get(entity_type, (SCHEMA.Thing, TOLKIEN_CLASS.Thing))
        self.graph.add((uri, RDF.type, schema_type))
        self.graph.add((uri, RDF.type, tolkien_type))
        
        # Nom et label
        self._add_literal(uri, SCHEMA.name, name)
        self._add_literal(uri, RDFS.label, name, lang="en")
        
        # Lien vers la page wiki
        wiki_page = URIRef(f"https://tolkiengateway.net/wiki/{quote(name.replace(' ', '_'))}")
        self.graph.add((uri, FOAF.isPrimaryTopicOf, wiki_page))
        self.graph.add((uri, SCHEMA.mainEntityOfPage, wiki_page))
        
        # Image
        if 'image' in entity_data:
            image_name = entity_data['image']
            image_url = f"https://tolkiengateway.net/wiki/File:{quote(image_name)}"
            self.graph.add((uri, SCHEMA.image, URIRef(image_url)))
            self.graph.add((uri, FOAF.depiction, URIRef(image_url)))
        
        # Description
        if 'caption' in entity_data:
            self._add_literal(uri, SCHEMA.description, entity_data['caption'])
        if 'description' in entity_data:
            self._add_literal(uri, SCHEMA.description, entity_data['description'])
        if 'summary' in entity_data:
            self._add_literal(uri, SCHEMA.description, entity_data['summary'])
        
        # Autres noms
        if 'othernames' in entity_data:
            othernames = entity_data['othernames']
            if isinstance(othernames, list):
                for othername in othernames:
                    self._add_literal(uri, SCHEMA.alternateName, othername)
            else:
                self._add_literal(uri, SCHEMA.alternateName, othernames)
        
        # Auteur (pour les livres, etc.)
        if 'author' in entity_data:
            authors = entity_data['author']
            if isinstance(authors, list):
                for author in authors:
                    self._add_link(uri, SCHEMA.author, author)
            else:
                self._add_link(uri, SCHEMA.author, authors)
        
        # Date de publication
        if 'published' in entity_data:
            pub_data = entity_data['published']
            if isinstance(pub_data, dict) and pub_data.get('text'):
                self._add_literal(uri, SCHEMA.datePublished, pub_data['text'])
            else:
                self._add_literal(uri, SCHEMA.datePublished, str(pub_data))
        
        if 'released' in entity_data:
            rel_data = entity_data['released']
            if isinstance(rel_data, dict) and rel_data.get('text'):
                self._add_literal(uri, SCHEMA.datePublished, rel_data['text'])
            else:
                self._add_literal(uri, SCHEMA.datePublished, str(rel_data))
        
        # Date générique
        if 'date' in entity_data:
            date_data = entity_data['date']
            if isinstance(date_data, dict) and date_data.get('text'):
                self._add_literal(uri, SCHEMA.startDate, date_data['text'])
            else:
                self._add_literal(uri, SCHEMA.startDate, str(date_data))
        
        # Lieu
        if 'location' in entity_data:
            locations = entity_data['location']
            if isinstance(locations, list):
                for loc in locations:
                    self._add_link(uri, SCHEMA.location, loc)
            else:
                self._add_link(uri, SCHEMA.location, locations)
        
        # Participants (pour les batailles, événements)
        if 'participants' in entity_data:
            participants = entity_data['participants']
            if isinstance(participants, list):
                for participant in participants:
                    self._add_link(uri, SCHEMA.participant, participant)
            else:
                self._add_link(uri, SCHEMA.participant, participants)
        
        # Personnages (pour les livres, films)
        if 'characters' in entity_data:
            characters = entity_data['characters']
            if isinstance(characters, list):
                for char in characters:
                    self._add_link(uri, SCHEMA.character, char)
            else:
                self._add_link(uri, SCHEMA.character, characters)
        
        # Résultat (pour les batailles)
        if 'outcome' in entity_data:
            self._add_literal(uri, TOLKIEN_PROP.outcome, entity_data['outcome'])
        
        # Pages (pour les livres)
        if 'pages' in entity_data:
            pages = entity_data['pages']
            if isinstance(pages, int):
                self._add_literal(uri, SCHEMA.numberOfPages, pages, XSD.integer)
            else:
                self._add_literal(uri, SCHEMA.numberOfPages, pages)
        
        # Traiter tous les autres champs comme propriétés custom
        handled_fields = {'_type', '_template', 'name', 'image', 'caption', 'description', 
                         'summary', 'othernames', 'author', 'published', 'released', 'date',
                         'location', 'participants', 'characters', 'outcome', 'pages'}
        
        for field, value in entity_data.items():
            if field not in handled_fields and not field.startswith('_'):
                if value:
                    prop_uri = self._make_property_uri(field)
                    if isinstance(value, list):
                        for v in value:
                            if isinstance(v, str):
                                self._add_literal(uri, prop_uri, v)
                    elif isinstance(value, dict):
                        if value.get('text'):
                            self._add_literal(uri, prop_uri, value['text'])
                    elif isinstance(value, (int, float)):
                        self._add_literal(uri, prop_uri, value, XSD.integer if isinstance(value, int) else XSD.decimal)
                    else:
                        self._add_literal(uri, prop_uri, str(value))
        
        return uri
    
    def add_wiki_page_link(self, entity_uri: URIRef, page_title: str):
        """
        Ajoute un lien entre une entité et sa page wiki.
        
        Args:
            entity_uri: URI de l'entité
            page_title: Titre de la page wiki
        """
        wiki_page = URIRef(f"https://tolkiengateway.net/wiki/{quote(page_title.replace(' ', '_'))}")
        self.graph.add((entity_uri, FOAF.isPrimaryTopicOf, wiki_page))
        self.graph.add((wiki_page, FOAF.primaryTopic, entity_uri))
    
    def add_same_as(self, entity_uri: URIRef, external_uri: str):
        """
        Ajoute un lien owl:sameAs vers une ressource externe.
        
        Args:
            entity_uri: URI de l'entité locale
            external_uri: URI de la ressource externe (DBpedia, YAGO, etc.)
        """
        self.graph.add((entity_uri, OWL.sameAs, URIRef(external_uri)))
    
    def serialize(self, format: str = "turtle") -> str:
        """
        Sérialise le graphe RDF.
        
        Args:
            format: Format de sortie (turtle, xml, n3, nt, json-ld)
            
        Returns:
            Graphe sérialisé
        """
        return self.graph.serialize(format=format)
    
    def save(self, filename: str, format: str = "turtle"):
        """
        Sauvegarde le graphe RDF dans un fichier.
        
        Args:
            filename: Chemin du fichier
            format: Format de sortie
        """
        self.graph.serialize(destination=filename, format=format)
        print(f"Graphe sauvegardé dans {filename} ({len(self.graph)} triplets)")
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Retourne des statistiques sur le graphe.
        
        Returns:
            Dictionnaire avec les statistiques
        """
        stats = {
            'total_triples': len(self.graph),
            'subjects': len(set(self.graph.subjects())),
            'predicates': len(set(self.graph.predicates())),
            'objects': len(set(self.graph.objects())),
        }
        
        # Compter par type
        type_counts = {}
        for s, p, o in self.graph.triples((None, RDF.type, None)):
            type_name = str(o).split('/')[-1].split('#')[-1]
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        stats['types'] = type_counts
        
        return stats


class VocabularyGenerator:
    """
    Génère le vocabulaire RDFS/OWL pour le Knowledge Graph.
    """
    
    def __init__(self):
        self.graph = Graph()
        self._bind_namespaces()
    
    def _bind_namespaces(self):
        """Lie les préfixes aux namespaces."""
        self.graph.bind("tolkien", TOLKIEN)
        self.graph.bind("tolkien_prop", TOLKIEN_PROP)
        self.graph.bind("tolkien_class", TOLKIEN_CLASS)
        self.graph.bind("schema", SCHEMA)
        self.graph.bind("owl", OWL)
        self.graph.bind("rdfs", RDFS)
    
    def generate_vocabulary(self):
        """Génère les classes et propriétés du vocabulaire."""
        
        # === CLASSES ===
        
        # Character
        self.graph.add((TOLKIEN_CLASS.Character, RDF.type, OWL.Class))
        self.graph.add((TOLKIEN_CLASS.Character, RDFS.subClassOf, SCHEMA.Person))
        self.graph.add((TOLKIEN_CLASS.Character, RDFS.label, Literal("Character", lang="en")))
        self.graph.add((TOLKIEN_CLASS.Character, RDFS.comment, 
                       Literal("A fictional character from Tolkien's legendarium", lang="en")))
        
        # Location
        self.graph.add((TOLKIEN_CLASS.Location, RDF.type, OWL.Class))
        self.graph.add((TOLKIEN_CLASS.Location, RDFS.subClassOf, SCHEMA.Place))
        self.graph.add((TOLKIEN_CLASS.Location, RDFS.label, Literal("Location", lang="en")))
        self.graph.add((TOLKIEN_CLASS.Location, RDFS.comment,
                       Literal("A place in Tolkien's legendarium", lang="en")))
        
        # Kingdom
        self.graph.add((TOLKIEN_CLASS.Kingdom, RDF.type, OWL.Class))
        self.graph.add((TOLKIEN_CLASS.Kingdom, RDFS.subClassOf, TOLKIEN_CLASS.Location))
        self.graph.add((TOLKIEN_CLASS.Kingdom, RDFS.subClassOf, SCHEMA.Country))
        self.graph.add((TOLKIEN_CLASS.Kingdom, RDFS.label, Literal("Kingdom", lang="en")))
        
        # Race
        self.graph.add((TOLKIEN_CLASS.Race, RDF.type, OWL.Class))
        self.graph.add((TOLKIEN_CLASS.Race, RDFS.label, Literal("Race", lang="en")))
        self.graph.add((TOLKIEN_CLASS.Race, RDFS.comment,
                       Literal("A race or people in Tolkien's legendarium (Elves, Dwarves, etc.)", lang="en")))
        
        # === PROPRIÉTÉS ===
        
        # people (race/peuple)
        self.graph.add((TOLKIEN_PROP.people, RDF.type, OWL.ObjectProperty))
        self.graph.add((TOLKIEN_PROP.people, RDFS.domain, TOLKIEN_CLASS.Character))
        self.graph.add((TOLKIEN_PROP.people, RDFS.range, TOLKIEN_CLASS.Race))
        self.graph.add((TOLKIEN_PROP.people, RDFS.label, Literal("people", lang="en")))
        self.graph.add((TOLKIEN_PROP.people, RDFS.comment,
                       Literal("The race or people to which a character belongs", lang="en")))
        
        # house (maison noble)
        self.graph.add((TOLKIEN_PROP.house, RDF.type, OWL.ObjectProperty))
        self.graph.add((TOLKIEN_PROP.house, RDFS.subPropertyOf, SCHEMA.memberOf))
        self.graph.add((TOLKIEN_PROP.house, RDFS.label, Literal("house", lang="en")))
        
        # affiliation
        self.graph.add((TOLKIEN_PROP.affiliation, RDF.type, OWL.ObjectProperty))
        self.graph.add((TOLKIEN_PROP.affiliation, RDFS.subPropertyOf, SCHEMA.memberOf))
        self.graph.add((TOLKIEN_PROP.affiliation, RDFS.label, Literal("affiliation", lang="en")))
        
        # weapon
        self.graph.add((TOLKIEN_PROP.weapon, RDF.type, OWL.ObjectProperty))
        self.graph.add((TOLKIEN_PROP.weapon, RDFS.domain, TOLKIEN_CLASS.Character))
        self.graph.add((TOLKIEN_PROP.weapon, RDFS.label, Literal("weapon", lang="en")))
        
        # steed (monture)
        self.graph.add((TOLKIEN_PROP.steed, RDF.type, OWL.ObjectProperty))
        self.graph.add((TOLKIEN_PROP.steed, RDFS.domain, TOLKIEN_CLASS.Character))
        self.graph.add((TOLKIEN_PROP.steed, RDFS.label, Literal("steed", lang="en")))
        
        # capital
        self.graph.add((TOLKIEN_PROP.capital, RDF.type, OWL.ObjectProperty))
        self.graph.add((TOLKIEN_PROP.capital, RDFS.domain, TOLKIEN_CLASS.Kingdom))
        self.graph.add((TOLKIEN_PROP.capital, RDFS.range, TOLKIEN_CLASS.Location))
        self.graph.add((TOLKIEN_PROP.capital, RDFS.label, Literal("capital", lang="en")))
        
        # notableFor
        self.graph.add((TOLKIEN_PROP.notableFor, RDF.type, OWL.DatatypeProperty))
        self.graph.add((TOLKIEN_PROP.notableFor, RDFS.domain, TOLKIEN_CLASS.Character))
        self.graph.add((TOLKIEN_PROP.notableFor, RDFS.range, XSD.string))
        self.graph.add((TOLKIEN_PROP.notableFor, RDFS.label, Literal("notable for", lang="en")))
        
        # Date properties for Tolkien ages
        self.graph.add((TOLKIEN_PROP.age, RDF.type, OWL.DatatypeProperty))
        self.graph.add((TOLKIEN_PROP.age, RDFS.label, Literal("age code", lang="en")))
        self.graph.add((TOLKIEN_PROP.age, RDFS.comment,
                       Literal("Age code (FA, SA, TA, SR, YT)", lang="en")))
        
        self.graph.add((TOLKIEN_PROP.ageName, RDF.type, OWL.DatatypeProperty))
        self.graph.add((TOLKIEN_PROP.ageName, RDFS.label, Literal("age name", lang="en")))
        
        self.graph.add((TOLKIEN_PROP.year, RDF.type, OWL.DatatypeProperty))
        self.graph.add((TOLKIEN_PROP.year, RDFS.range, XSD.integer))
        self.graph.add((TOLKIEN_PROP.year, RDFS.label, Literal("year", lang="en")))
        
        return self.graph
    
    def serialize(self, format: str = "turtle") -> str:
        """Sérialise le vocabulaire."""
        return self.graph.serialize(format=format)
    
    def save(self, filename: str, format: str = "turtle"):
        """Sauvegarde le vocabulaire."""
        self.graph.serialize(destination=filename, format=format)
        print(f"Vocabulaire sauvegardé dans {filename} ({len(self.graph)} triplets)")
