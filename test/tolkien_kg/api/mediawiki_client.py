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
    """
    Client pour interagir avec l'API MediaWiki du Tolkien Gateway.
    Implémente les bonnes pratiques pour éviter d'être banni:
    - User-Agent approprié
    - Délai entre les requêtes
    - Gestion de la pagination
    """
    
    def __init__(self, api_url: str = MEDIAWIKI_API_URL):
        self.api_url = api_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT
        })
        self.last_request_time = 0
    
    def _respect_rate_limit(self):
        """Attend si nécessaire pour respecter le délai entre requêtes."""
        elapsed = time.time() - self.last_request_time
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
        self.last_request_time = time.time()
    
    def _make_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Effectue une requête à l'API MediaWiki.
        
        Args:
            params: Paramètres de la requête
            
        Returns:
            Réponse JSON de l'API
        """
        self._respect_rate_limit()
        params['format'] = 'json'
        
        try:
            response = self.session.get(self.api_url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Erreur lors de la requête API: {e}")
            raise
    
    # ==================== ACTION: QUERY ====================
    
    def get_all_pages(self, namespace: int = 0, limit: int = None) -> Generator[Dict[str, Any], None, None]:
        """
        Récupère toutes les pages du wiki avec pagination.
        
        Args:
            namespace: Namespace à interroger (0 = articles principaux)
            limit: Nombre maximum de pages à récupérer (None = toutes)
            
        Yields:
            Dictionnaire avec les infos de chaque page (pageid, ns, title)
        """
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
            
            # Gestion de la pagination
            if 'continue' in data:
                params['apcontinue'] = data['continue']['apcontinue']
            else:
                break
    
    def get_category_members(self, category: str, limit: int = None) -> Generator[Dict[str, Any], None, None]:
        """
        Récupère tous les membres d'une catégorie.
        
        Args:
            category: Nom de la catégorie (avec ou sans préfixe "Category:")
            limit: Nombre maximum de membres à récupérer
            
        Yields:
            Dictionnaire avec les infos de chaque membre
        """
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
            
            # Gestion de la pagination
            if 'continue' in data:
                params['cmcontinue'] = data['continue']['cmcontinue']
            else:
                break
    
    def get_all_categories(self, limit: int = None) -> Generator[Dict[str, Any], None, None]:
        """
        Récupère toutes les catégories du wiki.
        
        Args:
            limit: Nombre maximum de catégories à récupérer
            
        Yields:
            Dictionnaire avec les infos de chaque catégorie
        """
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
        """
        Recherche des pages par mot-clé.
        
        Args:
            query: Terme de recherche
            limit: Nombre maximum de résultats
            
        Returns:
            Liste des pages correspondantes
        """
        params = {
            'action': 'query',
            'list': 'search',
            'srsearch': query,
            'srlimit': limit
        }
        
        data = self._make_request(params)
        return data.get('query', {}).get('search', [])
    
    # ==================== ACTION: PARSE ====================
    
    def get_page_wikitext(self, title: str) -> Optional[str]:
        """
        Récupère le code source wikitext d'une page.
        
        Args:
            title: Titre de la page
            
        Returns:
            Code wikitext de la page ou None si la page n'existe pas
        """
        params = {
            'action': 'parse',
            'page': title,
            'prop': 'wikitext',
            'formatversion': '2'
        }
        
        data = self._make_request(params)
        
        if 'error' in data:
            print(f"Erreur pour la page '{title}': {data['error'].get('info', 'Unknown error')}")
            return None
        
        return data.get('parse', {}).get('wikitext', None)
    
    def get_page_links(self, title: str) -> List[Dict[str, Any]]:
        """
        Récupère tous les liens internes d'une page.
        
        Args:
            title: Titre de la page
            
        Returns:
            Liste des liens avec leur namespace et titre
        """
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
        """
        Récupère tous les liens externes d'une page.
        
        Args:
            title: Titre de la page
            
        Returns:
            Liste des URLs externes
        """
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
        """
        Récupère tous les templates utilisés dans une page.
        
        Args:
            title: Titre de la page
            
        Returns:
            Liste des templates avec leur namespace et titre
        """
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
        """
        Récupère toutes les images d'une page.
        
        Args:
            title: Titre de la page
            
        Returns:
            Liste des noms de fichiers images
        """
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
        """
        Récupère toutes les catégories d'une page.
        
        Args:
            title: Titre de la page
            
        Returns:
            Liste des catégories
        """
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
        """
        Récupère toutes les informations d'une page en une seule requête.
        
        Args:
            title: Titre de la page
            
        Returns:
            Dictionnaire avec wikitext, links, templates, images, categories, externallinks
        """
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
    
    # ==================== ACTION: EMBEDDEDIN (PAGES PAR TEMPLATE) ====================
    
    def get_pages_using_template(self, template: str, namespace: int = 0, limit: int = None) -> Generator[Dict[str, Any], None, None]:
        """
        Récupère toutes les pages qui utilisent un template donné.
        Utilise l'action query avec list=embeddedin.
        
        Args:
            template: Nom du template (avec ou sans préfixe "Template:")
            namespace: Namespace à filtrer (0 = articles principaux, None = tous)
            limit: Nombre maximum de pages à récupérer (None = toutes)
            
        Yields:
            Dictionnaire avec les infos de chaque page (pageid, ns, title)
            
        Example:
            # Récupérer toutes les pages avec l'infobox character
            for page in client.get_pages_using_template("Infobox character"):
                print(page['title'])
        """
        if not template.startswith('Template:'):
            template = f'Template:{template}'
        
        params = {
            'action': 'query',
            'list': 'embeddedin',
            'eititle': template,
            'eilimit': min(MAX_PAGES_PER_REQUEST, limit) if limit else MAX_PAGES_PER_REQUEST,
            'eifilterredir': 'nonredirects'  # Exclure les redirections
        }
        
        # Filtrer par namespace si spécifié
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
            
            # Gestion de la pagination
            if 'continue' in data:
                params['eicontinue'] = data['continue']['eicontinue']
            else:
                break
    
    def get_all_infobox_templates(self) -> List[Dict[str, Any]]:
        """
        Récupère tous les templates d'infobox disponibles sur le wiki.
        Cherche dans la catégorie "Infobox templates".
        
        Returns:
            Liste des templates d'infobox avec leur titre
        """
        infobox_templates = []
        for member in self.get_category_members("Infobox templates"):
            if member.get('ns') == 10:  # Namespace 10 = Template
                infobox_templates.append(member)
        return infobox_templates
    
    def get_infobox_usage_stats(self) -> Dict[str, int]:
        """
        Récupère les statistiques d'utilisation de chaque template d'infobox.
        
        Returns:
            Dictionnaire {nom_template: nombre_pages}
        """
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
        """
        Compte le nombre de pages utilisant un template donné.
        
        Args:
            template: Nom du template
            
        Returns:
            Nombre de pages utilisant ce template
        """
        count = 0
        for _ in self.get_pages_using_template(template):
            count += 1
        return count
    
    # ==================== UTILITAIRES ====================
    
    def page_exists(self, title: str) -> bool:
        """
        Vérifie si une page existe.
        
        Args:
            title: Titre de la page
            
        Returns:
            True si la page existe, False sinon
        """
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
        """
        Récupère les statistiques générales du wiki.
        
        Returns:
            Dictionnaire avec les statistiques (pages, articles, users, etc.)
        """
        params = {
            'action': 'query',
            'meta': 'siteinfo',
            'siprop': 'statistics'
        }
        
        data = self._make_request(params)
        return data.get('query', {}).get('statistics', {})
