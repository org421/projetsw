import requests
from typing import Optional, Dict, Any
from pathlib import Path


class FusekiClient:
    # Client pour interagir avec un serveur Apache Jena Fuseki

    def __init__(self, base_url: str = "http://localhost:3030", dataset: str = "tolkien"):
        # Initialise la connexion Fuseki et la session HTTP
        self.base_url = base_url.rstrip("/")
        self.dataset = dataset
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "TolkienKG/1.0"
        })

    @property
    def query_endpoint(self) -> str:
        # Endpoint SPARQL SELECT
        return f"{self.base_url}/{self.dataset}/query"

    @property
    def update_endpoint(self) -> str:
        # Endpoint SPARQL UPDATE
        return f"{self.base_url}/{self.dataset}/update"

    @property
    def data_endpoint(self) -> str:
        # Endpoint Graph Store Protocol
        return f"{self.base_url}/{self.dataset}/data"

    def is_available(self) -> bool:
        # Vérifie si le serveur Fuseki est accessible
        try:
            response = self.session.get(f"{self.base_url}/$/ping", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def dataset_exists(self) -> bool:
        # Vérifie si le dataset existe sur le serveur
        try:
            response = self.session.get(
                f"{self.base_url}/$/datasets/{self.dataset}",
                timeout=5
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def create_dataset(self, persistent: bool = True) -> bool:
        # Crée un dataset s'il n'existe pas
        try:
            db_type = "tdb2" if persistent else "mem"
            response = self.session.post(
                f"{self.base_url}/$/datasets",
                data={
                    "dbName": self.dataset,
                    "dbType": db_type
                },
                timeout=10
            )
            return response.status_code in [200, 201]
        except requests.RequestException as e:
            print(f"Erreur création dataset : {e}")
            return False

    def clear_dataset(self) -> bool:
        # Supprime tous les triplets du dataset
        try:
            response = self.session.post(
                self.update_endpoint,
                data={"update": "CLEAR ALL"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30
            )
            return response.status_code == 200
        except requests.RequestException as e:
            print(f"Erreur vidage dataset : {e}")
            return False

    def upload_file(
        self,
        filepath: str,
        graph_uri: Optional[str] = None,
        clear_first: bool = False
    ) -> Dict[str, Any]:
        # Upload un fichier RDF dans Fuseki
        result = {
            "success": False,
            "message": "",
            "triples_before": 0,
            "triples_after": 0
        }

        path = Path(filepath)
        if not path.exists():
            result["message"] = f"Fichier introuvable : {filepath}"
            return result

        content_types = {
            ".ttl": "text/turtle",
            ".nt": "application/n-triples",
            ".nq": "application/n-quads",
            ".rdf": "application/rdf+xml",
            ".xml": "application/rdf+xml",
            ".jsonld": "application/ld+json",
            ".json": "application/ld+json",
        }
        content_type = content_types.get(path.suffix.lower(), "text/turtle")

        result["triples_before"] = self.count_triples()

        if clear_first:
            print("Vidage du dataset")
            self.clear_dataset()

        try:
            print(f"Upload du fichier {filepath}")

            with open(filepath, "rb") as f:
                params = {}
                if graph_uri:
                    params["graph"] = graph_uri

                response = self.session.post(
                    self.data_endpoint,
                    data=f,
                    params=params,
                    headers={"Content-Type": content_type},
                    timeout=300
                )

            if response.status_code in [200, 201, 204]:
                result["success"] = True
                result["triples_after"] = self.count_triples()
                added = result["triples_after"] - result["triples_before"]
                result["message"] = f"{added} triplets ajoutés"
            else:
                result["message"] = f"Erreur HTTP {response.status_code}"

        except requests.RequestException as e:
            result["message"] = f"Erreur réseau : {e}"
        except Exception as e:
            result["message"] = f"Erreur : {e}"

        return result

    def count_triples(self, graph_uri: Optional[str] = None) -> int:
        # Compte le nombre de triplets dans le dataset
        try:
            if graph_uri:
                query = f"""
                SELECT (COUNT(*) AS ?count)
                WHERE {{ GRAPH <{graph_uri}> {{ ?s ?p ?o }} }}
                """
            else:
                query = "SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }"

            response = self.session.post(
                self.query_endpoint,
                data={"query": query},
                headers={"Accept": "application/sparql-results+json"},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                return int(data["results"]["bindings"][0]["count"]["value"])
        except Exception:
            pass

        return 0

    def query(self, sparql: str) -> Optional[Dict]:
        # Exécute une requête SPARQL SELECT
        try:
            response = self.session.post(
                self.query_endpoint,
                data={"query": sparql},
                headers={"Accept": "application/sparql-results+json"},
                timeout=60
            )

            if response.status_code == 200:
                return response.json()

            print(f"Erreur requête SPARQL : {response.status_code}")
            return None

        except Exception as e:
            print(f"Erreur requête SPARQL : {e}")
            return None

    def get_statistics(self) -> Dict[str, Any]:
        # Récupère des statistiques globales sur le graphe
        stats = {
            "total_triples": self.count_triples(),
            "subjects": 0,
            "predicates": 0,
            "types": {},
            "languages": {}
        }

        result = self.query("SELECT (COUNT(DISTINCT ?s) AS ?c) WHERE { ?s ?p ?o }")
        if result:
            stats["subjects"] = int(result["results"]["bindings"][0]["c"]["value"])

        result = self.query("SELECT (COUNT(DISTINCT ?p) AS ?c) WHERE { ?s ?p ?o }")
        if result:
            stats["predicates"] = int(result["results"]["bindings"][0]["c"]["value"])

        result = self.query("""
            SELECT ?type (COUNT(?s) AS ?count)
            WHERE { ?s a ?type }
            GROUP BY ?type
            ORDER BY DESC(?count)
            LIMIT 20
        """)
        if result:
            for b in result["results"]["bindings"]:
                name = b["type"]["value"].split("/")[-1].split("#")[-1]
                stats["types"][name] = int(b["count"]["value"])

        result = self.query("""
            SELECT ?lang (COUNT(?label) AS ?count)
            WHERE {
                ?s <http://www.w3.org/2000/01/rdf-schema#label> ?label
                BIND(LANG(?label) AS ?lang)
            }
            GROUP BY ?lang
        """)
        if result:
            for b in result["results"]["bindings"]:
                lang = b["lang"]["value"] or "none"
                stats["languages"][lang] = int(b["count"]["value"])

        return stats


def upload_to_fuseki(filepath: str, endpoint_url: str, clear: bool = False) -> bool:
    # Fonction utilitaire pour charger un fichier RDF dans Fuseki
    parts = endpoint_url.rstrip("/").rsplit("/", 1)
    if len(parts) == 2:
        base_url, dataset = parts
    else:
        base_url = "http://localhost:3030"
        dataset = "tolkien"

    client = FusekiClient(base_url=base_url, dataset=dataset)

    print(f"Connexion à Fuseki : {base_url}")
    if not client.is_available():
        print("Fuseki inaccessible")
        return False

    if not client.dataset_exists():
        print(f"Création du dataset {dataset}")
        if not client.create_dataset():
            print("Échec création dataset")
            return False

    result = client.upload_file(filepath, clear_first=clear)

    if result["success"]:
        print(result["message"])
        print(f"Total triplets : {result['triples_after']}")
        return True

    print(result["message"])
    return False


def check_fuseki_status(
    base_url: str = "http://localhost:3030",
    dataset: str = "tolkien"
) -> Dict[str, Any]:
    # Vérifie l'état du serveur Fuseki et du dataset
    status = {
        "fuseki_running": False,
        "dataset_exists": False,
        "triple_count": 0,
        "stats": {}
    }

    client = FusekiClient(base_url=base_url, dataset=dataset)
    status["fuseki_running"] = client.is_available()

    if status["fuseki_running"]:
        status["dataset_exists"] = client.dataset_exists()
        if status["dataset_exists"]:
            status["triple_count"] = client.count_triples()
            status["stats"] = client.get_statistics()

    return status


def print_fuseki_status(
    base_url: str = "http://localhost:3030",
    dataset: str = "tolkien"
):
    # Affiche l'état de Fuseki et du dataset
    print("\n" + "=" * 60)
    print("STATUT FUSEKI")
    print("=" * 60)

    status = check_fuseki_status(base_url, dataset)

    print(f"Serveur : {base_url}")
    print(f"Dataset : {dataset}")
    print(f"Fuseki actif : {status['fuseki_running']}")

    if not status["fuseki_running"]:
        return

    print(f"Dataset présent : {status['dataset_exists']}")

    if status["dataset_exists"]:
        stats = status["stats"]
        print(f"Triplets : {stats.get('total_triples', 0)}")
        print(f"Sujets : {stats.get('subjects', 0)}")
        print(f"Prédicats : {stats.get('predicates', 0)}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        endpoint = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:3030/tolkien"
        upload_to_fuseki(file_path, endpoint)
    else:
        print_fuseki_status()
