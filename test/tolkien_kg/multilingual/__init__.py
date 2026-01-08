import requests
import json
import os
import time
from urllib.parse import quote

class FandomEnricher:
    """
    Classe responsable de l'enrichissement multilingue via l'API Fandom.
    Respecte les consignes: automatisation + source externe (The One Wiki).
    Intègre un cache pour ne pas être bloqué par l'API.
    """
    
    # L'API du wiki mentionné par le prof (The One Wiki to Rule Them All)
    API_URL = "https://lotr.fandom.com/api.php"
    CACHE_FILE = "fandom_lang_cache.json"

    def __init__(self):
        self.session = requests.Session()
        # User-Agent pour être poli envers le serveur (évite les bannissements)
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
        """Sauvegarde les nouvelles données si nécessaire."""
        if self.changes_count > 0:
            with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            print(f"   [Cache] Sauvegardé {self.changes_count} nouvelles entrées.")
            self.changes_count = 0

    def get_translations(self, entity_name):
        """
        Récupère les langlinks pour une entité.
        Retourne un dict: {'fr': 'Gandalf', 'de': 'Gandalf',...}
        """
        # 1. Vérifier le cache local (RAPIDE)
        if entity_name in self.cache:
            return self.cache[entity_name]

        # 2. Si pas dans le cache, appeler l'API (LENT)
        # On cherche les 'langlinks' (liens inter-langues)
        params = {
            "action": "query",
            "format": "json",
            "prop": "langlinks",
            "titles": entity_name,
            "lllimit": "max",  # Récupérer le maximum de langues
            "redirects": 1     # Suivre les redirections si le nom varie légèrement
        }

        try:
            response = self.session.get(self.API_URL, params=params, timeout=5)
            data = response.json()
            
            translations = {}
            pages = data.get("query", {}).get("pages", {})
            
            for page_id, page_data in pages.items():
                if page_id == "-1": continue # Page non trouvée
                
                if "langlinks" in page_data:
                    for ll in page_data["langlinks"]:
                        # Stocke code langue (ex: 'fr') -> Titre (ex: 'La Comté')
                        translations[ll["lang"]] = ll["*"]

            # Mise à jour du cache
            self.cache[entity_name] = translations
            self.changes_count += 1
            
            # Petite pause pour ne pas spammer l'API
            time.sleep(0.1) 
            
            return translations

        except Exception as e:
            print(f"   [Erreur API] {entity_name}: {e}")
            return {}