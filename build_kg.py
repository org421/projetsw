import requests
import time
from rdflib import Graph, Namespace
from tolkien_parser import parse_any_page

# 1. CONFIGURATION
API_URL = "https://tolkiengateway.net/w/api.php"
HEADERS = {"User-Agent": "TolkienKG-Bot/1.0 (Educational Project)"}

TOLKIEN = Namespace("http://tolkien-kg.org/ontology/")
RES = Namespace("http://tolkien-kg.org/resource/")
g = Graph()
g.bind("tolkien", TOLKIEN)
g.bind("res", RES)

# 2. FONCTIONS RÉSEAU (MÉTHODE EMBEDDEDIN)
def get_pages_using_template(template_name, limit=500):
    """
    Récupère toutes les pages qui incluent un template spécifique.
    C'est la méthode la plus fiable pour tout trouver.
    """
    print(f">> Recherche des pages utilisant : Template:{template_name}")
    params = {
        "action": "query", 
        "list": "embeddedin",
        "eititle": f"Template:{template_name}", 
        "einamespace": 0,    # 0 = Articles uniquement (ignore les pages utilisateurs/discussions)
        "eilimit": limit,
        "format": "json"
    }
    try:
        r = requests.get(API_URL, params=params, headers=HEADERS, timeout=10)
        return [m['title'] for m in r.json().get("query", {}).get("embeddedin", [])]
    except Exception as e:
        print(f"Erreur : {e}")
        return []

def get_page_content(title):
    params = {"action": "parse", "page": title, "prop": "wikitext", "format": "json", "formatversion": 2}
    try:
        r = requests.get(API_URL, params=params, headers=HEADERS)
        return r.json().get("parse", {}).get("wikitext", "")
    except: return ""

# 3. LISTE DES 72 TEMPLATES (D'après ton image)
# J'ai regroupé les noms exacts.
TEMPLATES_TO_SCAN = [
    # --- LES PLUS IMPORTANTS ---
    "Infobox character", "Location infobox", "Book", "Battle", 
    "Object infobox", "Weapon", # Parfois "Weapon" tout court, parfois "Object"
    "Actor", "Film infobox", 
    
    # --- RACES & PEUPLES ---
    "Elves infobox", "Men infobox", "Dwarves infobox", "Hobbit", # Parfois pas d'infobox spécifique
    "Maiar infobox", "Valar infobox", "Dragon infobox", "Eagle infobox",
    "Ent infobox", "Orc", "Troll", 
    "Arnorian infobox", "Gondorian infobox", "Rohirrim infobox", 
    "Numenorean infobox", "Easterling infobox", "Druadan infobox",
    "Half-elf infobox", "Avar infobox", "Nandor infobox", "Noldor infobox",
    "Sindar infobox", "Vanyar infobox", "Northmen infobox",
    
    # --- LIEUX ---
    "Kingdom", "Realms", "City",
    "Mountain", "River", "Lake", "Forest", 
    
    # --- CULTURE ---
    "Language", "Song", "Poem", "Letter infobox", "Journal",
    "Artist infobox", "Author infobox", "Band", 
    
    # --- AUTRES ---
    "Event", "War", "Organization infobox", "Company infobox",
    "Collectible", "Board game infobox", "Video game infobox",
    "Website", "Convention"
]

# 4. EXÉCUTION
if __name__ == "__main__":
    
    # LIMIT = None (ou 5000) pour tout prendre
    # LIMIT = 20 pour tester rapidement
    LIMIT = 20 
    
    print(f"--- DÉMARRAGE PAR TEMPLATES ({len(TEMPLATES_TO_SCAN)} types) ---")
    
    total_extracted = 0
    
    for template in TEMPLATES_TO_SCAN:
        # Cette fois, on est sûr d'avoir des résultats si le template est utilisé
        titles = get_pages_using_template(template, limit=LIMIT)
        
        if not titles:
            print("   (0 pages trouvées - Template peut-être inutilisé ou mal nommé)")
        else:
            print(f"   -> {len(titles)} pages candidates.")
        
        for title in titles:
            wikitext = get_page_content(title)
            if wikitext:
                # Le parser universel gère tout
                if parse_any_page(wikitext, title, g, RES):
                    print(f"   [OK] {title}")
                    total_extracted += 1
                else:
                    # Parfois la page utilise le template mais d'une façon bizarre
                    pass
            
            time.sleep(0.1) # Petit délai
            
    print(f"\n--- TERMINE : {total_extracted} entités extraites ---")
    g.serialize(destination="tolkien_kg_templates.ttl", format="turtle")
    print("Fichier 'tolkien_kg_templates.ttl' généré.")