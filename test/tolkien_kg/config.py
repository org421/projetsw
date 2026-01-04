"""
Configuration du projet Tolkien Knowledge Graph
"""

# Namespace et URIs de base
BASE_NAMESPACE = "https://tolkiengateway.net/wiki/"
RESOURCE_PREFIX = "https://tolkiengateway.net/wiki/"

# API MediaWiki
MEDIAWIKI_API_URL = "https://tolkiengateway.net/w/api.php"
MEDIAWIKI_SITE = "tolkiengateway.net"
MEDIAWIKI_PATH = "/w/"

# User-Agent pour les requêtes (important pour ne pas être banni)
USER_AGENT = "TolkienKGBot/1.0 (Semantic Web Project; Educational Purpose)"

# Paramètres de requête
REQUEST_DELAY = 0.5  # Délai entre les requêtes en secondes
MAX_PAGES_PER_REQUEST = 50  # Nombre max de pages par requête API
