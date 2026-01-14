"""
SHACL Shapes pour le Tolkien Knowledge Graph
Validation simple et adaptée au RDF généré par le projet
"""

from rdflib import Graph, Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, XSD, OWL, FOAF
from typing import Dict, Any, Tuple


# =============================================================================
# NAMESPACES
# =============================================================================

SH = Namespace("http://www.w3.org/ns/shacl#")
TOLKIEN = Namespace("https://tolkiengateway.net/wiki/")
TOLKIEN_PROP = Namespace("https://tolkiengateway.net/wiki/Property:")
TOLKIEN_CLASS = Namespace("https://tolkiengateway.net/wiki/Class:")
SCHEMA = Namespace("http://schema.org/")
MECCG_CLASS = Namespace("https://tolkiengateway.net/wiki/MECCG/Class:")
MECCG_PROP = Namespace("https://tolkiengateway.net/wiki/MECCG/Property:")


# =============================================================================
# GÉNÉRATEUR SHACL
# =============================================================================

class SHACLGenerator:
    """
    Génère des shapes SHACL simples pour valider le Tolkien KG.
    Les contraintes sont minimales pour éviter les faux positifs.
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
        self.graph.bind("meccg_class", MECCG_CLASS)
        self.graph.bind("meccg_prop", MECCG_PROP)
    
    def _add_property(self, shape: URIRef, path: URIRef, name: str,
                      min_count: int = None, max_count: int = None,
                      datatype: URIRef = None, node_kind: URIRef = None,
                      severity: URIRef = None, description: str = None):
        """
        Ajoute une contrainte de propriété à un shape.
        
        Args:
            shape: URI du shape parent
            path: URI de la propriété
            name: Nom lisible de la propriété
            min_count: Nombre minimum d'occurrences
            max_count: Nombre maximum d'occurrences
            datatype: Type de données XSD
            node_kind: Type de noeud (IRI, Literal, etc.)
            severity: Niveau de sévérité (Violation, Warning, Info)
            description: Description de la contrainte
        """
        prop = BNode()
        self.graph.add((shape, SH.property, prop))
        self.graph.add((prop, SH.path, path))
        self.graph.add((prop, SH.name, Literal(name)))
        
        if description:
            self.graph.add((prop, SH.description, Literal(description, lang="en")))
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
        
        return prop

    # =========================================================================
    # SHAPE: Character
    # =========================================================================
    
    def create_character_shape(self):
        """Shape pour les personnages (Infobox character)."""
        shape = TOLKIEN_CLASS.CharacterShape
        
        self.graph.add((shape, RDF.type, SH.NodeShape))
        self.graph.add((shape, SH.targetClass, TOLKIEN_CLASS.Character))
        self.graph.add((shape, RDFS.label, Literal("Character Shape", lang="en")))
        self.graph.add((shape, RDFS.comment, 
            Literal("Validates characters from Tolkien's legendarium", lang="en")))
        
        # REQUIS: nom et label
        self._add_property(shape, SCHEMA.name, "name", 
                          min_count=1, description="Character name (required)")
        self._add_property(shape, RDFS.label, "label", 
                          min_count=1, description="Human-readable label (required)")
        
        # RECOMMANDÉ (warnings)
        self._add_property(shape, FOAF.isPrimaryTopicOf, "wikiPage",
                          node_kind=SH.IRI, severity=SH.Warning,
                          description="Link to wiki page")
        
        # OPTIONNEL - Identification
        self._add_property(shape, SCHEMA.image, "image", node_kind=SH.IRI)
        self._add_property(shape, FOAF.depiction, "depiction", node_kind=SH.IRI)
        self._add_property(shape, SCHEMA.description, "description")
        self._add_property(shape, SCHEMA.alternateName, "alternateName")
        self._add_property(shape, SCHEMA.jobTitle, "title")
        
        # OPTIONNEL - Dates
        self._add_property(shape, SCHEMA.birthDate, "birthDate")
        self._add_property(shape, SCHEMA.birthPlace, "birthPlace", node_kind=SH.IRI)
        self._add_property(shape, SCHEMA.deathDate, "deathDate")
        self._add_property(shape, SCHEMA.deathPlace, "deathPlace", node_kind=SH.IRI)
        
        # OPTIONNEL - Caractéristiques
        self._add_property(shape, SCHEMA.gender, "gender")
        self._add_property(shape, TOLKIEN_PROP.people, "people", node_kind=SH.IRI)
        self._add_property(shape, TOLKIEN_PROP.race, "race", node_kind=SH.IRI)
        
        # OPTIONNEL - Relations familiales
        self._add_property(shape, SCHEMA.parent, "parent", node_kind=SH.IRI)
        self._add_property(shape, SCHEMA.spouse, "spouse", node_kind=SH.IRI)
        self._add_property(shape, SCHEMA.children, "children", node_kind=SH.IRI)
        self._add_property(shape, SCHEMA.sibling, "sibling", node_kind=SH.IRI)
        self._add_property(shape, TOLKIEN_PROP.house, "house", node_kind=SH.IRI)
        
        # OPTIONNEL - Affiliations
        self._add_property(shape, SCHEMA.memberOf, "memberOf", node_kind=SH.IRI)
        self._add_property(shape, TOLKIEN_PROP.affiliation, "affiliation", node_kind=SH.IRI)
        self._add_property(shape, SCHEMA.homeLocation, "homeLocation", node_kind=SH.IRI)
        
        # OPTIONNEL - Autres
        self._add_property(shape, TOLKIEN_PROP.weapon, "weapon", node_kind=SH.IRI)
        self._add_property(shape, TOLKIEN_PROP.steed, "steed", node_kind=SH.IRI)
        self._add_property(shape, TOLKIEN_PROP.notableFor, "notableFor")
        self._add_property(shape, SCHEMA.knowsLanguage, "language")
        
        return shape

    # =========================================================================
    # SHAPE: Location
    # =========================================================================
    
    def create_location_shape(self):
        """Shape pour les lieux (Location infobox)."""
        shape = TOLKIEN_CLASS.LocationShape
        
        self.graph.add((shape, RDF.type, SH.NodeShape))
        self.graph.add((shape, SH.targetClass, TOLKIEN_CLASS.Location))
        self.graph.add((shape, RDFS.label, Literal("Location Shape", lang="en")))
        
        # REQUIS
        self._add_property(shape, SCHEMA.name, "name", min_count=1)
        self._add_property(shape, RDFS.label, "label", min_count=1)
        
        # RECOMMANDÉ
        self._add_property(shape, FOAF.isPrimaryTopicOf, "wikiPage",
                          node_kind=SH.IRI, severity=SH.Warning)
        
        # OPTIONNEL
        self._add_property(shape, SCHEMA.image, "image", node_kind=SH.IRI)
        self._add_property(shape, SCHEMA.description, "description")
        self._add_property(shape, SCHEMA.alternateName, "alternateName")
        self._add_property(shape, SCHEMA.containedInPlace, "containedIn", node_kind=SH.IRI)
        self._add_property(shape, SCHEMA.containsPlace, "contains", node_kind=SH.IRI)
        self._add_property(shape, TOLKIEN_PROP.inhabitants, "inhabitants")
        self._add_property(shape, TOLKIEN_PROP.language, "language")
        
        return shape

    # =========================================================================
    # SHAPE: Kingdom
    # =========================================================================
    
    def create_kingdom_shape(self):
        """Shape pour les royaumes (Kingdom infobox)."""
        shape = TOLKIEN_CLASS.KingdomShape
        
        self.graph.add((shape, RDF.type, SH.NodeShape))
        self.graph.add((shape, SH.targetClass, TOLKIEN_CLASS.Kingdom))
        self.graph.add((shape, RDFS.label, Literal("Kingdom Shape", lang="en")))
        
        # REQUIS
        self._add_property(shape, SCHEMA.name, "name", min_count=1)
        self._add_property(shape, RDFS.label, "label", min_count=1)
        
        # OPTIONNEL
        self._add_property(shape, TOLKIEN_PROP.capital, "capital", node_kind=SH.IRI)
        self._add_property(shape, TOLKIEN_PROP.governance, "governance")
        self._add_property(shape, TOLKIEN_PROP.inhabitants, "inhabitants")
        
        return shape

    # =========================================================================
    # SHAPE: Book
    # =========================================================================
    
    def create_book_shape(self):
        """Shape pour les livres (Book infobox)."""
        shape = TOLKIEN_CLASS.BookShape
        
        self.graph.add((shape, RDF.type, SH.NodeShape))
        self.graph.add((shape, SH.targetClass, TOLKIEN_CLASS.Book))
        self.graph.add((shape, RDFS.label, Literal("Book Shape", lang="en")))
        
        # REQUIS
        self._add_property(shape, SCHEMA.name, "name", min_count=1)
        self._add_property(shape, RDFS.label, "label", min_count=1)
        
        # OPTIONNEL
        self._add_property(shape, SCHEMA.author, "author", node_kind=SH.IRI)
        self._add_property(shape, SCHEMA.datePublished, "datePublished")
        self._add_property(shape, SCHEMA.image, "image", node_kind=SH.IRI)
        self._add_property(shape, SCHEMA.description, "description")
        
        return shape

    # =========================================================================
    # SHAPE: Battle
    # =========================================================================
    
    def create_battle_shape(self):
        """Shape pour les batailles (Battle infobox)."""
        shape = TOLKIEN_CLASS.BattleShape
        
        self.graph.add((shape, RDF.type, SH.NodeShape))
        self.graph.add((shape, SH.targetClass, TOLKIEN_CLASS.Battle))
        self.graph.add((shape, RDFS.label, Literal("Battle Shape", lang="en")))
        
        # REQUIS
        self._add_property(shape, SCHEMA.name, "name", min_count=1)
        self._add_property(shape, RDFS.label, "label", min_count=1)
        
        # OPTIONNEL
        self._add_property(shape, SCHEMA.location, "location", node_kind=SH.IRI)
        self._add_property(shape, SCHEMA.description, "description")
        self._add_property(shape, SCHEMA.image, "image", node_kind=SH.IRI)
        
        return shape

    # =========================================================================
    # SHAPE: Object
    # =========================================================================
    
    def create_object_shape(self):
        """Shape pour les objets (Object infobox)."""
        shape = TOLKIEN_CLASS.ObjectShape
        
        self.graph.add((shape, RDF.type, SH.NodeShape))
        self.graph.add((shape, SH.targetClass, TOLKIEN_CLASS.Object))
        self.graph.add((shape, RDFS.label, Literal("Object Shape", lang="en")))
        
        # REQUIS
        self._add_property(shape, SCHEMA.name, "name", min_count=1)
        self._add_property(shape, RDFS.label, "label", min_count=1)
        
        # OPTIONNEL
        self._add_property(shape, SCHEMA.image, "image", node_kind=SH.IRI)
        self._add_property(shape, SCHEMA.description, "description")
        
        return shape

    # =========================================================================
    # SHAPE: Film
    # =========================================================================
    
    def create_film_shape(self):
        """Shape pour les films (Film infobox)."""
        shape = TOLKIEN_CLASS.FilmShape
        
        self.graph.add((shape, RDF.type, SH.NodeShape))
        self.graph.add((shape, SH.targetClass, TOLKIEN_CLASS.Film))
        self.graph.add((shape, RDFS.label, Literal("Film Shape", lang="en")))
        
        # REQUIS
        self._add_property(shape, SCHEMA.name, "name", min_count=1)
        self._add_property(shape, RDFS.label, "label", min_count=1)
        
        # OPTIONNEL
        self._add_property(shape, SCHEMA.datePublished, "releaseDate")
        self._add_property(shape, SCHEMA.image, "image", node_kind=SH.IRI)
        
        return shape

    # =========================================================================
    # SHAPE: MECCG Card
    # =========================================================================
    
    def create_card_shape(self):
        """Shape pour les cartes MECCG."""
        shape = MECCG_CLASS.CardShape
        
        self.graph.add((shape, RDF.type, SH.NodeShape))
        self.graph.add((shape, SH.targetClass, MECCG_CLASS.Card))
        self.graph.add((shape, RDFS.label, Literal("MECCG Card Shape", lang="en")))
        
        # REQUIS
        self._add_property(shape, RDFS.label, "label", min_count=1)
        
        # OPTIONNEL
        self._add_property(shape, SCHEMA.name, "name")
        self._add_property(shape, MECCG_PROP.cardSet, "cardSet")
        self._add_property(shape, MECCG_PROP.alignment, "alignment")
        
        return shape

    # =========================================================================
    # MÉTHODE PRINCIPALE
    # =========================================================================
    
    def create_all_shapes(self):
        """Crée tous les shapes SHACL."""
        self.create_character_shape()
        self.create_location_shape()
        self.create_kingdom_shape()
        self.create_book_shape()
        self.create_battle_shape()
        self.create_object_shape()
        self.create_race_shape()      # AJOUT
        self.create_weapon_shape()    # AJOUT
        self.create_film_shape()
        self.create_card_shape()
        
        print(f"✓ {len(self.graph)} triplets SHACL générés")
        return self.graph
    # =========================================================================
    # SHAPE: Race
    # =========================================================================
    
    def create_race_shape(self):
        """Shape pour les races/peuples (Race infobox)."""
        shape = TOLKIEN_CLASS.RaceShape
        
        self.graph.add((shape, RDF.type, SH.NodeShape))
        self.graph.add((shape, SH.targetClass, TOLKIEN_CLASS.Race))
        self.graph.add((shape, RDFS.label, Literal("Race Shape", lang="en")))
        
        # REQUIS
        self._add_property(shape, SCHEMA.name, "name", min_count=1)
        self._add_property(shape, RDFS.label, "label", min_count=1)
        
        # OPTIONNEL
        self._add_property(shape, SCHEMA.image, "image", node_kind=SH.IRI)
        self._add_property(shape, SCHEMA.description, "description")
        self._add_property(shape, TOLKIEN_PROP.language, "language")
        
        return shape

    # =========================================================================
    # SHAPE: Weapon
    # =========================================================================
    
    def create_weapon_shape(self):
        """Shape pour les armes (Weapon infobox)."""
        shape = TOLKIEN_CLASS.WeaponShape
        
        self.graph.add((shape, RDF.type, SH.NodeShape))
        self.graph.add((shape, SH.targetClass, TOLKIEN_CLASS.Weapon))
        self.graph.add((shape, RDFS.label, Literal("Weapon Shape", lang="en")))
        
        # REQUIS
        self._add_property(shape, SCHEMA.name, "name", min_count=1)
        self._add_property(shape, RDFS.label, "label", min_count=1)
        
        # OPTIONNEL
        self._add_property(shape, SCHEMA.image, "image", node_kind=SH.IRI)
        self._add_property(shape, SCHEMA.description, "description")
        self._add_property(shape, TOLKIEN_PROP.owner, "owner", node_kind=SH.IRI)
        
        return shape

    def serialize(self, format: str = "turtle") -> str:
        """Sérialise le graphe SHACL."""
        return self.graph.serialize(format=format)
    
    def save(self, filename: str, format: str = "turtle"):
        """Sauvegarde les shapes dans un fichier."""
        self.graph.serialize(destination=filename, format=format)
        print(f"✓ Shapes sauvegardés: {filename}")


# =============================================================================
# VALIDATEUR SHACL
# =============================================================================

class SHACLValidator:
    """Valide un graphe RDF contre les shapes SHACL."""
    
    def __init__(self, shapes_graph: Graph = None, shapes_file: str = None):
        """
        Args:
            shapes_graph: Graphe contenant les shapes SHACL
            shapes_file: Ou chemin vers le fichier Turtle des shapes
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
        Valide un graphe de données.
        
        Returns:
            Tuple (conforms, results_graph, results_text)
        """
        try:
            from pyshacl import validate
            return validate(
                data_graph,
                shacl_graph=self.shapes_graph,
                inference='none',
                abort_on_first=False
            )
        except ImportError:
            print("⚠️  pyshacl non installé. Installez: pip install pyshacl")
            return None, None, "pyshacl not installed"
    
    def validate_and_report(self, data_graph: Graph) -> Dict[str, Any]:
        """Valide et génère un rapport structuré."""
        conforms, results_graph, results_text = self.validate(data_graph)
        
        if conforms is None:
            return {'valid': None, 'error': 'pyshacl not installed'}
        
        report = {
            'valid': conforms,
            'violations': 0,
            'warnings': 0,
            'by_shape': {},
            'by_property': {},
            'details': []
        }
        
        if results_graph:
            for result in results_graph.subjects(RDF.type, SH.ValidationResult):
                severity = str(results_graph.value(result, SH.resultSeverity) or "")
                focus = str(results_graph.value(result, SH.focusNode) or "")
                path = str(results_graph.value(result, SH.resultPath) or "")
                source = str(results_graph.value(result, SH.sourceShape) or "")
                
                is_warning = 'Warning' in severity
                
                detail = {
                    'node': focus.split('/')[-1],
                    'path': path.split('/')[-1].split('#')[-1],
                    'shape': source.split('/')[-1],
                    'severity': 'Warning' if is_warning else 'Violation'
                }
                report['details'].append(detail)
                
                # Compteurs
                if is_warning:
                    report['warnings'] += 1
                else:
                    report['violations'] += 1
                
                # Par propriété
                prop_name = detail['path']
                if prop_name not in report['by_property']:
                    report['by_property'][prop_name] = {'violations': 0, 'warnings': 0}
                if is_warning:
                    report['by_property'][prop_name]['warnings'] += 1
                else:
                    report['by_property'][prop_name]['violations'] += 1
        
        return report
    
    def print_report(self, report: Dict[str, Any], max_items: int = 10):
        """Affiche le rapport de validation."""
        print("\n" + "=" * 60)
        print(" RAPPORT DE VALIDATION SHACL")
        print("=" * 60)
        
        if report.get('valid') is None:
            print(f"\n⚠️  Erreur: {report.get('error')}")
            print("   Installez: pip install pyshacl")
            return
        
        print(f"\n📊 Résumé:")
        print(f"   Violations: {report['violations']}")
        print(f"   Warnings: {report['warnings']}")
        
        if report['valid'] and report['warnings'] == 0:
            print("\n✅ Graphe VALIDE - Aucune erreur")
            return
        
        status = "✅ VALIDE (avec warnings)" if report['valid'] else "❌ INVALIDE"
        print(f"\n{status}")
        
        # Par propriété
        if report['by_property']:
            print(f"\n📋 Par propriété:")
            for prop, counts in sorted(report['by_property'].items(), 
                                       key=lambda x: -(x[1]['violations'] + x[1]['warnings'])):
                v, w = counts['violations'], counts['warnings']
                parts = []
                if v > 0: parts.append(f"{v} violations")
                if w > 0: parts.append(f"{w} warnings")
                print(f"   {prop}: {', '.join(parts)}")
        
        # Détails
        if report['details']:
            violations = [d for d in report['details'] if d['severity'] == 'Violation']
            warnings = [d for d in report['details'] if d['severity'] == 'Warning']
            
            if violations:
                print(f"\n🔴 Violations (max {max_items}):")
                for i, d in enumerate(violations[:max_items], 1):
                    print(f"   {i}. {d['node']} - {d['path']}")
                if len(violations) > max_items:
                    print(f"   ... et {len(violations) - max_items} autres")
            
            if warnings and len(warnings) <= max_items:
                print(f"\n🟡 Warnings (max {max_items}):")
                for i, d in enumerate(warnings[:max_items], 1):
                    print(f"   {i}. {d['node']} - {d['path']}")
                if len(warnings) > max_items:
                    print(f"   ... et {len(warnings) - max_items} autres")


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def create_shapes_file(filename: str = "tolkien_shapes.ttl") -> SHACLGenerator:
    """Crée et sauvegarde les shapes SHACL."""
    gen = SHACLGenerator()
    gen.create_all_shapes()
    gen.save(filename)
    return gen


def validate_kg(kg_file: str, shapes_file: str = "tolkien_shapes.ttl") -> Dict[str, Any]:
    """
    Valide un Knowledge Graph contre les shapes SHACL.
    
    Args:
        kg_file: Fichier du KG (Turtle)
        shapes_file: Fichier des shapes SHACL
        
    Returns:
        Rapport de validation
    """
    print(f"📂 Chargement du KG: {kg_file}")
    data = Graph()
    data.parse(kg_file, format="turtle")
    print(f"   {len(data)} triplets")
    
    print(f"📂 Chargement des shapes: {shapes_file}")
    validator = SHACLValidator(shapes_file=shapes_file)
    
    print("🔍 Validation en cours...")
    report = validator.validate_and_report(data)
    validator.print_report(report)
    
    return report


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    # Générer les shapes
    gen = SHACLGenerator()
    gen.create_all_shapes()
    gen.save("tolkien_shapes.ttl")
    
    print("\n📄 Aperçu du fichier généré:")
    print("-" * 40)
    print(gen.serialize()[:2000])
    print("...")