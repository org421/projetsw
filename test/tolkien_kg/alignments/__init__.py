"""
Module d'alignements externes - VERSION AMÉLIORÉE
Crée des triplets owl:sameAs vers DBpedia, YAGO et Wikidata
avec VÉRIFICATION que les ressources existent réellement.

Améliorations:
1. Vérifie si DBpedia/YAGO existent via HTTP HEAD
2. Utilise l'API MediaWiki externallinks pour trouver les vrais liens Wikipedia
3. Cache les résultats pour éviter les requêtes répétées
"""

import requests
import time
import json
import os
from typing import Dict, List, Any, Optional, Set
from urllib.parse import quote, unquote
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, FOAF, RDFS


# =============================================================================
# NAMESPACES
# =============================================================================

TOLKIEN = Namespace("https://tolkiengateway.net/wiki/")
DBPEDIA = Namespace("http://dbpedia.org/resource/")
YAGO = Namespace("http://yago-knowledge.org/resource/")
WIKIDATA = Namespace("http://www.wikidata.org/entity/")
WIKIPEDIA = Namespace("https://en.wikipedia.org/wiki/")


# =============================================================================
# CACHE PERSISTANT
# =============================================================================

class AlignmentCache:
    """Cache persistant pour éviter les requêtes répétées."""
    
    def __init__(self, cache_file: str = "alignment_cache.json"):
        self.cache_file = cache_file
        self.cache = {
            'dbpedia': {},      # entity_name -> True/False (existe ou non)
            'yago': {},         # entity_name -> True/False
            'wikidata': {},     # entity_name -> QID ou None
            'wikipedia': {},    # entity_name -> wikipedia_url ou None
        }
        self._load()
    
    def _load(self):
        """Charge le cache depuis le fichier."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    for key in self.cache:
                        if key in loaded:
                            self.cache[key] = loaded[key]
            except:
                pass
    
    def save(self):
        """Sauvegarde le cache dans le fichier."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def get(self, source: str, entity_name: str) -> Optional[Any]:
        """Récupère une valeur du cache."""
        return self.cache.get(source, {}).get(entity_name)
    
    def set(self, source: str, entity_name: str, value: Any):
        """Stocke une valeur dans le cache."""
        if source not in self.cache:
            self.cache[source] = {}
        self.cache[source][entity_name] = value
    
    def has(self, source: str, entity_name: str) -> bool:
        """Vérifie si une entrée existe dans le cache."""
        return entity_name in self.cache.get(source, {})


# =============================================================================
# VÉRIFICATEUR DE RESSOURCES
# =============================================================================

class ResourceVerifier:
    """
    Vérifie si les ressources externes existent réellement.
    Utilise HTTP HEAD pour minimiser la bande passante.
    """
    
    def __init__(self, cache: AlignmentCache):
        self.cache = cache
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TolkienKGBot/1.0 (Semantic Web Project; Educational Purpose)',
            'Accept': 'application/rdf+xml, text/turtle, application/json'
        })
        self.last_request = 0
        self.request_delay = 0.2  # 200ms entre les requêtes
    
    def _wait(self):
        """Rate limiting."""
        elapsed = time.time() - self.last_request
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        self.last_request = time.time()
    
    def _make_uri_name(self, entity_name: str) -> str:
        """Convertit le nom en format URI."""
        return quote(entity_name.replace(' ', '_'), safe='')
    
    def check_dbpedia(self, entity_name: str) -> bool:
        """
        Vérifie si une ressource DBpedia existe.
        
        Args:
            entity_name: Nom de l'entité
            
        Returns:
            True si la ressource existe
        """
        # Vérifier le cache
        if self.cache.has('dbpedia', entity_name):
            return self.cache.get('dbpedia', entity_name)
        
        self._wait()
        
        uri_name = self._make_uri_name(entity_name)
        url = f"http://dbpedia.org/resource/{uri_name}"
        
        try:
            # Utiliser HEAD pour vérifier l'existence
            response = self.session.head(
                url,
                allow_redirects=True,
                timeout=5
            )
            
            # DBpedia retourne 200 si la ressource existe
            # et 303 redirect vers la page de données
            exists = response.status_code in [200, 301, 302, 303]
            
            # Vérification supplémentaire: essayer de récupérer des données
            if exists:
                self._wait()
                data_url = f"http://dbpedia.org/data/{uri_name}.json"
                data_response = self.session.get(data_url, timeout=5)
                # Vérifier que la ressource a du contenu
                if data_response.status_code == 200:
                    try:
                        data = data_response.json()
                        # Vérifier que la ressource principale existe dans les données
                        resource_key = f"http://dbpedia.org/resource/{uri_name}"
                        exists = resource_key in data or len(data) > 0
                    except:
                        exists = False
                else:
                    exists = False
            
            self.cache.set('dbpedia', entity_name, exists)
            return exists
            
        except Exception as e:
            self.cache.set('dbpedia', entity_name, False)
            return False
    
    def check_yago(self, entity_name: str) -> bool:
        """
        Vérifie si une ressource YAGO existe.
        
        Args:
            entity_name: Nom de l'entité
            
        Returns:
            True si la ressource existe
        """
        # Vérifier le cache
        if self.cache.has('yago', entity_name):
            return self.cache.get('yago', entity_name)
        
        self._wait()
        
        uri_name = self._make_uri_name(entity_name)
        url = f"http://yago-knowledge.org/resource/{uri_name}"
        
        try:
            response = self.session.head(
                url,
                allow_redirects=True,
                timeout=5
            )
            
            exists = response.status_code in [200, 301, 302, 303]
            self.cache.set('yago', entity_name, exists)
            return exists
            
        except Exception as e:
            self.cache.set('yago', entity_name, False)
            return False


# =============================================================================
# CLIENT WIKIDATA AMÉLIORÉ
# =============================================================================

class WikidataClient:
    """
    Récupère les QIDs Wikidata avec vérification.
    """
    
    API_URL = "https://www.wikidata.org/w/api.php"
    
    def __init__(self, cache: AlignmentCache):
        self.cache = cache
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TolkienKGBot/1.0 (Semantic Web Project)'
        })
        self.last_request = 0
    
    def _wait(self):
        """Rate limiting."""
        elapsed = time.time() - self.last_request
        if elapsed < 0.1:
            time.sleep(0.1 - elapsed)
        self.last_request = time.time()
    
    def get_qid(self, entity_name: str, wikipedia_title: str = None) -> Optional[str]:
        """
        Récupère le QID Wikidata.
        
        Args:
            entity_name: Nom de l'entité
            wikipedia_title: Titre Wikipedia si connu (prioritaire)
            
        Returns:
            QID (ex: "Q177858") ou None
        """
        # Vérifier le cache
        if self.cache.has('wikidata', entity_name):
            return self.cache.get('wikidata', entity_name)
        
        self._wait()
        
        # Utiliser le titre Wikipedia si fourni
        wiki_title = wikipedia_title or entity_name.replace(' ', '_')
        
        try:
            # Méthode 1: Chercher via le titre Wikipedia anglais
            response = self.session.get(self.API_URL, params={
                'action': 'wbgetentities',
                'sites': 'enwiki',
                'titles': wiki_title,
                'props': 'info',
                'format': 'json'
            }, timeout=10)
            
            data = response.json()
            
            for qid, entity_data in data.get('entities', {}).items():
                if qid.startswith('Q') and 'missing' not in entity_data:
                    self.cache.set('wikidata', entity_name, qid)
                    return qid
        except:
            pass
        
        # Méthode 2: Recherche Wikidata par label (Tolkien-specific)
        try:
            self._wait()
            
            # Recherche avec contexte Tolkien
            search_terms = [
                entity_name,
                f"{entity_name} (Middle-earth)",
                f"{entity_name} (Tolkien)",
            ]
            
            for search_term in search_terms:
                response = self.session.get(self.API_URL, params={
                    'action': 'wbsearchentities',
                    'search': search_term,
                    'language': 'en',
                    'limit': 5,
                    'format': 'json'
                }, timeout=10)
                
                data = response.json()
                results = data.get('search', [])
                
                for result in results:
                    qid = result.get('id')
                    description = result.get('description', '').lower()
                    
                    # Vérifier si c'est lié à Tolkien/Middle-earth
                    tolkien_keywords = ['tolkien', 'middle-earth', 'lord of the rings', 
                                       'hobbit', 'silmarillion', 'fictional', 'character']
                    
                    if qid and qid.startswith('Q'):
                        if any(kw in description for kw in tolkien_keywords):
                            self.cache.set('wikidata', entity_name, qid)
                            return qid
                
                self._wait()
            
            # Si rien trouvé avec contexte Tolkien, prendre le premier résultat
            response = self.session.get(self.API_URL, params={
                'action': 'wbsearchentities',
                'search': entity_name,
                'language': 'en',
                'limit': 1,
                'format': 'json'
            }, timeout=10)
            
            data = response.json()
            results = data.get('search', [])
            
            if results:
                qid = results[0].get('id')
                if qid and qid.startswith('Q'):
                    self.cache.set('wikidata', entity_name, qid)
                    return qid
                    
        except:
            pass
        
        self.cache.set('wikidata', entity_name, None)
        return None


# =============================================================================
# EXTRACTEUR DE LIENS WIKIPEDIA VIA API MEDIAWIKI
# =============================================================================

class WikipediaLinkExtractor:
    """
    Extrait les liens Wikipedia depuis les pages du Tolkien Gateway
    en utilisant l'API MediaWiki (prop=externallinks).
    """
    
    API_URL = "https://tolkiengateway.net/w/api.php"
    
    def __init__(self, cache: AlignmentCache, mediawiki_client=None):
        self.cache = cache
        self.client = mediawiki_client
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TolkienKGBot/1.0 (Semantic Web Project)'
        })
        self.last_request = 0
    
    def _wait(self):
        """Rate limiting."""
        elapsed = time.time() - self.last_request
        if elapsed < 0.3:
            time.sleep(0.3 - elapsed)
        self.last_request = time.time()
    
    def get_wikipedia_link(self, page_title: str) -> Optional[str]:
        """
        Récupère le lien Wikipedia depuis une page Tolkien Gateway.
        
        Args:
            page_title: Titre de la page sur Tolkien Gateway
            
        Returns:
            URL Wikipedia ou None
        """
        # Vérifier le cache
        if self.cache.has('wikipedia', page_title):
            return self.cache.get('wikipedia', page_title)
        
        self._wait()
        
        try:
            # Utiliser l'API parse avec prop=externallinks
            response = self.session.get(self.API_URL, params={
                'action': 'parse',
                'page': page_title,
                'prop': 'externallinks',
                'format': 'json'
            }, timeout=10)
            
            data = response.json()
            
            if 'parse' in data and 'externallinks' in data['parse']:
                external_links = data['parse']['externallinks']
                
                # Chercher les liens Wikipedia
                for link in external_links:
                    link_lower = link.lower()
                    
                    # Patterns de liens Wikipedia
                    if 'en.wikipedia.org/wiki/' in link_lower:
                        # Extraire le titre Wikipedia
                        self.cache.set('wikipedia', page_title, link)
                        return link
                    
                    elif 'wikipedia.org/wiki/' in link_lower and '/en.' not in link_lower:
                        # Autre langue Wikipedia, moins prioritaire mais acceptable
                        if not self.cache.has('wikipedia', page_title):
                            self.cache.set('wikipedia', page_title, link)
            
            # Vérifier si on a trouvé quelque chose
            cached = self.cache.get('wikipedia', page_title)
            if cached:
                return cached
            
            self.cache.set('wikipedia', page_title, None)
            return None
            
        except Exception as e:
            self.cache.set('wikipedia', page_title, None)
            return None
    
    def extract_wikipedia_title(self, wikipedia_url: str) -> Optional[str]:
        """
        Extrait le titre d'article depuis une URL Wikipedia.
        
        Args:
            wikipedia_url: URL Wikipedia complète
            
        Returns:
            Titre de l'article (décodé)
        """
        if not wikipedia_url:
            return None
        
        try:
            # Pattern: https://en.wikipedia.org/wiki/Article_Title
            if '/wiki/' in wikipedia_url:
                title = wikipedia_url.split('/wiki/')[-1]
                # Nettoyer les ancres et paramètres
                title = title.split('#')[0].split('?')[0]
                # Décoder l'URL
                return unquote(title)
        except:
            pass
        
        return None


# =============================================================================
# GÉNÉRATEUR D'ALIGNEMENTS AMÉLIORÉ
# =============================================================================

class ExternalAlignmentGenerator:
    """
    Génère des alignements owl:sameAs VÉRIFIÉS.
    
    Améliorations par rapport à la version précédente:
    1. Vérifie si DBpedia/YAGO existent avant de créer le lien
    2. Utilise l'API externallinks pour trouver les vrais liens Wikipedia
    3. Cache les résultats pour éviter les requêtes répétées
    """
    
    def __init__(self, mediawiki_client=None, cache_file: str = "alignment_cache.json"):
        """
        Args:
            mediawiki_client: Instance de MediaWikiClient
            cache_file: Fichier de cache pour les résultats
        """
        self.client = mediawiki_client
        self.cache = AlignmentCache(cache_file)
        self.verifier = ResourceVerifier(self.cache)
        self.wikidata = WikidataClient(self.cache)
        self.wikipedia_extractor = WikipediaLinkExtractor(self.cache, mediawiki_client)
        
        self.graph = Graph()
        self._bind_namespaces()
        
        # Statistiques détaillées
        self.stats = {
            'processed': 0,
            'dbpedia_checked': 0,
            'dbpedia_verified': 0,
            'yago_checked': 0,
            'yago_verified': 0,
            'wikidata_found': 0,
            'wikipedia_found': 0,
            'total_alignments': 0,
        }
    
    def _bind_namespaces(self):
        """Bind namespaces."""
        self.graph.bind("tolkien", TOLKIEN)
        self.graph.bind("owl", OWL)
        self.graph.bind("foaf", FOAF)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("dbpedia", DBPEDIA)
        self.graph.bind("yago", YAGO)
        self.graph.bind("wikidata", WIKIDATA)
    
    def _make_uri_name(self, entity_name: str) -> str:
        """Convertit le nom en format URI."""
        return quote(entity_name.replace(' ', '_'), safe='')
    
    def align_entity(self, entity_name: str, verify_external: bool = True) -> int:
        """
        Crée les alignements VÉRIFIÉS pour une entité.
        
        Args:
            entity_name: Nom de l'entité
            verify_external: Si True, vérifie que les ressources externes existent
            
        Returns:
            Nombre d'alignements créés
        """
        self.stats['processed'] += 1
        count = 0
        
        uri_name = self._make_uri_name(entity_name)
        tolkien_uri = TOLKIEN[uri_name]
        
        # 1. Chercher le lien Wikipedia via l'API externallinks
        wikipedia_url = self.wikipedia_extractor.get_wikipedia_link(entity_name)
        wikipedia_title = None
        
        if wikipedia_url:
            self.stats['wikipedia_found'] += 1
            wikipedia_title = self.wikipedia_extractor.extract_wikipedia_title(wikipedia_url)
            
            # Ajouter le lien foaf:isPrimaryTopicOf
            self.graph.add((tolkien_uri, FOAF.isPrimaryTopicOf, URIRef(wikipedia_url)))
            count += 1
        
        # 2. DBpedia - vérifier si la ressource existe
        self.stats['dbpedia_checked'] += 1
        
        # Utiliser le titre Wikipedia si disponible, sinon le nom de l'entité
        dbpedia_name = wikipedia_title or entity_name
        dbpedia_uri_name = self._make_uri_name(dbpedia_name.replace('_', ' '))
        
        if verify_external:
            dbpedia_exists = self.verifier.check_dbpedia(dbpedia_name.replace('_', ' '))
        else:
            dbpedia_exists = True  # Mode non vérifié
        
        if dbpedia_exists:
            self.stats['dbpedia_verified'] += 1
            dbpedia_uri = DBPEDIA[dbpedia_uri_name]
            self.graph.add((tolkien_uri, OWL.sameAs, dbpedia_uri))
            count += 1
        
        # 3. YAGO - vérifier si la ressource existe
        self.stats['yago_checked'] += 1
        
        yago_name = wikipedia_title or entity_name
        yago_uri_name = self._make_uri_name(yago_name.replace('_', ' '))
        
        if verify_external:
            yago_exists = self.verifier.check_yago(yago_name.replace('_', ' '))
        else:
            yago_exists = True
        
        if yago_exists:
            self.stats['yago_verified'] += 1
            yago_uri = YAGO[yago_uri_name]
            self.graph.add((tolkien_uri, OWL.sameAs, yago_uri))
            count += 1
        
        # 4. Wikidata - récupérer le QID
        qid = self.wikidata.get_qid(entity_name, wikipedia_title)
        
        if qid:
            self.stats['wikidata_found'] += 1
            wikidata_uri = WIKIDATA[qid]
            self.graph.add((tolkien_uri, OWL.sameAs, wikidata_uri))
            count += 1
        
        self.stats['total_alignments'] += count
        return count
    
    def align_entities(self, entity_names: List[str], verbose: bool = True,
                       verify_external: bool = True) -> int:
        """
        Aligne un lot d'entités.
        
        Args:
            entity_names: Liste des noms d'entités
            verbose: Afficher la progression
            verify_external: Vérifier l'existence des ressources externes
            
        Returns:
            Nombre total d'alignements
        """
        total = 0
        
        if verbose:
            print(f"  🔗 Alignement de {len(entity_names)} entités...")
            if verify_external:
                print(f"     (avec vérification des ressources externes)")
            else:
                print(f"     (sans vérification - mode rapide)")
        
        for i, name in enumerate(entity_names):
            if verbose and (i + 1) % 20 == 0:
                print(f"     {i + 1}/{len(entity_names)} traités...")
                # Sauvegarder le cache périodiquement
                self.cache.save()
            
            try:
                total += self.align_entity(name, verify_external)
            except Exception as e:
                pass
        
        # Sauvegarder le cache final
        self.cache.save()
        
        if verbose:
            print(f"\n  📊 Résultats:")
            print(f"     Entités traitées: {self.stats['processed']}")
            print(f"     Wikipedia trouvés: {self.stats['wikipedia_found']}")
            print(f"     DBpedia vérifiés: {self.stats['dbpedia_verified']}/{self.stats['dbpedia_checked']}")
            print(f"     YAGO vérifiés: {self.stats['yago_verified']}/{self.stats['yago_checked']}")
            print(f"     Wikidata trouvés: {self.stats['wikidata_found']}")
            print(f"     Total alignements: {self.stats['total_alignments']}")
        
        return total
    
    def add_to_graph(self, target_graph: Graph) -> int:
        """Ajoute les alignements à un graphe cible."""
        count = 0
        for triple in self.graph:
            target_graph.add(triple)
            count += 1
        return count
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques."""
        return self.stats.copy()
    
    def save(self, filename: str, format: str = "turtle"):
        """Sauvegarde les alignements."""
        self.graph.serialize(destination=filename, format=format)
        print(f"  ✓ Sauvegardé: {filename} ({len(self.graph)} triplets)")


# =============================================================================
# FONCTION UTILITAIRE POUR main.py (COMPATIBLE)
# =============================================================================

def add_alignments_to_kg(kg_graph: Graph, client, entity_names: List[str],
                          verbose: bool = True, verify: bool = True) -> int:
    """
    Ajoute des alignements VÉRIFIÉS à un KG.
    
    Args:
        kg_graph: Graphe RDF cible
        client: MediaWikiClient
        entity_names: Liste des entités à aligner
        verbose: Afficher la progression
        verify: Vérifier l'existence des ressources (True = plus lent mais précis)
        
    Returns:
        Nombre d'alignements ajoutés
    """
    gen = ExternalAlignmentGenerator(mediawiki_client=client)
    gen.align_entities(list(entity_names), verbose=verbose, verify_external=verify)
    return gen.add_to_graph(kg_graph)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'ExternalAlignmentGenerator',
    'WikidataClient',
    'WikipediaLinkExtractor',
    'ResourceVerifier',
    'AlignmentCache',
    'add_alignments_to_kg',
]