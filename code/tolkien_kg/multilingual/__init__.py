"""
Enrichissement multilingue via l'API Fandom (The One Wiki to Rule Them All).
"""

import requests
import json
import os
import time
from urllib.parse import quote


class FandomEnricher:
    """Récupère les traductions des entités via l'API Fandom avec cache local."""
    
    API_URL = "https://lotr.fandom.com/api.php"
    CACHE_FILE = "fandom_lang_cache.json"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "TolkienSemanticProject/1.0 (Educational purpose)"
        })
        self.cache = self._load_cache()
        self.changes_count = 0
    
    def _load_cache(self):
        if os.path.exists(self.CACHE_FILE):
            try:
                with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_cache(self):
        """Sauvegarde le cache si des modifications ont été faites."""
        if self.changes_count > 0:
            with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            print(f"Cache sauvegarde: {self.changes_count} nouvelles entrees")
            self.changes_count = 0
    
    def get_translations(self, entity_name):
        """Récupère les traductions d'une entité via langlinks."""
        if entity_name in self.cache:
            return self.cache[entity_name]
        
        params = {
            "action": "query",
            "format": "json",
            "prop": "langlinks",
            "titles": entity_name,
            "lllimit": "max",
            "redirects": 1
        }
        
        try:
            response = self.session.get(self.API_URL, params=params, timeout=5)
            data = response.json()
            translations = {}
            
            pages = data.get("query", {}).get("pages", {})
            for page_id, page_data in pages.items():
                if page_id == "-1":
                    continue
                if "langlinks" in page_data:
                    for ll in page_data["langlinks"]:
                        translations[ll["lang"]] = ll["*"]
            
            self.cache[entity_name] = translations
            self.changes_count += 1
            
            time.sleep(0.1)
            
            return translations
            
        except Exception as e:
            print(f"Erreur API Fandom pour {entity_name}: {e}")
            return {}