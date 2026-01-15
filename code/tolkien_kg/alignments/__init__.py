"""
Module d'alignements externes vers DBpedia, YAGO et Wikidata.
Vérifie l'existence des ressources avant de créer les liens owl:sameAs.
"""

import requests
import time
import json
import os
from typing import Dict, List, Any, Optional, Set
from urllib.parse import quote, unquote
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, FOAF, RDFS


TOLKIEN = Namespace("https://tolkiengateway.net/wiki/")
DBPEDIA = Namespace("http://dbpedia.org/resource/")
YAGO = Namespace("http://yago-knowledge.org/resource/")
WIKIDATA = Namespace("http://www.wikidata.org/entity/")
WIKIPEDIA = Namespace("https://en.wikipedia.org/wiki/")


class AlignmentCache:
    """Gère le cache persistant des résultats d'alignement."""
    
    def __init__(self, cache_file: str = "alignment_cache.json"):
        self.cache_file = cache_file
        self.cache = {
            'dbpedia': {},
            'yago': {},
            'wikidata': {},
            'wikipedia': {},
        }
        self._load()
    
    def _load(self):
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
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def get(self, source: str, entity_name: str) -> Optional[Any]:
        return self.cache.get(source, {}).get(entity_name)
    
    def set(self, source: str, entity_name: str, value: Any):
        if source not in self.cache:
            self.cache[source] = {}
        self.cache[source][entity_name] = value
    
    def has(self, source: str, entity_name: str) -> bool:
        return entity_name in self.cache.get(source, {})


class ResourceVerifier:
    """Vérifie l'existence des ressources DBpedia et YAGO via HTTP HEAD."""
    
    def __init__(self, cache: AlignmentCache):
        self.cache = cache
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TolkienKGBot/1.0 (Semantic Web Project; Educational Purpose)',
            'Accept': 'application/rdf+xml, text/turtle, application/json'
        })
        self.last_request = 0
        self.request_delay = 0.2
    
    def _wait(self):
        elapsed = time.time() - self.last_request
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        self.last_request = time.time()
    
    def _make_uri_name(self, entity_name: str) -> str:
        return quote(entity_name.replace(' ', '_'), safe='')
    
    def check_dbpedia(self, entity_name: str) -> bool:
        """Vérifie si une ressource DBpedia existe."""
        if self.cache.has('dbpedia', entity_name):
            return self.cache.get('dbpedia', entity_name)
        
        self._wait()
        
        uri_name = self._make_uri_name(entity_name)
        url = f"http://dbpedia.org/resource/{uri_name}"
        
        try:
            response = self.session.head(
                url,
                allow_redirects=True,
                timeout=5
            )
            
            exists = response.status_code in [200, 301, 302, 303]
            
            if exists:
                self._wait()
                data_url = f"http://dbpedia.org/data/{uri_name}.json"
                data_response = self.session.get(data_url, timeout=5)
                if data_response.status_code == 200:
                    try:
                        data = data_response.json()
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
        """Vérifie si une ressource YAGO existe."""
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


class WikidataClient:
    """Récupère les QIDs Wikidata via l'API."""
    
    API_URL = "https://www.wikidata.org/w/api.php"
    
    def __init__(self, cache: AlignmentCache):
        self.cache = cache
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TolkienKGBot/1.0 (Semantic Web Project)'
        })
        self.last_request = 0
    
    def _wait(self):
        elapsed = time.time() - self.last_request
        if elapsed < 0.1:
            time.sleep(0.1 - elapsed)
        self.last_request = time.time()
    
    def get_qid(self, entity_name: str, wikipedia_title: str = None) -> Optional[str]:
        """Récupère le QID Wikidata pour une entité."""
        if self.cache.has('wikidata', entity_name):
            return self.cache.get('wikidata', entity_name)
        
        self._wait()
        
        wiki_title = wikipedia_title or entity_name.replace(' ', '_')
        
        try:
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
        
        try:
            self._wait()
            
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
                    
                    tolkien_keywords = ['tolkien', 'middle-earth', 'lord of the rings', 
                                       'hobbit', 'silmarillion', 'fictional', 'character']
                    
                    if qid and qid.startswith('Q'):
                        if any(kw in description for kw in tolkien_keywords):
                            self.cache.set('wikidata', entity_name, qid)
                            return qid
                
                self._wait()
            
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


class WikipediaLinkExtractor:
    """Extrait les liens Wikipedia depuis les pages Tolkien Gateway via l'API MediaWiki."""
    
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
        elapsed = time.time() - self.last_request
        if elapsed < 0.3:
            time.sleep(0.3 - elapsed)
        self.last_request = time.time()
    
    def get_wikipedia_link(self, page_title: str) -> Optional[str]:
        """Récupère le lien Wikipedia depuis une page Tolkien Gateway."""
        if self.cache.has('wikipedia', page_title):
            return self.cache.get('wikipedia', page_title)
        
        self._wait()
        
        try:
            response = self.session.get(self.API_URL, params={
                'action': 'parse',
                'page': page_title,
                'prop': 'externallinks',
                'format': 'json'
            }, timeout=10)
            
            data = response.json()
            
            if 'parse' in data and 'externallinks' in data['parse']:
                external_links = data['parse']['externallinks']
                
                for link in external_links:
                    link_lower = link.lower()
                    
                    if 'en.wikipedia.org/wiki/' in link_lower:
                        self.cache.set('wikipedia', page_title, link)
                        return link
                    
                    elif 'wikipedia.org/wiki/' in link_lower and '/en.' not in link_lower:
                        if not self.cache.has('wikipedia', page_title):
                            self.cache.set('wikipedia', page_title, link)
            
            cached = self.cache.get('wikipedia', page_title)
            if cached:
                return cached
            
            self.cache.set('wikipedia', page_title, None)
            return None
            
        except Exception as e:
            self.cache.set('wikipedia', page_title, None)
            return None
    
    def extract_wikipedia_title(self, wikipedia_url: str) -> Optional[str]:
        """Extrait le titre d'article depuis une URL Wikipedia."""
        if not wikipedia_url:
            return None
        
        try:
            if '/wiki/' in wikipedia_url:
                title = wikipedia_url.split('/wiki/')[-1]
                title = title.split('#')[0].split('?')[0]
                return unquote(title)
        except:
            pass
        
        return None


class ExternalAlignmentGenerator:
    """Génère des alignements owl:sameAs vérifiés vers des KGs externes."""
    
    def __init__(self, mediawiki_client=None, cache_file: str = "alignment_cache.json"):
        self.client = mediawiki_client
        self.cache = AlignmentCache(cache_file)
        self.verifier = ResourceVerifier(self.cache)
        self.wikidata = WikidataClient(self.cache)
        self.wikipedia_extractor = WikipediaLinkExtractor(self.cache, mediawiki_client)
        
        self.graph = Graph()
        self._bind_namespaces()
        
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
        self.graph.bind("tolkien", TOLKIEN)
        self.graph.bind("owl", OWL)
        self.graph.bind("foaf", FOAF)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("dbpedia", DBPEDIA)
        self.graph.bind("yago", YAGO)
        self.graph.bind("wikidata", WIKIDATA)
    
    def _make_uri_name(self, entity_name: str) -> str:
        return quote(entity_name.replace(' ', '_'), safe='')
    
    def align_entity(self, entity_name: str, verify_external: bool = True) -> int:
        """Crée les alignements vérifiés pour une entité."""
        self.stats['processed'] += 1
        count = 0
        
        uri_name = self._make_uri_name(entity_name)
        tolkien_uri = TOLKIEN[uri_name]
        
        wikipedia_url = self.wikipedia_extractor.get_wikipedia_link(entity_name)
        wikipedia_title = None
        
        if wikipedia_url:
            self.stats['wikipedia_found'] += 1
            wikipedia_title = self.wikipedia_extractor.extract_wikipedia_title(wikipedia_url)
            
            self.graph.add((tolkien_uri, FOAF.isPrimaryTopicOf, URIRef(wikipedia_url)))
            count += 1
        
        self.stats['dbpedia_checked'] += 1
        
        dbpedia_name = wikipedia_title or entity_name
        dbpedia_uri_name = self._make_uri_name(dbpedia_name.replace('_', ' '))
        
        if verify_external:
            dbpedia_exists = self.verifier.check_dbpedia(dbpedia_name.replace('_', ' '))
        else:
            dbpedia_exists = True
        
        if dbpedia_exists:
            self.stats['dbpedia_verified'] += 1
            dbpedia_uri = DBPEDIA[dbpedia_uri_name]
            self.graph.add((tolkien_uri, OWL.sameAs, dbpedia_uri))
            count += 1
        
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
        """Aligne un lot d'entités."""
        total = 0
        
        if verbose:
            print(f"Alignement de {len(entity_names)} entites...")
            if verify_external:
                print("Verification des ressources externes activee")
            else:
                print("Mode rapide sans verification")
        
        for i, name in enumerate(entity_names):
            if verbose and (i + 1) % 20 == 0:
                print(f"{i + 1}/{len(entity_names)} traites...")
                self.cache.save()
            
            try:
                total += self.align_entity(name, verify_external)
            except Exception as e:
                pass
        
        self.cache.save()
        
        if verbose:
            print("\nResultats:")
            print(f"Entites traitees: {self.stats['processed']}")
            print(f"Wikipedia trouves: {self.stats['wikipedia_found']}")
            print(f"DBpedia verifies: {self.stats['dbpedia_verified']}/{self.stats['dbpedia_checked']}")
            print(f"YAGO verifies: {self.stats['yago_verified']}/{self.stats['yago_checked']}")
            print(f"Wikidata trouves: {self.stats['wikidata_found']}")
            print(f"Total alignements: {self.stats['total_alignments']}")
        
        return total
    
    def add_to_graph(self, target_graph: Graph) -> int:
        """Ajoute les alignements à un graphe cible."""
        count = 0
        for triple in self.graph:
            target_graph.add(triple)
            count += 1
        return count
    
    def get_statistics(self) -> Dict[str, Any]:
        return self.stats.copy()
    
    def save(self, filename: str, format: str = "turtle"):
        """Sauvegarde les alignements dans un fichier."""
        self.graph.serialize(destination=filename, format=format)
        print(f"Sauvegarde: {filename} ({len(self.graph)} triplets)")


def add_alignments_to_kg(kg_graph: Graph, client, entity_names: List[str],
                          verbose: bool = True, verify: bool = True) -> int:
    """Ajoute des alignements vérifiés à un graphe RDF existant."""
    gen = ExternalAlignmentGenerator(mediawiki_client=client)
    gen.align_entities(list(entity_names), verbose=verbose, verify_external=verify)
    return gen.add_to_graph(kg_graph)


__all__ = [
    'ExternalAlignmentGenerator',
    'WikidataClient',
    'WikipediaLinkExtractor',
    'ResourceVerifier',
    'AlignmentCache',
    'add_alignments_to_kg',
]