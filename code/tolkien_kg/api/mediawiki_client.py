"""
Client pour l'API MediaWiki du Tolkien Gateway
"""

import requests
import time
from typing import Generator, Dict, List, Any, Optional
from ..config import (
    MEDIAWIKI_API_URL, 
    USER_AGENT, 
    REQUEST_DELAY, 
    MAX_PAGES_PER_REQUEST
)


class MediaWikiClient:
    """Client pour l'API MediaWiki du Tolkien Gateway avec rate limiting."""
    
    def __init__(self, api_url: str = MEDIAWIKI_API_URL):
        self.api_url = api_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT
        })
        self.last_request_time = 0
    
    def _respect_rate_limit(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
        self.last_request_time = time.time()
    
    def _make_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Effectue une requête à l'API MediaWiki."""
        self._respect_rate_limit()
        params['format'] = 'json'
        
        try:
            response = self.session.get(self.api_url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Erreur requete API: {e}")
            raise
    
    def get_all_pages(self, namespace: int = 0, limit: int = None) -> Generator[Dict[str, Any], None, None]:
        """Récupère toutes les pages du wiki avec pagination."""
        params = {
            'action': 'query',
            'list': 'allpages',
            'apnamespace': namespace,
            'aplimit': min(MAX_PAGES_PER_REQUEST, limit) if limit else MAX_PAGES_PER_REQUEST
        }
        
        count = 0
        while True:
            data = self._make_request(params)
            
            for page in data.get('query', {}).get('allpages', []):
                yield page
                count += 1
                if limit and count >= limit:
                    return
            
            if 'continue' in data:
                params['apcontinue'] = data['continue']['apcontinue']
            else:
                break
    
    def get_category_members(self, category: str, limit: int = None) -> Generator[Dict[str, Any], None, None]:
        """Récupère tous les membres d'une catégorie."""
        if not category.startswith('Category:'):
            category = f'Category:{category}'
        
        params = {
            'action': 'query',
            'list': 'categorymembers',
            'cmtitle': category,
            'cmlimit': min(MAX_PAGES_PER_REQUEST, limit) if limit else MAX_PAGES_PER_REQUEST
        }
        
        count = 0
        while True:
            data = self._make_request(params)
            
            for member in data.get('query', {}).get('categorymembers', []):
                yield member
                count += 1
                if limit and count >= limit:
                    return
            
            if 'continue' in data:
                params['cmcontinue'] = data['continue']['cmcontinue']
            else:
                break
    
    def get_all_categories(self, limit: int = None) -> Generator[Dict[str, Any], None, None]:
        """Récupère toutes les catégories du wiki."""
        params = {
            'action': 'query',
            'list': 'allcategories',
            'aclimit': min(MAX_PAGES_PER_REQUEST, limit) if limit else MAX_PAGES_PER_REQUEST
        }
        
        count = 0
        while True:
            data = self._make_request(params)
            
            for cat in data.get('query', {}).get('allcategories', []):
                yield cat
                count += 1
                if limit and count >= limit:
                    return
            
            if 'continue' in data:
                params['accontinue'] = data['continue']['accontinue']
            else:
                break
    
    def search_pages(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recherche des pages par mot-clé."""
        params = {
            'action': 'query',
            'list': 'search',
            'srsearch': query,
            'srlimit': limit
        }
        
        data = self._make_request(params)
        return data.get('query', {}).get('search', [])
    
    def get_page_wikitext(self, title: str) -> Optional[str]:
        """Récupère le code source wikitext d'une page."""
        params = {
            'action': 'parse',
            'page': title,
            'prop': 'wikitext',
            'formatversion': '2'
        }
        
        data = self._make_request(params)
        
        if 'error' in data:
            print(f"Erreur page '{title}': {data['error'].get('info', 'Unknown error')}")
            return None
        
        return data.get('parse', {}).get('wikitext', None)
    
    def get_page_links(self, title: str) -> List[Dict[str, Any]]:
        """Récupère tous les liens internes d'une page."""
        params = {
            'action': 'parse',
            'page': title,
            'prop': 'links',
            'formatversion': '2'
        }
        
        data = self._make_request(params)
        
        if 'error' in data:
            return []
        
        return data.get('parse', {}).get('links', [])
    
    def get_page_external_links(self, title: str) -> List[str]:
        """Récupère tous les liens externes d'une page."""
        params = {
            'action': 'parse',
            'page': title,
            'prop': 'externallinks',
            'formatversion': '2'
        }
        
        data = self._make_request(params)
        
        if 'error' in data:
            return []
        
        return data.get('parse', {}).get('externallinks', [])
    
    def get_page_templates(self, title: str) -> List[Dict[str, Any]]:
        """Récupère tous les templates utilisés dans une page."""
        params = {
            'action': 'parse',
            'page': title,
            'prop': 'templates',
            'formatversion': '2'
        }
        
        data = self._make_request(params)
        
        if 'error' in data:
            return []
        
        return data.get('parse', {}).get('templates', [])
    
    def get_page_images(self, title: str) -> List[str]:
        """Récupère toutes les images d'une page."""
        params = {
            'action': 'parse',
            'page': title,
            'prop': 'images',
            'formatversion': '2'
        }
        
        data = self._make_request(params)
        
        if 'error' in data:
            return []
        
        return data.get('parse', {}).get('images', [])
    
    def get_page_categories(self, title: str) -> List[Dict[str, Any]]:
        """Récupère toutes les catégories d'une page."""
        params = {
            'action': 'parse',
            'page': title,
            'prop': 'categories',
            'formatversion': '2'
        }
        
        data = self._make_request(params)
        
        if 'error' in data:
            return []
        
        return data.get('parse', {}).get('categories', [])
    
    def get_page_full_info(self, title: str) -> Dict[str, Any]:
        """Récupère toutes les informations d'une page en une seule requête."""
        params = {
            'action': 'parse',
            'page': title,
            'prop': 'wikitext|links|templates|images|categories|externallinks',
            'formatversion': '2'
        }
        
        data = self._make_request(params)
        
        if 'error' in data:
            return {'error': data['error']}
        
        parse_data = data.get('parse', {})
        return {
            'title': parse_data.get('title', title),
            'pageid': parse_data.get('pageid'),
            'wikitext': parse_data.get('wikitext'),
            'links': parse_data.get('links', []),
            'templates': parse_data.get('templates', []),
            'images': parse_data.get('images', []),
            'categories': parse_data.get('categories', []),
            'externallinks': parse_data.get('externallinks', [])
        }
    
    def get_pages_using_template(self, template: str, namespace: int = 0, limit: int = None) -> Generator[Dict[str, Any], None, None]:
        """Récupère toutes les pages qui utilisent un template donné."""
        if not template.startswith('Template:'):
            template = f'Template:{template}'
        
        params = {
            'action': 'query',
            'list': 'embeddedin',
            'eititle': template,
            'eilimit': min(MAX_PAGES_PER_REQUEST, limit) if limit else MAX_PAGES_PER_REQUEST,
            'eifilterredir': 'nonredirects'
        }
        
        if namespace is not None:
            params['einamespace'] = namespace
        
        count = 0
        while True:
            data = self._make_request(params)
            
            for page in data.get('query', {}).get('embeddedin', []):
                yield page
                count += 1
                if limit and count >= limit:
                    return
            
            if 'continue' in data:
                params['eicontinue'] = data['continue']['eicontinue']
            else:
                break
    
    def get_all_infobox_templates(self) -> List[Dict[str, Any]]:
        """Récupère tous les templates d'infobox disponibles."""
        infobox_templates = []
        for member in self.get_category_members("Infobox templates"):
            if member.get('ns') == 10:
                infobox_templates.append(member)
        return infobox_templates
    
    def get_infobox_usage_stats(self) -> Dict[str, int]:
        """Récupère les statistiques d'utilisation de chaque template d'infobox."""
        stats = {}
        templates = self.get_all_infobox_templates()
        
        for template in templates:
            template_name = template['title'].replace('Template:', '')
            count = 0
            for _ in self.get_pages_using_template(template_name):
                count += 1
            stats[template_name] = count
        
        return stats
    
    def count_pages_using_template(self, template: str) -> int:
        """Compte le nombre de pages utilisant un template donné."""
        count = 0
        for _ in self.get_pages_using_template(template):
            count += 1
        return count
    
    def page_exists(self, title: str) -> bool:
        """Vérifie si une page existe."""
        params = {
            'action': 'query',
            'titles': title,
            'formatversion': '2'
        }
        
        data = self._make_request(params)
        pages = data.get('query', {}).get('pages', [])
        
        if pages:
            return 'missing' not in pages[0]
        return False
    
    def get_wiki_statistics(self) -> Dict[str, Any]:
        """Récupère les statistiques générales du wiki."""
        params = {
            'action': 'query',
            'meta': 'siteinfo',
            'siprop': 'statistics'
        }
        
        data = self._make_request(params)
        return data.get('query', {}).get('statistics', {})