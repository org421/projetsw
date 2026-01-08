#!/usr/bin/env python3
"""
Tolkien Knowledge Graph - Linked Data Interface (Enhanced UI/UX)
Flask server with:
- Content negotiation (Turtle/HTML)
- Language tags with colors
- Card data differentiation
- Dropdown filters (language, data source)
- Infobox type navigation
- SPARQL queries with reasoning
"""

from flask import Flask, request, Response, render_template_string, redirect, url_for, jsonify
from SPARQLWrapper import SPARQLWrapper, JSON, N3
from urllib.parse import quote, unquote
import re

# =============================================================================
# CONFIGURATION
# =============================================================================

app = Flask(__name__)

# Update these URLs to match your Fuseki setup
FUSEKI_ENDPOINT = "http://localhost:3030/tolkien/query"
FUSEKI_UPDATE = "http://localhost:3030/tolkien/update"

NAMESPACES = {
    "tolkien": "https://tolkiengateway.net/wiki/",
    "tolkien_prop": "https://tolkiengateway.net/wiki/Property:",
    "tolkien_class": "https://tolkiengateway.net/wiki/Class:",
    "schema": "http://schema.org/",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "dbpedia": "http://dbpedia.org/resource/",
    "wikidata": "http://www.wikidata.org/entity/",
    "yago": "http://yago-knowledge.org/resource/",
    "meccg": "https://tolkiengateway.net/wiki/MECCG/",
    "meccg_prop": "https://tolkiengateway.net/wiki/MECCG/Property:",
    "meccg_class": "https://tolkiengateway.net/wiki/MECCG/Class:",
}

SPARQL_PREFIXES = "\n".join([f"PREFIX {k}: <{v}>" for k, v in NAMESPACES.items()])
BASE_URI = "https://tolkiengateway.net/wiki/"

# Infobox types for navigation
INFOBOX_TYPES = [
    ("Character", "Characters"),
    ("Location", "Locations"),
    ("Kingdom", "Kingdoms"),
    ("Book", "Books"),
    ("Film", "Films"),
    ("Battle", "Battles"),
    ("Object", "Objects"),
    ("Race", "Races"),
    ("Song", "Songs"),
]

# Language colors
LANG_COLORS = {
    "en": "#3498db",  # Blue
    "fr": "#e74c3c",  # Red
    "de": "#f39c12",  # Orange
    "es": "#9b59b6",  # Purple
    "it": "#1abc9c",  # Teal
    "nl": "#e67e22",
    "pl": "#c0392b",
    "ru": "#2980b9",
    "ja": "#8e44ad",
    "zh": "#16a085",
}

# Source colors
SOURCE_COLORS = {
    "card": "#e74c3c",     # Red
    "wiki": "#3498db",     # Blue
    "external": "#9b59b6", # Purple
    "inferred": "#f39c12", # Orange
}


# =============================================================================
# SPARQL QUERIES
# =============================================================================

def get_sparql():
    sparql = SPARQLWrapper(FUSEKI_ENDPOINT)
    return sparql


def query_entity_description(entity_uri: str) -> list:
    sparql = get_sparql()
    # Simple query to get all direct properties
    query = f"""
    {SPARQL_PREFIXES}
    SELECT ?predicate ?object ?isIncoming
    WHERE {{
        {{ <{entity_uri}> ?predicate ?object . BIND(false AS ?isIncoming) }}
        UNION
        {{ ?object ?predicate <{entity_uri}> . BIND(true AS ?isIncoming) }}
    }}
    """
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        return sparql.query().convert()["results"]["bindings"]
    except:
        return []


def query_all_classes_with_superclasses(entity_uri: str) -> list:
    """Gets direct classes and inferred superclasses"""
    sparql = get_sparql()
    query = f"""
    {SPARQL_PREFIXES}
    SELECT DISTINCT ?class ?classLabel ?isDirect
    WHERE {{
        {{ <{entity_uri}> rdf:type ?class . BIND(true AS ?isDirect) }}
        UNION
        {{ <{entity_uri}> rdf:type ?directClass . ?directClass rdfs:subClassOf+ ?class . BIND(false AS ?isDirect) }}
        OPTIONAL {{ ?class rdfs:label ?classLabel }}
    }}
    ORDER BY DESC(?isDirect)
    """
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        return sparql.query().convert()["results"]["bindings"]
    except:
        return []


def query_sameas_links(entity_uri: str) -> list:
    sparql = get_sparql()
    query = f"""
    {SPARQL_PREFIXES}
    SELECT ?sameAs WHERE {{ <{entity_uri}> owl:sameAs ?sameAs . }}
    """
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        return [r["sameAs"]["value"] for r in sparql.query().convert()["results"]["bindings"]]
    except:
        return []


def query_entity_turtle(entity_uri: str) -> str:
    sparql = get_sparql()
    query = f"""
    {SPARQL_PREFIXES}
    CONSTRUCT {{ <{entity_uri}> ?p ?o . ?s ?p2 <{entity_uri}> . }}
    WHERE {{ {{ <{entity_uri}> ?p ?o . }} UNION {{ ?s ?p2 <{entity_uri}> . }} }}
    """
    sparql.setQuery(query)
    sparql.setReturnFormat(N3)
    try:
        results = sparql.query().convert()
        # Handle bytes vs string depending on version
        return results.decode('utf-8') if isinstance(results, bytes) else str(results)
    except:
        return f"# No data for <{entity_uri}>"


def search_entities(query_text: str, limit: int = 20) -> list:
    sparql = get_sparql()
    query = f"""
    {SPARQL_PREFIXES}
    SELECT DISTINCT ?entity ?label ?type
    WHERE {{
        ?entity rdfs:label ?label .
        FILTER(CONTAINS(LCASE(STR(?label)), LCASE("{query_text}")))
        OPTIONAL {{ ?entity rdf:type ?type }}
    }}
    LIMIT {limit}
    """
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        return sparql.query().convert()["results"]["bindings"]
    except:
        return []


def get_entities_by_type(entity_type: str, limit: int = 50) -> list:
    sparql = get_sparql()
    query = f"""
    {SPARQL_PREFIXES}
    SELECT DISTINCT ?entity ?label
    WHERE {{
        ?entity rdf:type tolkien_class:{entity_type} .
        ?entity rdfs:label ?label .
        FILTER(LANG(?label) = "en" || LANG(?label) = "")
    }}
    LIMIT {limit}
    """
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        return sparql.query().convert()["results"]["bindings"]
    except:
        return []


def get_statistics() -> dict:
    sparql = get_sparql()
    stats = {}
    
    # Counts
    for key, query in [
        ("total_triples", "SELECT (COUNT(*) AS ?c) WHERE { ?s ?p ?o }"),
        ("entities", "SELECT (COUNT(DISTINCT ?s) AS ?c) WHERE { ?s ?p ?o }"),
    ]:
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        try:
            stats[key] = sparql.query().convert()["results"]["bindings"][0]["c"]["value"]
        except:
            stats[key] = "N/A"
    
    # Top types
    query = f"""
    {SPARQL_PREFIXES}
    SELECT ?type (COUNT(?s) AS ?count) WHERE {{ ?s rdf:type ?type }} GROUP BY ?type ORDER BY DESC(?count) LIMIT 10
    """
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        stats["types"] = [(r["type"]["value"], r["count"]["value"]) for r in sparql.query().convert()["results"]["bindings"]]
    except:
        stats["types"] = []
    
    return stats


# =============================================================================
# UTILITIES
# =============================================================================

def uri_to_label(uri: str) -> str:
    if not uri:
        return ""
    label = uri.split("#")[-1] if "#" in uri else uri.split("/")[-1]
    return unquote(label).replace("_", " ")

def get_entity_name(uri: str) -> str:
    if uri.startswith(BASE_URI):
        return unquote(uri[len(BASE_URI):].replace("_", " "))
    return uri_to_label(uri)

def categorize_uri(uri: str) -> str:
    if "dbpedia.org" in uri: return "dbpedia"
    elif "wikidata.org" in uri: return "wikidata"
    elif "yago-knowledge.org" in uri: return "yago"
    elif "MECCG" in uri or "meccg" in uri.lower(): return "card"
    elif "tolkiengateway.net" in uri: return "wiki"
    return "other"

def get_data_source(predicate: str, value: str = "") -> str:
    """Determines if data comes from Wiki, Cards, or External links"""
    pred_lower = predicate.lower()
    val_lower = value.lower() if value else ""
    
    if "meccg" in pred_lower or "meccg" in val_lower or "card" in pred_lower:
        return "card"
    elif "sameas" in pred_lower:
        return "external"
    elif "subclassof" in pred_lower:
        return "inferred"
    return "wiki"

def parse_accept_header(accept: str) -> str:
    if not accept: return "html"
    accept_lower = accept.lower()
    if "text/turtle" in accept_lower or "application/x-turtle" in accept_lower: return "turtle"
    if "application/n-triples" in accept_lower: return "ntriples"
    return "html"

def get_lang_color(lang: str) -> str:
    return LANG_COLORS.get(lang, "#95a5a6") # Default Grey

def get_source_color(source: str) -> str:
    return SOURCE_COLORS.get(source, "#95a5a6")

# =============================================================================
# HTML TEMPLATES (UI/UX)
# =============================================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - Tolkien KG</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f8f9fa;
        }
        
        /* --- Header & Nav --- */
        header {
            background: linear-gradient(135deg, #1a472a 0%, #2d5a3d 100%);
            color: white;
            padding: 0.8rem 2rem;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }
        
        .header-content {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        header h1 a {
            color: white;
            text-decoration: none;
            font-size: 1.4rem;
            font-weight: 700;
        }
        
        nav { display: flex; align-items: center; gap: 1.5rem; }
        nav a { color: #e0f2e0; text-decoration: none; font-size: 0.95rem; font-weight: 500; transition: color 0.2s; }
        nav a:hover { color: white; }
        
        /* Dropdown Menu */
        .dropdown { position: relative; display: inline-block; }
        .dropdown-btn {
            background: rgba(255,255,255,0.15);
            color: white;
            padding: 0.5rem 1rem;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
            display: flex; align-items: center; gap: 0.5rem;
        }
        .dropdown-btn:hover { background: rgba(255,255,255,0.25); }
        .dropdown-content {
            display: none;
            position: absolute;
            top: 100%; left: 0;
            background: white;
            min-width: 200px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            border-radius: 8px;
            overflow: hidden;
            z-index: 200;
            margin-top: 0.5rem;
        }
        .dropdown:hover .dropdown-content { display: block; }
        .dropdown-content a {
            display: block;
            padding: 0.7rem 1.2rem;
            color: #333;
            border-bottom: 1px solid #f0f0f0;
        }
        .dropdown-content a:hover { background: #f0f7f0; color: #1a472a; }

        /* --- Main Layout --- */
        .container { max-width: 1400px; margin: 0 auto; padding: 2rem; }
        
        /* --- Filters --- */
        .filters {
            background: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            display: flex;
            gap: 2rem;
            margin-bottom: 1.5rem;
            border-left: 5px solid #1a472a;
        }
        .filter-group { display: flex; flex-direction: column; gap: 0.3rem; }
        .filter-group label { font-size: 0.8rem; font-weight: 600; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }
        .filter-group select {
            padding: 0.5rem 1rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 0.9rem;
            min-width: 180px;
        }

        /* --- Entity Header --- */
        .entity-header {
            background: white;
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            display: flex;
            gap: 2rem;
        }
        .entity-image img {
            width: 200px;
            border-radius: 8px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.15);
        }
        .entity-info { flex: 1; }
        .entity-info h2 { font-size: 2.2rem; color: #1a472a; margin-bottom: 0.5rem; }
        .entity-uri { font-family: monospace; color: #888; font-size: 0.85rem; margin-bottom: 1rem; word-break: break-all; }
        
        /* --- Tags --- */
        .tag {
            display: inline-flex; align-items: center; justify-content: center;
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 700;
            color: white;
            text-transform: uppercase;
            margin-right: 0.4rem;
            min-width: 30px;
            vertical-align: middle;
        }
        .tag-source-card { background-color: #e74c3c; } /* Red */
        .tag-source-wiki { background-color: #3498db; } /* Blue */
        .tag-source-external { background-color: #9b59b6; } /* Purple */
        .tag-source-inferred { background-color: #f39c12; } /* Orange */

        .type-badge {
            display: inline-block;
            background: #e8f5e9;
            color: #2e7d32;
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            margin-bottom: 1rem;
            margin-right: 0.5rem;
        }

        /* --- Tables --- */
        .section-card {
            background: white;
            border-radius: 10px;
            margin-bottom: 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            overflow: hidden;
        }
        .section-header {
            background: #f8f9fa;
            padding: 1rem 1.5rem;
            border-bottom: 1px solid #eee;
            font-weight: 700;
            color: #2c3e50;
            font-size: 1.1rem;
        }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 1rem 1.5rem; text-align: left; border-bottom: 1px solid #f0f0f0; }
        th { width: 30%; background: #fafafa; color: #666; font-weight: 600; font-size: 0.9rem; }
        td a { color: #2980b9; text-decoration: none; }
        td a:hover { text-decoration: underline; }
        
        /* Logic for filtering visibility */
        tr[data-visible="false"] { display: none; }

        /* --- Footer --- */
        footer {
            text-align: center;
            padding: 2rem;
            color: #888;
            font-size: 0.9rem;
            border-top: 1px solid #eee;
            margin-top: 2rem;
        }

        /* --- Grid for browsing --- */
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1rem; }
        .card { background: white; padding: 1.2rem; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .card a { color: #1a472a; font-weight: 600; text-decoration: none; }

        /* Stats */
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .stat-box { background: white; padding: 1.5rem; text-align: center; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
        .stat-num { font-size: 2rem; font-weight: bold; color: #1a472a; }
        .stat-label { color: #777; font-size: 0.9rem; margin-top: 0.5rem; }
    </style>
</head>
<body>
    <header>
        <div class="header-content">
            <h1><a href="/">🏔️ Tolkien Knowledge Graph</a></h1>
            <nav>
                <a href="/">Home</a>
                
                <div class="dropdown">
                    <button class="dropdown-btn">Browse by Type ▾</button>
                    <div class="dropdown-content">
                        {% for type_id, type_name in infobox_types %}
                        <a href="/browse/{{ type_id }}">{{ type_name }}</a>
                        {% endfor %}
                    </div>
                </div>
                
                <a href="/search">Search</a>
                <a href="/sparql">SPARQL</a>
            </nav>
        </div>
    </header>
    
    <div class="container">
        {{ content | safe }}
    </div>
    
    <footer>
        <p>Tolkien Knowledge Graph Interface</p>
        <p>Data linked from Wiki, MECCG Cards, and External DBs.</p>
    </footer>

    <script>
        // UI Filtering Logic
        function updateFilters() {
            const langSelect = document.getElementById('langFilter');
            const sourceSelect = document.getElementById('sourceFilter');
            
            const selectedLang = langSelect ? langSelect.value : 'all';
            const selectedSource = sourceSelect ? sourceSelect.value : 'all';
            
            const rows = document.querySelectorAll('tr[data-filter]');
            
            rows.forEach(row => {
                const rowLang = row.dataset.lang || 'default';
                const rowSource = row.dataset.source;
                
                const langMatch = (selectedLang === 'all') || (rowLang === selectedLang) || (rowLang === 'default' && selectedLang === 'all');
                const sourceMatch = (selectedSource === 'all') || (rowSource === selectedSource);
                
                if (langMatch && sourceMatch) {
                    row.style.display = 'table-row';
                } else {
                    row.style.display = 'none';
                }
            });
        }
    </script>
</body>
</html>
"""

HOME_CONTENT = """
<div style="text-align: center; margin-bottom: 3rem;">
    <h2 style="font-size: 2.5rem; color: #1a472a; margin-bottom: 1rem;">Welcome to Middle-earth Data</h2>
    <p style="color: #666; max-width: 600px; margin: 0 auto;">Explore the semantic connections between characters, locations, and objects from Tolkien's Legendarium. Combining Wiki data and Collectible Card Game statistics.</p>
</div>

<div class="stats-grid">
    <div class="stat-box">
        <div class="stat-num">{{ stats.total_triples }}</div>
        <div class="stat-label">Total Facts (Triples)</div>
    </div>
    <div class="stat-box">
        <div class="stat-num">{{ stats.entities }}</div>
        <div class="stat-label">Total Entities</div>
    </div>
</div>

<div class="section-card">
    <div class="section-header">🔍 Quick Search</div>
    <div style="padding: 1.5rem;">
        <form action="/search" method="get" style="display: flex; gap: 1rem;">
            <input type="text" name="q" placeholder="e.g. Gandalf, The One Ring, Shire..." style="flex: 1; padding: 0.8rem; border: 2px solid #ddd; border-radius: 6px;">
            <button type="submit" style="padding: 0.8rem 2rem; background: #1a472a; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold;">Search</button>
        </form>
    </div>
</div>

<div class="grid">
    <div class="card">
        <h3>Example Entities</h3>
        <ul style="margin-top: 1rem; padding-left: 1.2rem;">
            <li><a href="/resource/Gandalf">Gandalf</a> (Character)</li>
            <li><a href="/resource/Rivendell">Rivendell</a> (Location)</li>
            <li><a href="/resource/Narya">Narya</a> (Ring of Power)</li>
            <li><a href="/resource/Smaug">Smaug</a> (Dragon)</li>
        </ul>
    </div>
    <div class="card">
        <h3>Top Types</h3>
        <ul style="margin-top: 1rem; padding-left: 1.2rem;">
            {% for type_uri, count in stats.types %}
            <li><a href="{{ type_uri }}">{{ type_uri | uri_label }}</a> ({{ count }})</li>
            {% endfor %}
        </ul>
    </div>
</div>
"""

ENTITY_CONTENT = """
<div class="entity-header">
    {% if image %}
    <div class="entity-image">
        <img src="{{ image }}" alt="{{ name }}">
    </div>
    {% endif %}
    <div class="entity-info">
        <h2>{{ name }}</h2>
        <div class="entity-uri">{{ uri }}</div>
        
        <div>
            {% for cls in classes %}
            <span class="type-badge">
                {{ cls.label }}{% if not cls.direct %} (Inferred){% endif %}
            </span>
            {% endfor %}
        </div>
        
        {% if description %}
        <p style="margin-top: 1rem; color: #555; line-height: 1.8;">{{ description }}</p>
        {% endif %}
        
        <div style="margin-top: 1.5rem; font-size: 0.9rem;">
            <strong>Download Data: </strong>
            <a href="{{ request_path }}?format=turtle" style="color: #2980b9; margin-right: 1rem;">Turtle (.ttl)</a>
            <a href="{{ request_path }}?format=ntriples" style="color: #2980b9;">N-Triples (.nt)</a>
        </div>
    </div>
</div>

<div class="filters">
    <div class="filter-group">
        <label for="langFilter">Language</label>
        <select id="langFilter" onchange="updateFilters()">
            <option value="all">All Languages</option>
            {% for lang in available_langs %}
            <option value="{{ lang }}">{{ lang | upper }}</option>
            {% endfor %}
        </select>
    </div>
    <div class="filter-group">
        <label for="sourceFilter">Data Source</label>
        <select id="sourceFilter" onchange="updateFilters()">
            <option value="all">All Sources</option>
            <option value="wiki">Wiki Data</option>
            <option value="card">Card Data (MECCG)</option>
            <option value="external">External Links</option>
        </select>
    </div>
</div>

{% if labels %}
<div class="section-card">
    <div class="section-header">🏷️ Names & Labels</div>
    <table>
        <tr>
            <th>Value</th>
            <th>Metadata (Lang / Source)</th>
        </tr>
        {% for label in labels %}
        <tr data-filter="true" data-lang="{{ label.lang }}" data-source="wiki">
            <td style="font-weight: 500;">{{ label.value }}</td>
            <td>
                {% if label.lang %}
                <span class="tag" style="background-color: {{ label.color }};">{{ label.lang | upper }}</span>
                {% endif %}
                <span class="tag tag-source-wiki">Wiki</span>
            </td>
        </tr>
        {% endfor %}
    </table>
</div>
{% endif %}

{% if outgoing %}
<div class="section-card">
    <div class="section-header">➡️ Properties</div>
    <table>
        <tr>
            <th>Property</th>
            <th>Value</th>
        </tr>
        {% for prop in outgoing %}
        <tr data-filter="true" data-lang="{{ prop.lang }}" data-source="{{ prop.source }}">
            <td>
                <span class="tag tag-source-{{ prop.source }}">{{ prop.source | upper }}</span>
                <a href="{{ prop.predicate }}">{{ prop.predicate | uri_label }}</a>
            </td>
            <td>
                {% if prop.is_uri %}
                    <a href="/resource/{{ prop.value | uri_to_path }}">{{ prop.value | uri_label }}</a>
                    {% if prop.external %}
                    <span style="font-size: 0.8rem; color: #999;">↗</span>
                    {% endif %}
                {% else %}
                    {{ prop.value }}
                    {% if prop.lang %}
                    <span class="tag" style="background-color: {{ prop.lang_color }}; margin-left: 0.5rem;">{{ prop.lang | upper }}</span>
                    {% endif %}
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </table>
</div>
{% endif %}

{% if incoming %}
<div class="section-card">
    <div class="section-header">⬅️ Referenced By</div>
    <table>
        <tr>
            <th>Entity</th>
            <th>Property</th>
        </tr>
        {% for prop in incoming %}
        <tr data-filter="true" data-source="{{ prop.source }}">
            <td>
                <span class="tag tag-source-{{ prop.source }}">{{ prop.source | upper }}</span>
                <a href="/resource/{{ prop.subject | uri_to_path }}">{{ prop.subject | uri_label }}</a>
            </td>
            <td><a href="{{ prop.predicate }}">{{ prop.predicate | uri_label }}</a></td>
        </tr>
        {% endfor %}
    </table>
</div>
{% endif %}
"""

BROWSE_CONTENT = """
<div style="margin-bottom: 2rem;">
    <h2 style="color: #1a472a; margin-bottom: 0.5rem;">Browsing: {{ type_name }}</h2>
    <p style="color: #666;">Found {{ entities | length }} entities.</p>
</div>

<div class="grid">
    {% for e in entities %}
    <div class="card">
        <a href="/resource/{{ e.uri | uri_to_path }}">{{ e.label }}</a>
    </div>
    {% endfor %}
</div>

{% if not entities %}
<div style="padding: 2rem; background: white; border-radius: 8px; text-align: center;">No entities found for this type.</div>
{% endif %}
"""

SEARCH_CONTENT = """
<h2 style="margin-bottom: 1.5rem; color: #1a472a;">Search Results</h2>

<form action="/search" method="get" style="display: flex; gap: 1rem; margin-bottom: 2rem;">
    <input type="text" name="q" value="{{ query }}" placeholder="Search entities..." style="flex: 1; padding: 0.8rem; border: 2px solid #ddd; border-radius: 6px;">
    <button type="submit" style="padding: 0.8rem 2rem; background: #1a472a; color: white; border: none; border-radius: 6px; cursor: pointer;">Search</button>
</form>

{% if results %}
<div class="section-card">
    <table>
        <tr><th>Entity Name</th><th>Type</th></tr>
        {% for r in results %}
        <tr>
            <td><a href="/resource/{{ r.entity | uri_to_path }}">{{ r.label }}</a></td>
            <td>{{ r.type | uri_label if r.type else '-' }}</td>
        </tr>
        {% endfor %}
    </table>
</div>
{% elif query %}
<div style="padding: 2rem; background: white; border-radius: 8px; text-align: center; color: #c0392b;">No results found for "{{ query }}"</div>
{% endif %}
"""

SPARQL_CONTENT = """
<h2 style="margin-bottom: 1.5rem; color: #1a472a;">SPARQL Query Interface</h2>

<div class="section-card">
    <div style="padding: 1.5rem;">
        <p style="margin-bottom: 1rem;"><strong>Endpoint:</strong> <code>{{ endpoint }}</code></p>
        
        <form action="/sparql" method="get">
            <textarea name="query" rows="8" style="width: 100%; font-family: monospace; padding: 1rem; border: 1px solid #ddd; border-radius: 6px; background: #fdfdfd; font-size: 0.9rem;">{{ query or 'SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10' }}</textarea>
            <br><br>
            <button type="submit" style="padding: 0.8rem 2rem; background: #1a472a; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold;">Run Query</button>
        </form>
    </div>
</div>

{% if results %}
<div class="section-card">
    <div class="section-header">Results</div>
    <div style="overflow-x: auto;">
        <table>
            <tr>{% for v in variables %}<th>{{ v }}</th>{% endfor %}</tr>
            {% for row in results %}
            <tr>{% for v in variables %}<td>{{ row[v] | truncate(80) }}</td>{% endfor %}</tr>
            {% endfor %}
        </table>
    </div>
</div>
{% endif %}
"""


# =============================================================================
# JINJA FILTERS & CONTEXT
# =============================================================================

@app.template_filter('uri_label')
def uri_label_filter(uri):
    return uri_to_label(uri) if uri else ""

@app.template_filter('uri_to_path')
def uri_to_path_filter(uri):
    if not uri: return ""
    if uri.startswith(BASE_URI):
        return uri[len(BASE_URI):]
    return quote(uri_to_label(uri).replace(" ", "_"), safe="")

@app.template_filter('truncate')
def truncate_filter(value, length=80):
    s = str(value) if value else ""
    return s[:length-3] + "..." if len(s) > length else s

@app.context_processor
def inject_globals():
    return {"infobox_types": INFOBOX_TYPES}


# =============================================================================
# ROUTES
# =============================================================================

@app.route("/")
def home():
    stats = get_statistics()
    content = render_template_string(HOME_CONTENT, stats=stats)
    return render_template_string(HTML_TEMPLATE, title="Home", content=content)


@app.route("/resource/<path:entity_name>")
def resource(entity_name: str):
    entity_uri = BASE_URI + entity_name
    
    # Content Negotiation
    format_param = request.args.get("format", "")
    if format_param:
        output_format = format_param
    else:
        output_format = parse_accept_header(request.headers.get("Accept", ""))
    
    if output_format in ("turtle", "ttl"):
        return Response(query_entity_turtle(entity_uri), mimetype="text/turtle")
    if output_format == "ntriples":
        return Response(query_entity_turtle(entity_uri), mimetype="application/n-triples")
    
    # Get Data
    bindings = query_entity_description(entity_uri)
    
    if not bindings:
        content = "<div class='container'><h2>Entity not found: " + entity_name + "</h2></div>"
        return render_template_string(HTML_TEMPLATE, title="Not Found", content=content), 404
    
    name = unquote(entity_name.replace("_", " "))
    description = None
    image = None
    labels = []
    outgoing = []
    incoming = []
    available_langs = set()
    
    # Process properties
    for b in bindings:
        pred = b["predicate"]["value"]
        obj = b["object"]
        is_incoming = b.get("isIncoming", {}).get("value") == "true"
        
        # Determine Source (Wiki vs Card vs External)
        source = get_data_source(pred, obj.get("value", ""))
        
        # Determine Language
        lang = obj.get("xml:lang", "")
        if lang: available_langs.add(lang)
        
        if is_incoming:
            incoming.append({
                "subject": obj["value"],
                "predicate": pred,
                "source": get_data_source(pred, obj["value"])
            })
        else:
            # Handle specific known properties for Header display
            if "label" in pred.lower() and "type" not in pred.lower():
                labels.append({
                    "value": obj["value"],
                    "lang": lang,
                    "color": get_lang_color(lang)
                })
            elif "description" in pred.lower() or "abstract" in pred.lower():
                description = obj["value"]
            elif "image" in pred.lower() or "depiction" in pred.lower():
                image = obj["value"]
            elif "type" not in pred.lower():
                outgoing.append({
                    "predicate": pred,
                    "value": obj["value"],
                    "is_uri": obj["type"] == "uri",
                    "lang": lang,
                    "lang_color": get_lang_color(lang) if lang else "",
                    "external": obj["type"] == "uri" and "tolkiengateway.net" not in obj["value"],
                    "source": source
                })
    
    # Get Classes (Types)
    classes_result = query_all_classes_with_superclasses(entity_uri)
    classes = [{
        "uri": c["class"]["value"],
        "label": c.get("classLabel", {}).get("value", uri_to_label(c["class"]["value"])),
        "direct": c.get("isDirect", {}).get("value") == "true"
    } for c in classes_result]
    
    content = render_template_string(ENTITY_CONTENT,
        name=name, uri=entity_uri, description=description, image=image,
        classes=classes, labels=labels,
        outgoing=outgoing, incoming=incoming,
        available_langs=sorted(available_langs),
        request_path=request.path)
    
    return render_template_string(HTML_TEMPLATE, title=name, content=content)


@app.route("/browse/<type_id>")
def browse(type_id: str):
    type_name = dict(INFOBOX_TYPES).get(type_id, type_id)
    raw = get_entities_by_type(type_id)
    entities = [{"uri": r["entity"]["value"], "label": r["label"]["value"]} for r in raw]
    
    content = render_template_string(BROWSE_CONTENT, type_id=type_id, type_name=type_name, entities=entities)
    return render_template_string(HTML_TEMPLATE, title=type_name, content=content)


@app.route("/search")
def search():
    query = request.args.get("q", "")
    results = []
    if query:
        raw = search_entities(query)
        results = [{"entity": r["entity"]["value"], "label": r["label"]["value"], "type": r.get("type", {}).get("value", "")} for r in raw]
    
    content = render_template_string(SEARCH_CONTENT, query=query, results=results)
    return render_template_string(HTML_TEMPLATE, title="Search", content=content)


@app.route("/sparql")
def sparql_page():
    query = request.args.get("query", "")
    results = []
    variables = []
    
    if query:
        try:
            sparql = get_sparql()
            sparql.setQuery(SPARQL_PREFIXES + "\n" + query)
            sparql.setReturnFormat(JSON)
            response = sparql.query().convert()
            variables = response["head"]["vars"]
            results = [{v: b.get(v, {}).get("value", "") for v in variables} for b in response["results"]["bindings"]]
        except Exception as e:
            results = [{"error": str(e)}]
            variables = ["error"]
    
    content = render_template_string(SPARQL_CONTENT,
        endpoint=FUSEKI_ENDPOINT, update_endpoint=FUSEKI_UPDATE,
        query=query, results=results, variables=variables)
    return render_template_string(HTML_TEMPLATE, title="SPARQL", content=content)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("Starting Tolkien KG Interface...")
    app.run(host="0.0.0.0", port=5000, debug=True)