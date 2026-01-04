"""
SHACL Shapes pour le Knowledge Graph Tolkien
Définit les contraintes de validation pour chaque type d'entité
"""

from rdflib import Graph, Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, XSD, OWL, FOAF
from typing import Dict, List, Any, Tuple


# Namespaces
SH = Namespace("http://www.w3.org/ns/shacl#")
TOLKIEN = Namespace("https://tolkiengateway.net/wiki/")
TOLKIEN_PROP = Namespace("https://tolkiengateway.net/wiki/Property:")
TOLKIEN_CLASS = Namespace("https://tolkiengateway.net/wiki/Class:")
SCHEMA = Namespace("http://schema.org/")


class SHACLGenerator:
    """
    Génère les shapes SHACL pour valider le Knowledge Graph.
    Chaque shape correspond à un type d'infobox du wiki.
    """
    
    def __init__(self):
        self.graph = Graph()
        self._bind_namespaces()
    
    def _bind_namespaces(self):
        """Lie les préfixes aux namespaces."""
        self.graph.bind("sh", SH)
        self.graph.bind("tolkien", TOLKIEN)
        self.graph.bind("tolkien_prop", TOLKIEN_PROP)
        self.graph.bind("tolkien_class", TOLKIEN_CLASS)
        self.graph.bind("schema", SCHEMA)
        self.graph.bind("xsd", XSD)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("foaf", FOAF)
        self.graph.bind("owl", OWL)
    
    def _add_property_shape(self, shape_uri: URIRef, path: URIRef, 
                            name: str, datatype: URIRef = None,
                            node_kind: URIRef = None, class_constraint: URIRef = None,
                            min_count: int = None, max_count: int = None,
                            pattern: str = None, min_length: int = None,
                            description: str = None, severity: URIRef = None):
        """
        Ajoute une contrainte de propriété à un shape.
        """
        prop_shape = BNode()
        self.graph.add((shape_uri, SH.property, prop_shape))
        self.graph.add((prop_shape, SH.path, path))
        self.graph.add((prop_shape, SH.name, Literal(name)))
        
        if description:
            self.graph.add((prop_shape, SH.description, Literal(description, lang="en")))
        
        if datatype:
            self.graph.add((prop_shape, SH.datatype, datatype))
        
        if node_kind:
            self.graph.add((prop_shape, SH.nodeKind, node_kind))
        
        if class_constraint:
            self.graph.add((prop_shape, SH["class"], class_constraint))
        
        if min_count is not None:
            self.graph.add((prop_shape, SH.minCount, Literal(min_count, datatype=XSD.integer)))
        
        if max_count is not None:
            self.graph.add((prop_shape, SH.maxCount, Literal(max_count, datatype=XSD.integer)))
        
        if pattern:
            self.graph.add((prop_shape, SH.pattern, Literal(pattern)))
        
        if min_length:
            self.graph.add((prop_shape, SH.minLength, Literal(min_length, datatype=XSD.integer)))
        
        if severity:
            self.graph.add((prop_shape, SH.severity, severity))
        
        return prop_shape

    # =========================================================================
    # SHAPE: Character (Infobox character)
    # =========================================================================
    
    def create_character_shape(self) -> URIRef:
        """
        Crée le shape SHACL pour les personnages.
        Basé sur le template "Infobox character".
        """
        shape_uri = TOLKIEN_CLASS.CharacterShape
        
        # Définition du shape
        self.graph.add((shape_uri, RDF.type, SH.NodeShape))
        self.graph.add((shape_uri, SH.targetClass, TOLKIEN_CLASS.Character))
        self.graph.add((shape_uri, RDFS.label, Literal("Character Shape", lang="en")))
        self.graph.add((shape_uri, RDFS.comment, 
                       Literal("Validates characters from Tolkien's legendarium (Infobox character)", lang="en")))
        
        # --- Propriétés REQUISES ---
        
        self._add_property_shape(
            shape_uri, SCHEMA.name, "name",
            datatype=XSD.string, min_count=1, max_count=1,
            min_length=1,
            description="Name of the character (required)"
        )
        
        self._add_property_shape(
            shape_uri, RDFS.label, "label",
            min_count=1,
            description="Human-readable label (required)"
        )
        
        # --- Propriétés RECOMMANDÉES (Warning si absentes) ---
        
        self._add_property_shape(
            shape_uri, SCHEMA.gender, "gender",
            datatype=XSD.string, max_count=1,
            severity=SH.Warning,
            description="Gender (Male/Female)"
        )
        
        self._add_property_shape(
            shape_uri, TOLKIEN_PROP.people, "people",
            node_kind=SH.IRI, max_count=1,
            severity=SH.Warning,
            description="Race or people (Elves, Hobbits, Men, etc.)"
        )
        
        # --- Propriétés OPTIONNELLES ---
        
        # Identification
        self._add_property_shape(
            shape_uri, SCHEMA.image, "image",
            node_kind=SH.IRI,
            description="Image depicting the character"
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.description, "description",
            datatype=XSD.string, max_count=1,
            description="Description or caption"
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.alternateName, "alternateName",
            datatype=XSD.string,
            description="Other names (Sindarin, Quenya, etc.)"
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.jobTitle, "titles",
            datatype=XSD.string,
            description="Titles held by the character"
        )
        
        # Dates
        self._add_property_shape(
            shape_uri, SCHEMA.birthDate, "birthDate",
            max_count=1,
            description="Birth date (may be structured with age/year)"
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.birthPlace, "birthPlace",
            node_kind=SH.IRI, max_count=1,
            description="Place of birth"
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.deathDate, "deathDate",
            max_count=1,
            description="Death date"
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.deathPlace, "deathPlace",
            node_kind=SH.IRI, max_count=1,
            description="Place of death"
        )
        
        self._add_property_shape(
            shape_uri, TOLKIEN_PROP.age, "age",
            description="Age of the character"
        )
        
        # Relations familiales
        self._add_property_shape(
            shape_uri, SCHEMA.parent, "parent",
            node_kind=SH.IRI,
            description="Parents of the character"
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.sibling, "sibling",
            node_kind=SH.IRI,
            description="Siblings"
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.spouse, "spouse",
            node_kind=SH.IRI,
            description="Spouse(s)"
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.children, "children",
            node_kind=SH.IRI,
            description="Children"
        )
        
        self._add_property_shape(
            shape_uri, TOLKIEN_PROP.house, "house",
            node_kind=SH.IRI, max_count=1,
            description="Noble house (House of Hador, etc.)"
        )
        
        # Affiliations et lieux
        self._add_property_shape(
            shape_uri, SCHEMA.memberOf, "memberOf",
            node_kind=SH.IRI,
            description="Organizations or groups"
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.homeLocation, "homeLocation",
            node_kind=SH.IRI,
            description="Locations where the character lived"
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.knowsLanguage, "knowsLanguage",
            datatype=XSD.string,
            description="Languages spoken"
        )
        
        # Équipement
        self._add_property_shape(
            shape_uri, TOLKIEN_PROP.weapon, "weapon",
            node_kind=SH.IRI,
            description="Weapons wielded"
        )
        
        self._add_property_shape(
            shape_uri, TOLKIEN_PROP.steed, "steed",
            node_kind=SH.IRI, max_count=1,
            description="Mount/steed"
        )
        
        # Liens externes
        self._add_property_shape(
            shape_uri, OWL.sameAs, "sameAs",
            node_kind=SH.IRI,
            description="Links to external resources (DBpedia, etc.)"
        )
        
        return shape_uri

    # =========================================================================
    # SHAPE: Location (Location infobox)
    # =========================================================================
    
    def create_location_shape(self) -> URIRef:
        """
        Crée le shape SHACL pour les lieux.
        Basé sur le template "Location infobox".
        """
        shape_uri = TOLKIEN_CLASS.LocationShape
        
        self.graph.add((shape_uri, RDF.type, SH.NodeShape))
        self.graph.add((shape_uri, SH.targetClass, TOLKIEN_CLASS.Location))
        self.graph.add((shape_uri, RDFS.label, Literal("Location Shape", lang="en")))
        self.graph.add((shape_uri, RDFS.comment,
                       Literal("Validates locations from Tolkien's legendarium", lang="en")))
        
        # Requis
        self._add_property_shape(
            shape_uri, SCHEMA.name, "name",
            datatype=XSD.string, min_count=1, max_count=1, min_length=1,
            description="Name of the location (required)"
        )
        
        self._add_property_shape(
            shape_uri, RDFS.label, "label",
            min_count=1,
            description="Human-readable label (required)"
        )
        
        # Optionnel
        self._add_property_shape(
            shape_uri, SCHEMA.image, "image",
            node_kind=SH.IRI,
            description="Image of the location"
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.description, "description",
            datatype=XSD.string, max_count=1,
            description="Description"
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.alternateName, "alternateName",
            datatype=XSD.string,
            description="Other names"
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.containedInPlace, "containedInPlace",
            node_kind=SH.IRI,
            description="Larger location containing this one"
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.containsPlace, "containsPlace",
            node_kind=SH.IRI,
            description="Smaller locations within this one"
        )
        
        self._add_property_shape(
            shape_uri, TOLKIEN_PROP.inhabitants, "inhabitants",
            datatype=XSD.string,
            description="Types of inhabitants"
        )
        
        return shape_uri

    # =========================================================================
    # SHAPE: Kingdom
    # =========================================================================
    
    def create_kingdom_shape(self) -> URIRef:
        """
        Crée le shape SHACL pour les royaumes.
        Basé sur le template "Kingdom".
        """
        shape_uri = TOLKIEN_CLASS.KingdomShape
        
        self.graph.add((shape_uri, RDF.type, SH.NodeShape))
        self.graph.add((shape_uri, SH.targetClass, TOLKIEN_CLASS.Kingdom))
        self.graph.add((shape_uri, RDFS.label, Literal("Kingdom Shape", lang="en")))
        self.graph.add((shape_uri, RDFS.comment,
                       Literal("Validates kingdoms and realms", lang="en")))
        
        # Requis
        self._add_property_shape(
            shape_uri, SCHEMA.name, "name",
            datatype=XSD.string, min_count=1, max_count=1,
            description="Name of the kingdom (required)"
        )
        
        self._add_property_shape(
            shape_uri, RDFS.label, "label",
            min_count=1,
            description="Human-readable label (required)"
        )
        
        # Spécifique aux royaumes
        self._add_property_shape(
            shape_uri, TOLKIEN_PROP.capital, "capital",
            node_kind=SH.IRI, max_count=1,
            severity=SH.Warning,
            description="Capital city"
        )
        
        self._add_property_shape(
            shape_uri, TOLKIEN_PROP.governance, "governance",
            datatype=XSD.string,
            description="Type of governance"
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.containedInPlace, "containedInPlace",
            node_kind=SH.IRI,
            description="Larger region containing the kingdom"
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.containsPlace, "containsPlace",
            node_kind=SH.IRI,
            description="Regions within the kingdom"
        )
        
        return shape_uri

    # =========================================================================
    # SHAPE: Book
    # =========================================================================
    
    def create_book_shape(self) -> URIRef:
        """
        Crée le shape SHACL pour les livres.
        Basé sur le template "Book".
        """
        shape_uri = TOLKIEN_CLASS.BookShape
        
        self.graph.add((shape_uri, RDF.type, SH.NodeShape))
        self.graph.add((shape_uri, SH.targetClass, TOLKIEN_CLASS.Book))
        self.graph.add((shape_uri, RDFS.label, Literal("Book Shape", lang="en")))
        self.graph.add((shape_uri, RDFS.comment,
                       Literal("Validates books and publications", lang="en")))
        
        # Requis
        self._add_property_shape(
            shape_uri, SCHEMA.name, "name",
            datatype=XSD.string, min_count=1, max_count=1,
            description="Title of the book (required)"
        )
        
        self._add_property_shape(
            shape_uri, RDFS.label, "label",
            min_count=1,
            description="Human-readable label (required)"
        )
        
        # Recommandé
        self._add_property_shape(
            shape_uri, SCHEMA.author, "author",
            node_kind=SH.IRI,
            severity=SH.Warning,
            description="Author of the book"
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.datePublished, "datePublished",
            max_count=1,
            severity=SH.Warning,
            description="Publication date"
        )
        
        # Optionnel
        self._add_property_shape(
            shape_uri, SCHEMA.image, "image",
            node_kind=SH.IRI,
            description="Cover image"
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.numberOfPages, "numberOfPages",
            datatype=XSD.integer, max_count=1,
            description="Number of pages"
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.publisher, "publisher",
            datatype=XSD.string,
            description="Publisher"
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.isbn, "isbn",
            datatype=XSD.string,
            description="ISBN"
        )
        
        return shape_uri

    # =========================================================================
    # SHAPE: Battle
    # =========================================================================
    
    def create_battle_shape(self) -> URIRef:
        """
        Crée le shape SHACL pour les batailles.
        Basé sur le template "Battle".
        """
        shape_uri = TOLKIEN_CLASS.BattleShape
        
        self.graph.add((shape_uri, RDF.type, SH.NodeShape))
        self.graph.add((shape_uri, SH.targetClass, TOLKIEN_CLASS.Battle))
        self.graph.add((shape_uri, RDFS.label, Literal("Battle Shape", lang="en")))
        self.graph.add((shape_uri, RDFS.comment,
                       Literal("Validates battles and military conflicts", lang="en")))
        
        # Requis
        self._add_property_shape(
            shape_uri, SCHEMA.name, "name",
            datatype=XSD.string, min_count=1, max_count=1,
            description="Name of the battle (required)"
        )
        
        self._add_property_shape(
            shape_uri, RDFS.label, "label",
            min_count=1,
            description="Human-readable label (required)"
        )
        
        # Recommandé
        self._add_property_shape(
            shape_uri, SCHEMA.location, "location",
            node_kind=SH.IRI,
            severity=SH.Warning,
            description="Location of the battle"
        )
        
        self._add_property_shape(
            shape_uri, TOLKIEN_PROP.outcome, "outcome",
            datatype=XSD.string, max_count=1,
            description="Outcome of the battle"
        )
        
        # Optionnel
        self._add_property_shape(
            shape_uri, SCHEMA.startDate, "date",
            max_count=1,
            description="Date of the battle"
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.participant, "participant",
            node_kind=SH.IRI,
            description="Participants in the battle"
        )
        
        return shape_uri

    # =========================================================================
    # SHAPE: War
    # =========================================================================
    
    def create_war_shape(self) -> URIRef:
        """Crée le shape SHACL pour les guerres."""
        shape_uri = TOLKIEN_CLASS.WarShape
        
        self.graph.add((shape_uri, RDF.type, SH.NodeShape))
        self.graph.add((shape_uri, SH.targetClass, TOLKIEN_CLASS.War))
        self.graph.add((shape_uri, RDFS.label, Literal("War Shape", lang="en")))
        
        self._add_property_shape(
            shape_uri, SCHEMA.name, "name",
            datatype=XSD.string, min_count=1, max_count=1,
            description="Name of the war (required)"
        )
        
        self._add_property_shape(
            shape_uri, RDFS.label, "label", min_count=1
        )
        
        self._add_property_shape(
            shape_uri, TOLKIEN_PROP.outcome, "outcome",
            datatype=XSD.string, max_count=1
        )
        
        return shape_uri

    # =========================================================================
    # SHAPE: Film
    # =========================================================================
    
    def create_film_shape(self) -> URIRef:
        """Crée le shape SHACL pour les films."""
        shape_uri = TOLKIEN_CLASS.FilmShape
        
        self.graph.add((shape_uri, RDF.type, SH.NodeShape))
        self.graph.add((shape_uri, SH.targetClass, TOLKIEN_CLASS.Film))
        self.graph.add((shape_uri, RDFS.label, Literal("Film Shape", lang="en")))
        
        self._add_property_shape(
            shape_uri, SCHEMA.name, "name",
            datatype=XSD.string, min_count=1, max_count=1,
            description="Title of the film (required)"
        )
        
        self._add_property_shape(
            shape_uri, RDFS.label, "label", min_count=1
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.director, "director",
            node_kind=SH.IRI, severity=SH.Warning,
            description="Director of the film"
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.datePublished, "releaseDate",
            max_count=1, severity=SH.Warning
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.image, "image", node_kind=SH.IRI
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.actor, "actor", node_kind=SH.IRI
        )
        
        return shape_uri

    # =========================================================================
    # SHAPE: VideoGame
    # =========================================================================
    
    def create_videogame_shape(self) -> URIRef:
        """Crée le shape SHACL pour les jeux vidéo."""
        shape_uri = TOLKIEN_CLASS.VideoGameShape
        
        self.graph.add((shape_uri, RDF.type, SH.NodeShape))
        self.graph.add((shape_uri, SH.targetClass, TOLKIEN_CLASS.VideoGame))
        self.graph.add((shape_uri, RDFS.label, Literal("Video Game Shape", lang="en")))
        
        self._add_property_shape(
            shape_uri, SCHEMA.name, "name",
            datatype=XSD.string, min_count=1, max_count=1
        )
        
        self._add_property_shape(
            shape_uri, RDFS.label, "label", min_count=1
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.image, "image", node_kind=SH.IRI
        )
        
        return shape_uri

    # =========================================================================
    # SHAPE: Song
    # =========================================================================
    
    def create_song_shape(self) -> URIRef:
        """Crée le shape SHACL pour les chansons/poèmes."""
        shape_uri = TOLKIEN_CLASS.SongShape
        
        self.graph.add((shape_uri, RDF.type, SH.NodeShape))
        self.graph.add((shape_uri, SH.targetClass, TOLKIEN_CLASS.Song))
        self.graph.add((shape_uri, RDFS.label, Literal("Song Shape", lang="en")))
        
        self._add_property_shape(
            shape_uri, SCHEMA.name, "name",
            datatype=XSD.string, min_count=1, max_count=1
        )
        
        self._add_property_shape(
            shape_uri, RDFS.label, "label", min_count=1
        )
        
        return shape_uri

    # =========================================================================
    # SHAPE: Actor
    # =========================================================================
    
    def create_actor_shape(self) -> URIRef:
        """Crée le shape SHACL pour les acteurs."""
        shape_uri = TOLKIEN_CLASS.ActorShape
        
        self.graph.add((shape_uri, RDF.type, SH.NodeShape))
        self.graph.add((shape_uri, SH.targetClass, TOLKIEN_CLASS.Actor))
        self.graph.add((shape_uri, RDFS.label, Literal("Actor Shape", lang="en")))
        
        self._add_property_shape(
            shape_uri, SCHEMA.name, "name",
            datatype=XSD.string, min_count=1, max_count=1
        )
        
        self._add_property_shape(
            shape_uri, RDFS.label, "label", min_count=1
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.image, "image", node_kind=SH.IRI
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.birthDate, "birthDate", max_count=1
        )
        
        return shape_uri

    # =========================================================================
    # SHAPE: Author
    # =========================================================================
    
    def create_author_shape(self) -> URIRef:
        """Crée le shape SHACL pour les auteurs."""
        shape_uri = TOLKIEN_CLASS.AuthorShape
        
        self.graph.add((shape_uri, RDF.type, SH.NodeShape))
        self.graph.add((shape_uri, SH.targetClass, TOLKIEN_CLASS.Author))
        self.graph.add((shape_uri, RDFS.label, Literal("Author Shape", lang="en")))
        
        self._add_property_shape(
            shape_uri, SCHEMA.name, "name",
            datatype=XSD.string, min_count=1, max_count=1
        )
        
        self._add_property_shape(
            shape_uri, RDFS.label, "label", min_count=1
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.image, "image", node_kind=SH.IRI
        )
        
        return shape_uri

    # =========================================================================
    # SHAPE: Object
    # =========================================================================
    
    def create_object_shape(self) -> URIRef:
        """Crée le shape SHACL pour les objets."""
        shape_uri = TOLKIEN_CLASS.ObjectShape
        
        self.graph.add((shape_uri, RDF.type, SH.NodeShape))
        self.graph.add((shape_uri, SH.targetClass, TOLKIEN_CLASS.Object))
        self.graph.add((shape_uri, RDFS.label, Literal("Object Shape", lang="en")))
        
        self._add_property_shape(
            shape_uri, SCHEMA.name, "name",
            datatype=XSD.string, min_count=1, max_count=1
        )
        
        self._add_property_shape(
            shape_uri, RDFS.label, "label", min_count=1
        )
        
        self._add_property_shape(
            shape_uri, SCHEMA.image, "image", node_kind=SH.IRI
        )
        
        return shape_uri

    # =========================================================================
    # SHAPE: Race/People
    # =========================================================================
    
    def create_race_shape(self) -> URIRef:
        """Crée le shape SHACL pour les races/peuples."""
        shape_uri = TOLKIEN_CLASS.RaceShape
        
        self.graph.add((shape_uri, RDF.type, SH.NodeShape))
        self.graph.add((shape_uri, SH.targetClass, TOLKIEN_CLASS.Race))
        self.graph.add((shape_uri, RDFS.label, Literal("Race Shape", lang="en")))
        
        self._add_property_shape(
            shape_uri, SCHEMA.name, "name",
            datatype=XSD.string, min_count=1, max_count=1
        )
        
        self._add_property_shape(
            shape_uri, RDFS.label, "label", min_count=1
        )
        
        return shape_uri

    # =========================================================================
    # GÉNÉRATION COMPLÈTE
    # =========================================================================
    
    def create_all_shapes(self) -> Graph:
        """Crée tous les shapes SHACL pour le Knowledge Graph."""
        print("Génération des shapes SHACL...")
        
        shapes = [
            ("Character", self.create_character_shape),
            ("Location", self.create_location_shape),
            ("Kingdom", self.create_kingdom_shape),
            ("Book", self.create_book_shape),
            ("Battle", self.create_battle_shape),
            ("War", self.create_war_shape),
            ("Film", self.create_film_shape),
            ("VideoGame", self.create_videogame_shape),
            ("Song", self.create_song_shape),
            ("Actor", self.create_actor_shape),
            ("Author", self.create_author_shape),
            ("Object", self.create_object_shape),
            ("Race", self.create_race_shape),
        ]
        
        for name, create_func in shapes:
            create_func()
            print(f"  ✓ {name}Shape")
        
        print(f"\nTotal: {len(self.graph)} triplets SHACL")
        return self.graph
    
    def serialize(self, format: str = "turtle") -> str:
        """Sérialise les shapes en Turtle."""
        return self.graph.serialize(format=format)
    
    def save(self, filename: str, format: str = "turtle"):
        """Sauvegarde les shapes dans un fichier."""
        self.graph.serialize(destination=filename, format=format)
        print(f"Shapes sauvegardés dans {filename}")


# =============================================================================
# VALIDATEUR SHACL
# =============================================================================

class SHACLValidator:
    """
    Valide un graphe RDF contre les shapes SHACL.
    Nécessite pyshacl: pip install pyshacl
    """
    
    def __init__(self, shapes_graph: Graph = None, shapes_file: str = None):
        """
        Args:
            shapes_graph: Graphe contenant les shapes SHACL
            shapes_file: Ou fichier Turtle des shapes
        """
        if shapes_graph:
            self.shapes_graph = shapes_graph
        elif shapes_file:
            self.shapes_graph = Graph()
            self.shapes_graph.parse(shapes_file, format="turtle")
        else:
            raise ValueError("shapes_graph ou shapes_file requis")
    
    def validate(self, data_graph: Graph) -> Tuple[bool, Graph, str]:
        """
        Valide un graphe de données contre les shapes.
        
        Returns:
            Tuple (conforms, results_graph, results_text)
        """
        try:
            from pyshacl import validate
            
            conforms, results_graph, results_text = validate(
                data_graph,
                shacl_graph=self.shapes_graph,
                inference='none',
                abort_on_first=False,
                meta_shacl=False,
                debug=False
            )
            
            return conforms, results_graph, results_text
            
        except ImportError:
            print("⚠️  pyshacl non installé. Installez avec: pip install pyshacl")
            return None, None, "pyshacl not installed"
    
    def validate_and_report(self, data_graph: Graph) -> Dict[str, Any]:
        """Valide et génère un rapport détaillé."""
        conforms, results_graph, results_text = self.validate(data_graph)
        
        if conforms is None:
            return {
                'valid': None,
                'error': 'pyshacl not installed',
                'violations': [],
                'warnings': [],
                'summary': {}
            }
        
        report = {
            'valid': conforms,
            'violations': [],
            'warnings': [],
            'summary': {
                'total_violations': 0,
                'total_warnings': 0,
                'by_property': {},
                'by_shape': {}
            }
        }
        
        if results_graph:
            for result in results_graph.subjects(RDF.type, SH.ValidationResult):
                severity = str(results_graph.value(result, SH.resultSeverity))
                
                violation = {
                    'focus_node': str(results_graph.value(result, SH.focusNode)),
                    'path': str(results_graph.value(result, SH.resultPath)),
                    'message': str(results_graph.value(result, SH.resultMessage)),
                    'severity': severity.split('#')[-1] if '#' in severity else severity,
                    'source_shape': str(results_graph.value(result, SH.sourceShape)),
                    'value': str(results_graph.value(result, SH.value))
                }
                
                if 'Warning' in severity:
                    report['warnings'].append(violation)
                    report['summary']['total_warnings'] += 1
                else:
                    report['violations'].append(violation)
                    report['summary']['total_violations'] += 1
                
                # Résumé par propriété
                path = violation['path']
                if path not in report['summary']['by_property']:
                    report['summary']['by_property'][path] = {'violations': 0, 'warnings': 0}
                if 'Warning' in severity:
                    report['summary']['by_property'][path]['warnings'] += 1
                else:
                    report['summary']['by_property'][path]['violations'] += 1
        
        return report
    
    def print_report(self, report: Dict[str, Any], max_details: int = 10):
        """Affiche un rapport de validation formaté."""
        print("\n" + "=" * 70)
        print(" RAPPORT DE VALIDATION SHACL")
        print("=" * 70)
        
        if report['valid'] is None:
            print(f"\n⚠️  Erreur: {report.get('error', 'Unknown error')}")
            print("   Installez pyshacl: pip install pyshacl")
            return
        
        summary = report['summary']
        
        if report['valid'] and summary['total_warnings'] == 0:
            print("\n✅ Le graphe est VALIDE - Toutes les contraintes sont respectées")
            return
        
        # Résumé global
        print(f"\n📊 Résumé:")
        print(f"   Violations (erreurs): {summary['total_violations']}")
        print(f"   Warnings (avertissements): {summary['total_warnings']}")
        
        if report['valid']:
            print("\n✅ Le graphe est VALIDE (avec warnings)")
        else:
            print("\n❌ Le graphe est INVALIDE")
        
        # Résumé par propriété
        if summary['by_property']:
            print(f"\n📋 Par propriété:")
            for path, counts in sorted(summary['by_property'].items(), 
                                       key=lambda x: -(x[1]['violations'] + x[1]['warnings'])):
                prop_name = path.split('/')[-1].split('#')[-1]
                v = counts['violations']
                w = counts['warnings']
                status = []
                if v > 0:
                    status.append(f"{v} erreur(s)")
                if w > 0:
                    status.append(f"{w} warning(s)")
                print(f"   {prop_name}: {', '.join(status)}")
        
        # Détail des violations
        if report['violations']:
            print(f"\n🔴 Violations (max {max_details}):")
            for i, v in enumerate(report['violations'][:max_details], 1):
                focus = v['focus_node'].split('/')[-1]
                path = v['path'].split('/')[-1].split('#')[-1]
                print(f"\n   {i}. {focus}")
                print(f"      Propriété: {path}")
                if v['message'] and v['message'] != 'None':
                    print(f"      Message: {v['message']}")
            
            if len(report['violations']) > max_details:
                print(f"\n   ... et {len(report['violations']) - max_details} autres violations")
        
        # Détail des warnings
        if report['warnings']:
            print(f"\n🟡 Warnings (max {max_details}):")
            for i, w in enumerate(report['warnings'][:max_details], 1):
                focus = w['focus_node'].split('/')[-1]
                path = w['path'].split('/')[-1].split('#')[-1]
                print(f"\n   {i}. {focus}")
                print(f"      Propriété manquante: {path}")
            
            if len(report['warnings']) > max_details:
                print(f"\n   ... et {len(report['warnings']) - max_details} autres warnings")


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def create_shapes_file(filename: str = "tolkien_shapes.ttl") -> SHACLGenerator:
    """Crée et sauvegarde le fichier des shapes SHACL."""
    generator = SHACLGenerator()
    generator.create_all_shapes()
    generator.save(filename)
    return generator


def validate_kg(kg_file: str, shapes_file: str = "tolkien_shapes.ttl") -> Dict[str, Any]:
    """
    Valide un Knowledge Graph contre les shapes SHACL.
    
    Args:
        kg_file: Fichier du Knowledge Graph (Turtle)
        shapes_file: Fichier des shapes SHACL
        
    Returns:
        Rapport de validation
    """
    print(f"Chargement du KG: {kg_file}")
    data_graph = Graph()
    data_graph.parse(kg_file, format="turtle")
    print(f"  {len(data_graph)} triplets chargés")
    
    print(f"Chargement des shapes: {shapes_file}")
    validator = SHACLValidator(shapes_file=shapes_file)
    print(f"  {len(validator.shapes_graph)} triplets SHACL chargés")
    
    print("\nValidation en cours...")
    report = validator.validate_and_report(data_graph)
    validator.print_report(report)
    
    return report
