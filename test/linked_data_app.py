#!/usr/bin/env python3
"""
Interface Linked Data pour le Tolkien Knowledge Graph
Étape 14 : Exposer le KG via une interface web

Cette application Flask fournit :
- Une interface web pour naviguer dans le KG
- Un endpoint SPARQL proxy
- Des pages HTML pour chaque entité (Content Negotiation)
- Une API REST pour les données
"""

from flask import Flask, request, jsonify, render_template_string, redirect, url_for, Response
import requests
from urllib.parse import quote, unquote
import json

app = Flask(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

FUSEKI_URL = "http://localhost:3030"
DATASET_NAME = "tolkien"
SPARQL_ENDPOINT = f"{FUSEKI_URL}/{DATASET_NAME}/sparql"

# Préfixes SPARQL
PREFIXES = """
PREFIX tolkien: <https://tolkiengateway.net/wiki/>
PREFIX tolkien_prop: <https://tolkiengateway.net/wiki/Property:>
PREFIX tolkien_class: <https://tolkiengateway.net/wiki/Class:>
PREFIX meccg: <https://meccg.net/card/>
PREFIX meccg_prop: <https://meccg.net/property/>
PREFIX meccg_class: <https://meccg.net/class/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX schema: <http://schema.org/>
PREFIX dbpedia: <http://dbpedia.org/resource/>
PREFIX wikidata: <http://www.wikidata.org/entity/>
"""


# =============================================================================
# TEMPLATES HTML
# =============================================================================

BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - Tolkien Knowledge Graph</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #e0e0e0;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header { 
            background: rgba(255,255,255,0.1); 
            padding: 20px; 
            margin-bottom: 30px;
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }
        header h1 { 
            color: #ffd700; 
            font-size: 2em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }
        header p { color: #aaa; margin-top: 5px; }
        nav { margin-top: 15px; }
        nav a { 
            color: #87ceeb; 
            text-decoration: none; 
            margin-right: 20px;
            padding: 8px 15px;
            border-radius: 5px;
            transition: all 0.3s;
        }
        nav a:hover { background: rgba(255,255,255,0.1); color: #ffd700; }
        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .card h2 { color: #ffd700; margin-bottom: 15px; }
        .card h3 { color: #87ceeb; margin: 15px 0 10px 0; font-size: 1.1em; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { 
            padding: 12px; 
            text-align: left; 
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        th { color: #ffd700; font-weight: 600; }
        td a { color: #87ceeb; text-decoration: none; }
        td a:hover { color: #ffd700; text-decoration: underline; }
        .uri { font-family: monospace; font-size: 0.9em; color: #888; word-break: break-all; }
        .lang-tag { 
            background: #4a5568; 
            color: #e2e8f0; 
            padding: 2px 6px; 
            border-radius: 3px; 
            font-size: 0.8em;
            margin-left: 5px;
        }
        .type-badge {
            display: inline-block;
            background: #2d3748;
            color: #68d391;
            padding: 4px 10px;
            border-radius: 15px;
            font-size: 0.85em;
            margin-right: 5px;
            margin-bottom: 5px;
        }
        .external-link {
            display: inline-block;
            background: #553c9a;
            color: #e9d8fd;
            padding: 4px 10px;
            border-radius: 15px;
            font-size: 0.85em;
            margin-right: 5px;
            margin-bottom: 5px;
            text-decoration: none;
        }
        .external-link:hover { background: #6b46c1; }
        form { margin: 20px 0; }
        input[type="text"], textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 5px;
            background: rgba(0,0,0,0.3);
            color: #e0e0e0;
            font-family: monospace;
        }
        textarea { min-height: 150px; resize: vertical; }
        button {
            background: #ffd700;
            color: #1a1a2e;
            padding: 12px 25px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: 600;
            margin-top: 10px;
            transition: all 0.3s;
        }
        button:hover { background: #ffed4a; transform: translateY(-2px); }
        .stats { display: flex; gap: 20px; flex-wrap: wrap; }
        .stat-box {
            background: rgba(255,215,0,0.1);
            border: 1px solid rgba(255,215,0,0.3);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            min-width: 150px;
        }
        .stat-box .number { font-size: 2em; color: #ffd700; font-weight: bold; }
        .stat-box .label { color: #aaa; margin-top: 5px; }
        .search-results { margin-top: 20px; }
        .result-item { 
            padding: 15px; 
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .result-item:hover { background: rgba(255,255,255,0.05); }
        pre {
            background: rgba(0,0,0,0.3);
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-size: 0.9em;
        }
        footer {
            text-align: center;
            padding: 30px;
            color: #666;
            margin-top: 50px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🏔️ Tolkien Knowledge Graph</h1>
            <p>Explorez l'univers de Tolkien en données liées</p>
            <nav>
                <a href="/">🏠 Accueil</a>
                <a href="/sparql">🔍 SPARQL</a>
                <a href="/browse/characters">👤 Personnages</a>
                <a href="/browse/locations">📍 Lieux</a>
                <a href="/browse/cards">🎴 Cartes MECCG</a>
                <a href="/search">🔎 Recherche</a>
            </nav>
        </header>
        
        {{ content | safe }}
        
        <footer>
            <p>Tolkien Knowledge Graph - Projet Web Sémantique M2 DSC</p>
            <p>Données: Tolkien Gateway + MECCG + DBpedia/Wikidata</p>
        </footer>
    </div>
</body>
</html>
"""


# =============================================================================
# FONCTIONS SPARQL
# =============================================================================

def sparql_query(query: str, format: str = "json") -> dict:
    """Exécute une requête SPARQL sur Fuseki."""
    headers = {
        "Accept": "application/sparql-results+json" if format == "json" else "text/turtle"
    }
    
    try:
        response = requests.post(
            SPARQL_ENDPOINT,
            data={"query": PREFIXES + query},
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json() if format == "json" else {"raw": response.text}
        else:
            return {"error": f"SPARQL Error: {response.status_code}"}
            
    except requests.exceptions.RequestException as e:
        return {"error": f"Connection error: {str(e)}"}


def get_entity_data(uri: str) -> dict:
    """Récupère toutes les données d'une entité."""
    query = f"""
    SELECT ?p ?o ?lang
    WHERE {{
        <{uri}> ?p ?o .
        BIND(lang(?o) AS ?lang)
    }}
    """
    return sparql_query(query)


def get_reverse_links(uri: str) -> dict:
    """Récupère les entités qui pointent vers cette entité."""
    query = f"""
    SELECT ?s ?p ?sLabel
    WHERE {{
        ?s ?p <{uri}> .
        OPTIONAL {{ ?s rdfs:label ?sLabel . FILTER(lang(?sLabel) = "en" || lang(?sLabel) = "") }}
    }}
    LIMIT 50
    """
    return sparql_query(query)


# =============================================================================
# ROUTES
# =============================================================================

@app.route("/")
def home():
    """Page d'accueil avec statistiques."""
    # Récupérer les statistiques
    stats_query = """
    SELECT 
        (COUNT(*) AS ?triples)
    WHERE { ?s ?p ?o . }
    """
    
    types_query = """
    SELECT ?type (COUNT(?s) AS ?count)
    WHERE { ?s a ?type . }
    GROUP BY ?type
    ORDER BY DESC(?count)
    LIMIT 10
    """
    
    stats = sparql_query(stats_query)
    types = sparql_query(types_query)
    
    triples = "N/A"
    if "results" in stats:
        triples = stats["results"]["bindings"][0]["triples"]["value"]
    
    types_html = ""
    if "results" in types:
        for binding in types["results"]["bindings"]:
            type_name = binding["type"]["value"].split("/")[-1].split("#")[-1]
            count = binding["count"]["value"]
            types_html += f'<tr><td>{type_name}</td><td>{count}</td></tr>'
    
    content = f"""
    <div class="card">
        <h2>📊 Statistiques</h2>
        <div class="stats">
            <div class="stat-box">
                <div class="number">{triples}</div>
                <div class="label">Triplets RDF</div>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h2>📂 Types d'entités</h2>
        <table>
            <tr><th>Type</th><th>Nombre</th></tr>
            {types_html}
        </table>
    </div>
    
    <div class="card">
        <h2>🔍 Exploration rapide</h2>
        <p>Quelques exemples d'entités :</p>
        <ul style="list-style: none; padding: 10px 0;">
            <li style="margin: 10px 0;">
                <a href="/entity/Gandalf">👤 Gandalf</a> - 
                <a href="/entity/Frodo_Baggins">👤 Frodo Baggins</a> - 
                <a href="/entity/Aragorn_II">👤 Aragorn II</a>
            </li>
            <li style="margin: 10px 0;">
                <a href="/entity/Rivendell">📍 Rivendell</a> - 
                <a href="/entity/Mordor">📍 Mordor</a> - 
                <a href="/entity/Gondor">📍 Gondor</a>
            </li>
        </ul>
    </div>
    """
    
    return render_template_string(BASE_TEMPLATE, title="Accueil", content=content)


@app.route("/sparql", methods=["GET", "POST"])
def sparql_interface():
    """Interface SPARQL."""
    results_html = ""
    query_text = request.form.get("query", "")
    
    if request.method == "POST" and query_text:
        results = sparql_query(query_text)
        
        if "error" in results:
            results_html = f'<div class="card"><p style="color: #ff6b6b;">❌ {results["error"]}</p></div>'
        elif "results" in results:
            bindings = results["results"]["bindings"]
            vars = results["head"]["vars"]
            
            if bindings:
                table_html = "<table><tr>"
                for var in vars:
                    table_html += f"<th>{var}</th>"
                table_html += "</tr>"
                
                for binding in bindings[:100]:
                    table_html += "<tr>"
                    for var in vars:
                        value = binding.get(var, {}).get("value", "")
                        # Créer des liens pour les URIs
                        if value.startswith("http"):
                            if "tolkiengateway.net/wiki/" in value:
                                name = value.split("/wiki/")[-1]
                                value = f'<a href="/entity/{name}">{unquote(name)}</a>'
                            else:
                                value = f'<a href="{value}" target="_blank">{value[-50:]}</a>'
                        table_html += f"<td>{value}</td>"
                    table_html += "</tr>"
                
                table_html += "</table>"
                results_html = f'<div class="card"><h3>Résultats ({len(bindings)})</h3>{table_html}</div>'
            else:
                results_html = '<div class="card"><p>Aucun résultat</p></div>'
    
    default_query = """SELECT ?s ?p ?o
WHERE {
  ?s a tolkien_class:Character .
  ?s rdfs:label ?o .
  FILTER(lang(?o) = "en")
}
LIMIT 20"""
    
    content = f"""
    <div class="card">
        <h2>🔍 Interface SPARQL</h2>
        <form method="POST">
            <textarea name="query" placeholder="Entrez votre requête SPARQL...">{query_text or default_query}</textarea>
            <button type="submit">▶ Exécuter</button>
        </form>
        <p style="margin-top: 10px; color: #888;">
            Préfixes disponibles : tolkien:, tolkien_prop:, tolkien_class:, meccg:, meccg_prop:, rdfs:, owl:
        </p>
    </div>
    {results_html}
    """
    
    return render_template_string(BASE_TEMPLATE, title="SPARQL", content=content)


@app.route("/entity/<path:name>")
def entity_page(name: str):
    """Page d'une entité spécifique."""
    uri = f"https://tolkiengateway.net/wiki/{name}"
    
    # Récupérer les données
    data = get_entity_data(uri)
    reverse = get_reverse_links(uri)
    
    if "error" in data:
        content = f'<div class="card"><h2>❌ Erreur</h2><p>{data["error"]}</p></div>'
        return render_template_string(BASE_TEMPLATE, title="Erreur", content=content)
    
    # Organiser les propriétés
    labels = []
    types = []
    alignments = []
    properties = []
    
    if "results" in data:
        for binding in data["results"]["bindings"]:
            pred = binding["p"]["value"]
            obj = binding["o"]["value"]
            lang = binding.get("lang", {}).get("value", "")
            
            pred_name = pred.split("/")[-1].split("#")[-1]
            
            if "label" in pred.lower():
                labels.append((obj, lang))
            elif "type" in pred.lower() or "rdf-syntax" in pred:
                type_name = obj.split("/")[-1].split("#")[-1]
                types.append((type_name, obj))
            elif "sameAs" in pred:
                alignments.append(obj)
            else:
                properties.append((pred_name, obj, pred))
    
    # Construire le HTML
    types_html = "".join([f'<span class="type-badge">{t[0]}</span>' for t in types])
    
    labels_html = ""
    for label, lang in labels:
        lang_tag = f'<span class="lang-tag">{lang}</span>' if lang else ""
        labels_html += f"<li>{label}{lang_tag}</li>"
    
    alignments_html = ""
    for uri in alignments:
        source = "DBpedia" if "dbpedia" in uri else "Wikidata" if "wikidata" in uri else "YAGO" if "yago" in uri else "External"
        alignments_html += f'<a href="{uri}" target="_blank" class="external-link">{source}</a>'
    
    props_html = "<table>"
    for pred_name, obj, full_pred in properties[:30]:
        obj_display = obj
        if obj.startswith("https://tolkiengateway.net/wiki/"):
            obj_name = obj.split("/wiki/")[-1]
            obj_display = f'<a href="/entity/{obj_name}">{unquote(obj_name)}</a>'
        elif obj.startswith("http"):
            obj_display = f'<a href="{obj}" target="_blank">{obj[-50:]}</a>'
        props_html += f"<tr><td><strong>{pred_name}</strong></td><td>{obj_display}</td></tr>"
    props_html += "</table>"
    
    # Liens inverses
    reverse_html = ""
    if "results" in reverse and reverse["results"]["bindings"]:
        reverse_html = "<h3>🔗 Référencé par</h3><ul>"
        for binding in reverse["results"]["bindings"][:20]:
            s = binding["s"]["value"]
            if "tolkiengateway.net/wiki/" in s:
                s_name = s.split("/wiki/")[-1]
                label = binding.get("sLabel", {}).get("value", unquote(s_name))
                reverse_html += f'<li><a href="/entity/{s_name}">{label}</a></li>'
        reverse_html += "</ul>"
    
    content = f"""
    <div class="card">
        <h2>📖 {unquote(name).replace("_", " ")}</h2>
        <p class="uri">{uri}</p>
        
        <h3>Types</h3>
        <div>{types_html or "Aucun type"}</div>
        
        <h3>Labels</h3>
        <ul style="list-style: none;">{labels_html or "<li>Aucun label</li>"}</ul>
        
        <h3>Alignements externes</h3>
        <div>{alignments_html or "Aucun alignement"}</div>
        
        <h3>Propriétés</h3>
        {props_html}
        
        {reverse_html}
    </div>
    
    <div class="card">
        <h2>📥 Télécharger</h2>
        <p>
            <a href="/entity/{name}/rdf" target="_blank">RDF/Turtle</a> |
            <a href="/entity/{name}/json" target="_blank">JSON-LD</a>
        </p>
    </div>
    """
    
    return render_template_string(BASE_TEMPLATE, title=unquote(name), content=content)


@app.route("/entity/<path:name>/rdf")
def entity_rdf(name: str):
    """Retourne les données RDF d'une entité."""
    uri = f"https://tolkiengateway.net/wiki/{name}"
    query = f"CONSTRUCT {{ <{uri}> ?p ?o }} WHERE {{ <{uri}> ?p ?o }}"
    
    results = sparql_query(query, format="turtle")
    
    if "raw" in results:
        return Response(results["raw"], mimetype="text/turtle")
    return jsonify({"error": "Could not retrieve RDF data"}), 500


@app.route("/entity/<path:name>/json")
def entity_json(name: str):
    """Retourne les données JSON d'une entité."""
    uri = f"https://tolkiengateway.net/wiki/{name}"
    data = get_entity_data(uri)
    
    if "error" in data:
        return jsonify(data), 500
    
    # Transformer en format plus lisible
    entity = {"@id": uri, "properties": {}}
    
    if "results" in data:
        for binding in data["results"]["bindings"]:
            pred = binding["p"]["value"]
            obj = binding["o"]["value"]
            pred_name = pred.split("/")[-1].split("#")[-1]
            
            if pred_name not in entity["properties"]:
                entity["properties"][pred_name] = []
            entity["properties"][pred_name].append(obj)
    
    return jsonify(entity)


@app.route("/browse/<category>")
def browse(category: str):
    """Page de navigation par catégorie."""
    queries = {
        "characters": """
            SELECT ?entity ?name
            WHERE {
                ?entity a tolkien_class:Character .
                ?entity rdfs:label ?name .
                FILTER(lang(?name) = "en" || lang(?name) = "")
            }
            ORDER BY ?name
            LIMIT 100
        """,
        "locations": """
            SELECT ?entity ?name
            WHERE {
                { ?entity a tolkien_class:Location } UNION { ?entity a tolkien_class:Kingdom }
                ?entity rdfs:label ?name .
                FILTER(lang(?name) = "en" || lang(?name) = "")
            }
            ORDER BY ?name
            LIMIT 100
        """,
        "cards": """
            SELECT ?entity ?name ?type
            WHERE {
                ?entity meccg_prop:cardType ?type .
                ?entity rdfs:label ?name .
                FILTER(lang(?name) = "en" || lang(?name) = "")
            }
            ORDER BY ?name
            LIMIT 100
        """
    }
    
    titles = {
        "characters": "👤 Personnages",
        "locations": "📍 Lieux",
        "cards": "🎴 Cartes MECCG"
    }
    
    if category not in queries:
        return redirect("/")
    
    results = sparql_query(queries[category])
    
    items_html = ""
    if "results" in results:
        for binding in results["results"]["bindings"]:
            uri = binding["entity"]["value"]
            name = binding["name"]["value"]
            
            if "tolkiengateway.net/wiki/" in uri:
                entity_name = uri.split("/wiki/")[-1]
                items_html += f'<div class="result-item"><a href="/entity/{entity_name}">{name}</a></div>'
            elif "meccg.net" in uri:
                items_html += f'<div class="result-item">{name}</div>'
    
    content = f"""
    <div class="card">
        <h2>{titles.get(category, category)}</h2>
        <div class="search-results">
            {items_html or "<p>Aucun résultat</p>"}
        </div>
    </div>
    """
    
    return render_template_string(BASE_TEMPLATE, title=titles.get(category), content=content)


@app.route("/search")
def search():
    """Page de recherche."""
    query_text = request.args.get("q", "")
    results_html = ""
    
    if query_text:
        search_query = f"""
        SELECT DISTINCT ?entity ?name ?type
        WHERE {{
            ?entity rdfs:label ?name .
            OPTIONAL {{ ?entity a ?type }}
            FILTER(CONTAINS(LCASE(STR(?name)), LCASE("{query_text}")))
        }}
        LIMIT 50
        """
        
        results = sparql_query(search_query)
        
        if "results" in results and results["results"]["bindings"]:
            for binding in results["results"]["bindings"]:
                uri = binding["entity"]["value"]
                name = binding["name"]["value"]
                type_val = binding.get("type", {}).get("value", "")
                type_name = type_val.split("/")[-1].split("#")[-1] if type_val else ""
                
                if "tolkiengateway.net/wiki/" in uri:
                    entity_name = uri.split("/wiki/")[-1]
                    results_html += f'''
                    <div class="result-item">
                        <a href="/entity/{entity_name}">{name}</a>
                        {f'<span class="type-badge">{type_name}</span>' if type_name else ""}
                    </div>
                    '''
        else:
            results_html = "<p>Aucun résultat trouvé</p>"
    
    content = f"""
    <div class="card">
        <h2>🔎 Recherche</h2>
        <form method="GET">
            <input type="text" name="q" value="{query_text}" placeholder="Rechercher une entité...">
            <button type="submit">Rechercher</button>
        </form>
    </div>
    
    {f'<div class="card"><h3>Résultats pour "{query_text}"</h3><div class="search-results">{results_html}</div></div>' if query_text else ""}
    """
    
    return render_template_string(BASE_TEMPLATE, title="Recherche", content=content)


@app.route("/api/sparql", methods=["POST"])
def api_sparql():
    """API SPARQL pour requêtes programmatiques."""
    query = request.form.get("query") or request.json.get("query")
    
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    results = sparql_query(query)
    return jsonify(results)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  🏔️  TOLKIEN KNOWLEDGE GRAPH - Interface Web")
    print("=" * 60)
    print(f"\n📡 Fuseki endpoint: {SPARQL_ENDPOINT}")
    print("🌐 Interface web: http://localhost:5000")
    print("\nRoutes disponibles:")
    print("  /           - Page d'accueil")
    print("  /sparql     - Interface SPARQL")
    print("  /entity/X   - Page d'une entité")
    print("  /browse/... - Navigation par catégorie")
    print("  /search     - Recherche")
    print("  /api/sparql - API SPARQL (POST)")
    print("\n" + "=" * 60 + "\n")
    
    app.run(debug=True, port=5000)
