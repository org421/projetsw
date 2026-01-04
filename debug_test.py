import requests

# URL et Paramètres identiques à ceux qui plantent
API_URL = "https://tolkiengateway.net/api.php"
params = {
    "action": "query",
    "format": "json",
    "generator": "embeddedin",
    "geititle": "Template:Infobox character",
    "geilimit": "5", # On en demande peu pour tester
    "prop": "revisions",
    "rvprop": "content"
}

# Headers "Navigateur"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

print(f"--- TEST DE CONNEXION VERS {API_URL} ---")

try:
    resp = requests.get(API_URL, params=params, headers=headers, timeout=10)
    
    print(f"Code Statut HTTP : {resp.status_code}")
    print(f"URL Finale : {resp.url}")
    
    try:
        data = resp.json()
        print("\nSUCCÈS ! JSON valide reçu.")
        print(str(data)[:200] + "...")
    except Exception as e:
        print("\nÉCHEC DU PARSING JSON.")
        print("Le serveur a renvoyé du texte brut (HTML). Voici le début :\n")
        print("="*40)
        print(resp.text[:1000]) # On affiche les 1000 premiers caractères
        print("="*40)

except Exception as e:
    print(f"Erreur fatale de connexion : {e}")