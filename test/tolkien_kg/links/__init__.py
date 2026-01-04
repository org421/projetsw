"""
Extracteur de liens entre pages du wiki
Génère des triplets RDF pour les relations entre entités
"""

from typing import Dict, List, Any, Set, Tuple
from urllib.parse import quote


class LinkExtractor:
    """
    Extrait les liens entre pages du wiki et génère des relations RDF.
    """
    
    # Namespaces à ignorer (pas des entités du monde Tolkien)
    IGNORED_NAMESPACES = {
        'Category',
        'File', 
        'Template',
        'User',
        'Talk',
        'Help',
        'MediaWiki',
        'Special',
        'Portal',
    }
    
    # Pages spéciales à ignorer
    IGNORED_PAGES = {
        'Main Page',
        'Tolkien Gateway',
        'disambiguation',
        'Disambig',
    }
    
    def __init__(self, client):
        """
        Args:
            client: MediaWikiClient instance
        """
        self.client = client
        self._page_cache = {}  # Cache pour éviter les requêtes répétées
    
    def is_valid_link(self, link: Dict[str, Any]) -> bool:
        """
        Vérifie si un lien pointe vers une entité valide.
        
        Args:
            link: Dictionnaire avec 'ns' (namespace) et 'title'
            
        Returns:
            True si le lien est valide
        """
        # Vérifier le namespace (0 = articles principaux)
        ns = link.get('ns', 0)
        if ns != 0:
            return False
        
        title = link.get('title', '')
        
        # Vérifier les pages ignorées
        for ignored in self.IGNORED_PAGES:
            if ignored.lower() in title.lower():
                return False
        
        # Vérifier les préfixes de namespace dans le titre
        for ns_prefix in self.IGNORED_NAMESPACES:
            if title.startswith(f"{ns_prefix}:"):
                return False
        
        return True
    
    def extract_links_from_page(self, title: str) -> List[str]:
        """
        Extrait tous les liens valides d'une page.
        
        Args:
            title: Titre de la page source
            
        Returns:
            Liste des titres des pages cibles
        """
        links = self.client.get_page_links(title)
        
        valid_links = []
        for link in links:
            if self.is_valid_link(link):
                target_title = link.get('title', '')
                if target_title and target_title != title:  # Pas d'auto-liens
                    valid_links.append(target_title)
        
        return valid_links
    
    def extract_images_from_page(self, title: str) -> List[str]:
        """
        Extrait toutes les images d'une page.
        
        Args:
            title: Titre de la page
            
        Returns:
            Liste des noms de fichiers images
        """
        images = self.client.get_page_images(title)
        
        # Filtrer les images de navigation/templates
        valid_images = []
        for image in images:
            # Ignorer les icônes et images de template
            if not any(skip in image.lower() for skip in ['icon', 'logo', 'button', 'arrow', 'bullet']):
                valid_images.append(image)
        
        return valid_images
    
    def extract_external_links_from_page(self, title: str) -> Dict[str, List[str]]:
        """
        Extrait les liens externes d'une page, classés par domaine.
        
        Args:
            title: Titre de la page
            
        Returns:
            Dictionnaire {domaine: [urls]}
        """
        ext_links = self.client.get_page_external_links(title)
        
        categorized = {
            'wikipedia': [],
            'dbpedia': [],
            'imdb': [],
            'other': []
        }
        
        for url in ext_links:
            url_lower = url.lower()
            if 'wikipedia.org' in url_lower:
                categorized['wikipedia'].append(url)
            elif 'dbpedia.org' in url_lower:
                categorized['dbpedia'].append(url)
            elif 'imdb.com' in url_lower:
                categorized['imdb'].append(url)
            else:
                categorized['other'].append(url)
        
        return categorized
    
    def extract_all_relations(self, title: str) -> Dict[str, Any]:
        """
        Extrait toutes les relations d'une page (liens, images, liens externes).
        
        Args:
            title: Titre de la page
            
        Returns:
            Dictionnaire avec toutes les relations
        """
        return {
            'source': title,
            'internal_links': self.extract_links_from_page(title),
            'images': self.extract_images_from_page(title),
            'external_links': self.extract_external_links_from_page(title)
        }
    
    def build_link_graph(self, pages: List[str], show_progress: bool = True) -> Dict[str, List[str]]:
        """
        Construit un graphe de liens entre plusieurs pages.
        
        Args:
            pages: Liste des titres de pages
            show_progress: Afficher la progression
            
        Returns:
            Dictionnaire {page_source: [pages_cibles]}
        """
        graph = {}
        page_set = set(pages)  # Pour vérifier rapidement si une cible existe
        
        for i, page in enumerate(pages):
            if show_progress and (i + 1) % 100 == 0:
                print(f"  Traitement des liens: {i + 1}/{len(pages)}")
            
            links = self.extract_links_from_page(page)
            
            # Ne garder que les liens vers des pages qu'on a dans notre KG
            valid_links = [link for link in links if link in page_set]
            
            if valid_links:
                graph[page] = valid_links
        
        return graph
    
    def get_wikipedia_url(self, title: str) -> str:
        """
        Cherche l'URL Wikipedia correspondante dans les liens externes.
        
        Args:
            title: Titre de la page Tolkien Gateway
            
        Returns:
            URL Wikipedia ou None
        """
        ext_links = self.extract_external_links_from_page(title)
        
        wikipedia_links = ext_links.get('wikipedia', [])
        
        # Chercher un lien Wikipedia en anglais de préférence
        for url in wikipedia_links:
            if 'en.wikipedia.org' in url:
                return url
        
        # Sinon retourner le premier lien Wikipedia
        return wikipedia_links[0] if wikipedia_links else None


def add_links_to_rdf(rdf_gen, link_extractor, pages: List[str], 
                     limit_per_page: int = None, show_progress: bool = True):
    """
    Ajoute les liens entre pages au graphe RDF.
    
    Args:
        rdf_gen: RDFGenerator instance
        link_extractor: LinkExtractor instance
        pages: Liste des titres de pages à traiter
        limit_per_page: Limite de liens par page (None = tous)
        show_progress: Afficher la progression
    """
    from rdflib import URIRef, Namespace
    from rdflib.namespace import RDFS, FOAF
    
    TOLKIEN = Namespace("https://tolkiengateway.net/wiki/")
    TOLKIEN_PROP = Namespace("https://tolkiengateway.net/wiki/Property:")
    SCHEMA = Namespace("http://schema.org/")
    
    page_set = set(pages)
    total_links = 0
    total_images = 0
    
    for i, page in enumerate(pages):
        if show_progress and (i + 1) % 100 == 0:
            print(f"  Extraction des liens: {i + 1}/{len(pages)} pages")
        
        try:
            # Extraire les liens internes
            links = link_extractor.extract_links_from_page(page)
            
            # Limiter si demandé
            if limit_per_page:
                links = links[:limit_per_page]
            
            # Créer l'URI source
            source_uri = TOLKIEN[quote(page.replace(" ", "_"), safe="")]
            
            for target in links:
                # Ne créer des liens que vers des pages qu'on a dans notre KG
                if target in page_set:
                    target_uri = TOLKIEN[quote(target.replace(" ", "_"), safe="")]
                    
                    # Ajouter le triplet de relation
                    rdf_gen.graph.add((source_uri, TOLKIEN_PROP.relatedTo, target_uri))
                    rdf_gen.graph.add((source_uri, SCHEMA.mentions, target_uri))
                    total_links += 1
            
            # Extraire et ajouter les images
            images = link_extractor.extract_images_from_page(page)
            for image in images[:3]:  # Limiter à 3 images par page
                image_url = f"https://tolkiengateway.net/wiki/File:{quote(image)}"
                rdf_gen.graph.add((source_uri, SCHEMA.image, URIRef(image_url)))
                rdf_gen.graph.add((source_uri, FOAF.depiction, URIRef(image_url)))
                total_images += 1
                
        except Exception as e:
            if show_progress:
                print(f"    [ERR] {page}: {e}")
    
    if show_progress:
        print(f"\n  Total liens ajoutés: {total_links}")
        print(f"  Total images ajoutées: {total_images}")
    
    return total_links, total_images


def add_wikipedia_alignments(rdf_gen, link_extractor, pages: List[str],
                             show_progress: bool = True):
    """
    Ajoute les alignements owl:sameAs vers Wikipedia/DBpedia.
    
    Args:
        rdf_gen: RDFGenerator instance
        link_extractor: LinkExtractor instance
        pages: Liste des titres de pages
        show_progress: Afficher la progression
    """
    from rdflib import URIRef, Namespace
    from rdflib.namespace import OWL
    
    TOLKIEN = Namespace("https://tolkiengateway.net/wiki/")
    DBPEDIA = Namespace("http://dbpedia.org/resource/")
    
    total_alignments = 0
    
    for i, page in enumerate(pages):
        if show_progress and (i + 1) % 100 == 0:
            print(f"  Recherche alignements: {i + 1}/{len(pages)} pages")
        
        try:
            wikipedia_url = link_extractor.get_wikipedia_url(page)
            
            if wikipedia_url:
                source_uri = TOLKIEN[quote(page.replace(" ", "_"), safe="")]
                
                # Extraire le titre Wikipedia de l'URL
                # Ex: https://en.wikipedia.org/wiki/Gandalf -> Gandalf
                if '/wiki/' in wikipedia_url:
                    wiki_title = wikipedia_url.split('/wiki/')[-1]
                    
                    # Créer l'URI DBpedia correspondante
                    dbpedia_uri = DBPEDIA[wiki_title]
                    
                    # Ajouter owl:sameAs
                    rdf_gen.graph.add((source_uri, OWL.sameAs, dbpedia_uri))
                    rdf_gen.graph.add((source_uri, OWL.sameAs, URIRef(wikipedia_url)))
                    
                    total_alignments += 1
                    
        except Exception as e:
            pass  # Ignorer les erreurs silencieusement
    
    if show_progress:
        print(f"\n  Total alignements Wikipedia/DBpedia: {total_alignments}")
    
    return total_alignments
