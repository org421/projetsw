"""
Generation and validation of SHACL shapes for the Tolkien Knowledge Graph.
"""

from rdflib import Graph, Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, XSD, OWL, FOAF
import sys

# Define namespaces
SH = Namespace("http://www.w3.org/ns/shacl#")
TOLKIEN = Namespace("https://tolkiengateway.net/wiki/")
TOLKIEN_PROP = Namespace("https://tolkiengateway.net/wiki/Property:")
TOLKIEN_CLASS = Namespace("https://tolkiengateway.net/wiki/Class:")
SCHEMA = Namespace("http://schema.org/")
MECCG_CLASS = Namespace("https://tolkiengateway.net/wiki/MECCG/Class:")
MECCG_PROP = Namespace("https://tolkiengateway.net/wiki/MECCG/Property:")


class SHACLGenerator:
    """
    Manages the creation of SHACL validation rules.
    """
    
    def __init__(self):
        self.graph = Graph()
        self._bind_namespaces()
    
    def _bind_namespaces(self):
        """Binds prefixes to namespaces in the graph."""
        self.graph.bind("sh", SH)
        self.graph.bind("tolkien", TOLKIEN)
        self.graph.bind("tolkien_prop", TOLKIEN_PROP)
        self.graph.bind("tolkien_class", TOLKIEN_CLASS)
        self.graph.bind("schema", SCHEMA)
        self.graph.bind("xsd", XSD)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("foaf", FOAF)
        self.graph.bind("owl", OWL)
        self.graph.bind("meccg_class", MECCG_CLASS)
        self.graph.bind("meccg_prop", MECCG_PROP)
    
    def _add_property(self, shape: URIRef, path: URIRef, name: str,
                      min_count: int = None, max_count: int = None,
                      datatype: URIRef = None, node_kind: URIRef = None,
                      severity: URIRef = None, description: str = None,
                      has_value: URIRef = None, message: str = None):
        """Helper to add a property constraint to a shape."""
        prop = BNode()
        self.graph.add((shape, SH.property, prop))
        self.graph.add((prop, SH.path, path))
        self.graph.add((prop, SH.name, Literal(name)))
        
        if description:
            self.graph.add((prop, SH.description, Literal(description, lang="en")))
        if message:
            self.graph.add((prop, SH.message, Literal(message, lang="fr")))
        if min_count is not None:
            self.graph.add((prop, SH.minCount, Literal(min_count, datatype=XSD.integer)))
        if max_count is not None:
            self.graph.add((prop, SH.maxCount, Literal(max_count, datatype=XSD.integer)))
        if datatype:
            self.graph.add((prop, SH.datatype, datatype))
        if node_kind:
            self.graph.add((prop, SH.nodeKind, node_kind))
        if severity:
            self.graph.add((prop, SH.severity, severity))
        if has_value:
            self.graph.add((prop, SH.hasValue, has_value))
        
        return prop

    def create_character_shape(self):
        """Rules for Character entities."""
        shape = TOLKIEN_CLASS.CharacterShape
        self.graph.add((shape, RDF.type, SH.NodeShape))
        self.graph.add((shape, SH.targetClass, TOLKIEN_CLASS.Character))
        self.graph.add((shape, RDFS.label, Literal("Character Shape", lang="en")))
        
        # Required properties
        self._add_property(shape, SCHEMA.name, "name", min_count=1)
        self._add_property(shape, RDFS.label, "label", min_count=1)

        # Validate external links (sameAs must be an IRI)
        self._add_property(shape, OWL.sameAs, "sameAs", 
                          node_kind=SH.IRI,
                          message="Le lien sameAs doit être une URI valide vers une source externe.")
        
        # Optional properties
        self._add_property(shape, FOAF.isPrimaryTopicOf, "wikiPage",
                          node_kind=SH.IRI, severity=SH.Warning)
        self._add_property(shape, SCHEMA.description, "description")
        self._add_property(shape, TOLKIEN_PROP.race, "race", node_kind=SH.IRI)
        return shape

    def create_battle_shape(self):
        """Rules for Battle entities."""
        shape = TOLKIEN_CLASS.BattleShape
        self.graph.add((shape, RDF.type, SH.NodeShape))
        self.graph.add((shape, SH.targetClass, TOLKIEN_CLASS.Battle))
        self.graph.add((shape, RDFS.label, Literal("Battle Shape", lang="en")))
        
        # Type inference check (Battle -> Event)
        self._add_property(shape, RDF.type, "type inference check", 
                          has_value=SCHEMA.Event, 
                          severity=SH.Info,
                          message="[INFO] Vérification inférence: Cette entité est bien reconnue comme un schema:Event.")

        self._add_property(shape, SCHEMA.name, "name", min_count=1)
        self._add_property(shape, RDFS.label, "label", min_count=1)
        return shape

    def create_location_shape(self):
        """Rules for Location entities."""
        shape = TOLKIEN_CLASS.LocationShape
        self.graph.add((shape, RDF.type, SH.NodeShape))
        self.graph.add((shape, SH.targetClass, TOLKIEN_CLASS.Location))
        self._add_property(shape, SCHEMA.name, "name", min_count=1)
        self._add_property(shape, RDFS.label, "label", min_count=1)
        return shape

    def create_kingdom_shape(self):
        """Rules for Kingdom entities."""
        shape = TOLKIEN_CLASS.KingdomShape
        self.graph.add((shape, RDF.type, SH.NodeShape))
        self.graph.add((shape, SH.targetClass, TOLKIEN_CLASS.Kingdom))
        self._add_property(shape, SCHEMA.name, "name", min_count=1)
        return shape

    def create_book_shape(self):
        """Rules for Book entities."""
        shape = TOLKIEN_CLASS.BookShape
        self.graph.add((shape, RDF.type, SH.NodeShape))
        self.graph.add((shape, SH.targetClass, TOLKIEN_CLASS.Book))
        self._add_property(shape, SCHEMA.name, "name", min_count=1)
        return shape

    def create_object_shape(self):
        """Rules for Object entities."""
        shape = TOLKIEN_CLASS.ObjectShape
        self.graph.add((shape, RDF.type, SH.NodeShape))
        self.graph.add((shape, SH.targetClass, TOLKIEN_CLASS.Object))
        self._add_property(shape, SCHEMA.name, "name", min_count=1)
        return shape

    def create_race_shape(self):
        """Rules for Race entities."""
        shape = TOLKIEN_CLASS.RaceShape
        self.graph.add((shape, RDF.type, SH.NodeShape))
        self.graph.add((shape, SH.targetClass, TOLKIEN_CLASS.Race))
        self._add_property(shape, SCHEMA.name, "name", min_count=1)
        return shape
    
    def create_card_shape(self):
        """Rules for MECCG Card entities."""
        shape = MECCG_CLASS.CardShape
        self.graph.add((shape, RDF.type, SH.NodeShape))
        self.graph.add((shape, SH.targetClass, MECCG_CLASS.Card))
        self._add_property(shape, RDFS.label, "label", min_count=1)
        return shape

    def create_all_shapes(self):
        """Generates all defined SHACL shapes."""
        self.create_character_shape()
        self.create_battle_shape()
        self.create_location_shape()
        self.create_kingdom_shape()
        self.create_book_shape()
        self.create_object_shape()
        self.create_race_shape()
        self.create_card_shape()
        return self.graph
    
    def save(self, filename: str, format: str = "turtle"):
        """Serializes the SHACL graph to a file."""
        self.graph.serialize(destination=filename, format=format)
        print(f"SHACL file generated: {filename}")


class SHACLValidator:
    """
    Wrapper for pyshacl validation.
    """
    
    def __init__(self, shapes_file: str = None, shapes_graph: Graph = None):
        """Initializes with either a file path or an existing Graph."""
        self.shapes_graph = Graph()
        
        if shapes_graph:
            self.shapes_graph = shapes_graph
        elif shapes_file:
            self.shapes_graph.parse(shapes_file, format="turtle")
        else:
            raise ValueError("Error: Provide either shapes_file or shapes_graph.")
    
    def validate_and_report(self, data_input):
        """Validates input data (file path or Graph)."""
        data_graph = Graph()
        source_name = "Data"

        # Handle input type
        if isinstance(data_input, Graph):
            data_graph = data_input
            source_name = "Memory Graph"
        elif isinstance(data_input, str):
            print(f"Loading and validating: {data_input}")
            data_graph.parse(data_input, format="turtle")
            source_name = data_input
        else:
            print("Error: Unsupported data format.")
            return {'valid': None}

        try:
            from pyshacl import validate
            
            # Validation with RDFS inference
            conforms, results_graph, results_text = validate(
                data_graph,
                shacl_graph=self.shapes_graph,
                inference='rdfs', 
                abort_on_first=False
            )
            
            if conforms:
                print(f"{source_name}: Valid.")
            else:
                print(f"{source_name}: Violations found.")
                limit = 800
                print(results_text[:limit] + ("..." if len(results_text) > limit else ""))
            
            return {
                'valid': conforms,
                'results_text': results_text,
                'results_graph': results_graph
            }
            
        except ImportError:
            print("Error: pyshacl library missing.")
            return {'valid': None}

    def print_report(self, report, max_details=5):
        """Compatibility method for printing reports."""
        pass


if __name__ == "__main__":
    output_file = "tolkien_shapes.ttl"
    gen = SHACLGenerator()
    gen.create_all_shapes()
    gen.save(output_file)