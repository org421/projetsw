#!/usr/bin/env python3
"""
Tolkien Knowledge Graph - Linked Data Interface v2.2
Enhanced UI/UX with:
- Card data with colored tags
- Language tags (en, fr, de...)
- Dropdown filters (language, data source)
- Infobox type selector in navbar
- View Turtle/N-Triples in new tab (Inline view)
- Full relation display (including images in properties table)

Usage:
    1. Start Fuseki: fuseki-server --update --mem /tolkien
    2. Load tolkien_kg_complete.ttl via http://localhost:3030
    3. Run: python linked_data_server_v2.py
    4. Open http://localhost:5000/resource/Gandalf
"""

from flask import Flask, request, Response, render_template_string, redirect, url_for
from SPARQLWrapper import SPARQLWrapper, JSON, N3
from urllib.parse import quote, unquote

app = Flask(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

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
    "dbpedia": "http://dbpedia.org/resource/",
    "wikidata": "http://www.wikidata.org/entity/",
    "yago": "http://yago-knowledge.org/resource/",
    "meccg": "https://tolkiengateway.net/wiki/MECCG/",
    "meccg_prop": "https://tolkiengateway.net/wiki/MECCG/Property:",
    "meccg_class": "https://tolkiengateway.net/wiki/MECCG/Class:",
}

SPARQL_PREFIXES = "\n".join([f"PREFIX {k}: <{v}>" for k, v in NAMESPACES.items()])
BASE_URI = "https://tolkiengateway.net/wiki/"

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
    ("Actor", "Actors"),
]


# =============================================================================
# SPARQL QUERIES
# =============================================================================

def get_sparql():
    return SPARQLWrapper(FUSEKI_ENDPOINT)


def query_entity_description(entity_uri: str) -> list:
    sparql = get_sparql()
    # On utilise (owl:sameAs|^owl:sameAs)* pour inclure l'entité elle-même et ses alias
    query = f"""
    {SPARQL_PREFIXES}
    SELECT ?predicate ?object ?isIncoming
    WHERE {{
        {{ 
            <{entity_uri}> (owl:sameAs|^owl:sameAs)* ?subject .
            ?subject ?predicate ?object . 
            BIND(false AS ?isIncoming) 
        }}
        UNION
        {{ 
            ?object ?predicate ?target .
            ?target (owl:sameAs|^owl:sameAs)* <{entity_uri}> . 
            BIND(true AS ?isIncoming) 
        }}
    }}
    """
    # ... reste du code

def query_all_classes_with_superclasses(entity_uri: str) -> list:
    """Get all classes including superclasses via rdfs:subClassOf*"""
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


def query_card_data_for_entity(entity_uri: str) -> list:
    """Get MECCG card data linked to this entity"""
    sparql = get_sparql()
    query = f"""
    {SPARQL_PREFIXES}
    SELECT ?card ?predicate ?object
    WHERE {{
        ?card ?linkPred <{entity_uri}> .
        ?card a meccg_class:Card .
        ?card ?predicate ?object .
    }}
    """
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        return sparql.query().convert()["results"]["bindings"]
    except:
        return []


def generate_turtle_fallback(entity_uri: str) -> str:
    """
    Génère du Turtle manuellement si CONSTRUCT échoue.
    """
    bindings = query_entity_description(entity_uri)
    
    lines = [f"@prefix {k}: <{v}> ." for k, v in NAMESPACES.items()]
    lines.append("")
    lines.append(f"<{entity_uri}>")
    
    properties = []
    for binding in bindings:
        # Seulement les propriétés sortantes pour la description Turtle de base
        if binding.get("isIncoming", {}).get("value") == "false":
            pred = binding["predicate"]["value"]
            obj = binding["object"]
            
            if obj["type"] == "uri":
                properties.append(f"    <{pred}> <{obj['value']}>")
            else:
                value = obj["value"].replace('"', '\\"')
                lang = obj.get("xml:lang", "")
                if lang:
                    properties.append(f'    <{pred}> "{value}"@{lang}')
                else:
                    properties.append(f'    <{pred}> "{value}"')
    
    if properties:
        lines.append(" ;\n".join(properties) + " .")
    else:
        lines.append("    a owl:Thing . # No properties found via fallback")
    
    return "\n".join(lines)


def query_entity_turtle(entity_uri: str) -> str:
    """
    Tente une requête CONSTRUCT. Si le résultat est vide ou échoue,
    utilise le fallback manuel.
    """
    sparql = get_sparql()
    query = f"""
    {SPARQL_PREFIXES}
    CONSTRUCT {{ <{entity_uri}> ?p ?o . }}
    WHERE {{ <{entity_uri}> ?p ?o . }}
    """
    sparql.setQuery(query)
    sparql.setReturnFormat(N3)
    
    try:
        results = sparql.query().convert()
        turtle_data = results.decode('utf-8') if isinstance(results, bytes) else str(results)
        
        # Vérification simple : si on n'a que des préfixes, c'est vide
        if len(turtle_data.split('\n')) < len(NAMESPACES) + 3:
             return generate_turtle_fallback(entity_uri)
        return turtle_data
    except Exception as e:
        print(f"CONSTRUCT failed: {e}, using fallback.")
        return generate_turtle_fallback(entity_uri)


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


def query_entities_by_type(entity_type: str, limit: int = 50) -> list:
    sparql = get_sparql()
    query = f"""
    {SPARQL_PREFIXES}
    SELECT DISTINCT ?entity ?label
    WHERE {{
        ?entity a tolkien_class:{entity_type} .
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
    try:
        sparql.setQuery("SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }")
        sparql.setReturnFormat(JSON)
        stats["total_triples"] = sparql.query().convert()["results"]["bindings"][0]["count"]["value"]
    except:
        stats["total_triples"] = "N/A"
    try:
        sparql.setQuery("SELECT (COUNT(DISTINCT ?s) AS ?count) WHERE { ?s ?p ?o }")
        sparql.setReturnFormat(JSON)
        stats["entities"] = sparql.query().convert()["results"]["bindings"][0]["count"]["value"]
    except:
        stats["entities"] = "N/A"
    try:
        sparql.setQuery(f"{SPARQL_PREFIXES}\nSELECT ?type (COUNT(?s) AS ?count) WHERE {{ ?s rdf:type ?type }} GROUP BY ?type ORDER BY DESC(?count) LIMIT 10")
        sparql.setReturnFormat(JSON)
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


def categorize_uri(uri: str) -> str:
    if "dbpedia.org" in uri:
        return "dbpedia"
    elif "wikidata.org" in uri:
        return "wikidata"
    elif "yago-knowledge.org" in uri:
        return "yago"
    elif "MECCG" in uri:
        return "card"
    return "wiki"


def get_data_source(predicate: str, value: str = "") -> str:
    pred_lower = predicate.lower()
    if "meccg" in pred_lower or "card" in pred_lower:
        return "card"
    elif "dbpedia" in value or "wikidata" in value or "yago" in value:
        return "external"
    elif "sameas" in pred_lower:
        return "alignment"
    return "wiki"


def parse_accept_header(accept: str) -> str:
    if not accept:
        return "html"
    if "text/turtle" in accept.lower():
        return "turtle"
    if "application/n-triples" in accept.lower():
        return "ntriples"
    return "html"


# =============================================================================
# HTML TEMPLATES (V2 Modern UI)
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
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; }
        
        header { background: linear-gradient(135deg, #1a472a 0%, #2d5a3d 100%); color: white; padding: 0.8rem 2rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem; }
        .logo { font-size: 1.3rem; font-weight: 600; }
        .logo a { color: white; text-decoration: none; }
        nav { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }
        nav a { color: #c0e0c0; text-decoration: none; padding: 0.4rem 0.8rem; border-radius: 4px; }
        nav a:hover { background: rgba(255,255,255,0.1); }
        
        .dropdown { position: relative; }
        .dropdown-btn { background: rgba(255,255,255,0.1); color: #c0e0c0; padding: 0.4rem 1rem; border: 1px solid rgba(255,255,255,0.2); border-radius: 4px; cursor: pointer; font-size: 0.9rem; }
        .dropdown-btn:hover { background: rgba(255,255,255,0.2); }
        .dropdown-content { display: none; position: absolute; top: 100%; left: 0; background: white; min-width: 180px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); border-radius: 4px; z-index: 100; }
        .dropdown:hover .dropdown-content { display: block; }
        .dropdown-content a { display: block; padding: 0.6rem 1rem; color: #333; border-bottom: 1px solid #eee; }
        .dropdown-content a:hover { background: #f0f0f0; }
        
        .container { max-width: 1200px; margin: 0 auto; padding: 1.5rem; }
        
        .entity-header { background: white; border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.1); display: flex; gap: 1.5rem; flex-wrap: wrap; }
        .entity-image img { max-width: 180px; max-height: 220px; border-radius: 4px; }
        .entity-info { flex: 1; min-width: 300px; }
        .entity-info h2 { font-size: 1.8rem; color: #1a472a; margin-bottom: 0.3rem; }
        .entity-uri { font-family: monospace; font-size: 0.8rem; color: #666; word-break: break-all; margin-bottom: 0.8rem; }
        .entity-types { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 0.8rem; }
        
        .tag { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.75rem; font-weight: 500; }
        .tag-type { background: #e8f5e9; color: #2e7d32; }
        .tag-inferred { background: #fff3e0; color: #e65100; }
        .tag-card { background: #e3f2fd; color: #1565c0; }
        .tag-wiki { background: #f3e5f5; color: #7b1fa2; }
        .tag-external { background: #fce4ec; color: #c2185b; }
        
        .lang-tag { display: inline-block; padding: 0.15rem 0.4rem; border-radius: 3px; font-size: 0.7rem; font-weight: 600; color: white; margin-left: 0.3rem; text-transform: uppercase; }
        .lang-en { background: #3498db; }
        .lang-fr { background: #e74c3c; }
        .lang-de { background: #f39c12; }
        .lang-es { background: #9b59b6; }
        .lang-it { background: #1abc9c; }
        .lang-nl { background: #e67e22; }
        .lang-default { background: #95a5a6; }
        
        .formats { margin-top: 1rem; padding-top: 0.8rem; border-top: 1px solid #eee; }
        .formats a { display: inline-block; margin-right: 0.8rem; padding: 0.3rem 0.7rem; background: #f0f0f0; border-radius: 4px; text-decoration: none; color: #333; font-size: 0.8rem; }
        .formats a:hover { background: #e0e0e0; }
        
        .filter-bar { background: white; border-radius: 8px; padding: 1rem 1.5rem; margin-bottom: 1rem; box-shadow: 0 2px 8px rgba(0,0,0,0.1); display: flex; align-items: center; gap: 1.5rem; flex-wrap: wrap; }
        .filter-bar label { font-weight: 500; color: #555; font-size: 0.9rem; }
        .filter-bar select { padding: 0.4rem 0.8rem; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9rem; }
        .filter-group { display: flex; align-items: center; gap: 0.5rem; }
        
        .section { background: white; border-radius: 8px; margin-bottom: 1rem; box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden; }
        .section-header { background: #f8f9fa; padding: 0.8rem 1.2rem; border-bottom: 1px solid #eee; font-weight: 600; color: #1a472a; display: flex; align-items: center; gap: 0.5rem; }
        
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 0.6rem 1rem; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #fafafa; font-weight: 500; color: #666; width: 25%; }
        td a { color: #1565c0; text-decoration: none; }
        td a:hover { text-decoration: underline; }
        .external-link { font-size: 0.75rem; color: #888; margin-left: 0.4rem; }
        
        tr[data-source="card"] { background: #f0f7ff; }
        tr.hidden { display: none; }
        
        .sameas-badge { display: inline-block; padding: 0.2rem 0.5rem; border-radius: 3px; font-size: 0.75rem; font-weight: 500; }
        .sameas-badge.dbpedia { background: #e3f2fd; color: #1565c0; }
        .sameas-badge.wikidata { background: #f3e5f5; color: #7b1fa2; }
        .sameas-badge.yago { background: #fff8e1; color: #f57f17; }
        
        .search-box { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; }
        .search-box input { flex: 1; padding: 0.7rem 1rem; border: 2px solid #ddd; border-radius: 4px; font-size: 1rem; }
        .search-box button { padding: 0.7rem 1.5rem; background: #1a472a; color: white; border: none; border-radius: 4px; cursor: pointer; }
        
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
        .stat-card { background: white; padding: 1.2rem; border-radius: 8px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .stat-card .value { font-size: 1.8rem; font-weight: bold; color: #1a472a; }
        .stat-card .label { color: #666; font-size: 0.85rem; }
        
        .error { background: #ffebee; color: #c62828; padding: 2rem; border-radius: 8px; text-align: center; }
        footer { text-align: center; padding: 1.5rem; color: #666; font-size: 0.85rem; }
        footer a { color: #1565c0; }
    </style>
</head>
<body>
    <header>
        <div class="logo">🏔️ <a href="/">Tolkien KG</a></div>
        <nav>
            <a href="/">Home</a>
            <div class="dropdown">
                <button class="dropdown-btn">Browse by Type ▼</button>
                <div class="dropdown-content">
                    {% for type_id, type_name in infobox_types %}
                    <a href="/browse/{{ type_id }}">{{ type_name }}</a>
                    {% endfor %}
                </div>
            </div>
            <a href="/search">Search</a>
            <a href="/sparql">SPARQL</a>
        </nav>
    </header>
    <div class="container">{{ content | safe }}</div>
    <footer>Tolkien KG - Data from <a href="https://tolkiengateway.net">Tolkien Gateway</a> & MECCG</footer>
    <script>
        function applyFilters() {
            const langFilter = document.getElementById('lang-filter')?.value || 'all';
            const sourceFilter = document.getElementById('source-filter')?.value || 'all';
            document.querySelectorAll('tr[data-filterable]').forEach(row => {
                const rowLang = row.dataset.lang || '';
                const rowSource = row.dataset.source || '';
                let show = (langFilter === 'all' || rowLang === langFilter || rowLang === '') && (sourceFilter === 'all' || rowSource === sourceFilter);
                row.classList.toggle('hidden', !show);
            });
        }
        document.addEventListener('DOMContentLoaded', () => {
            document.getElementById('lang-filter')?.addEventListener('change', applyFilters);
            document.getElementById('source-filter')?.addEventListener('change', applyFilters);
        });
    </script>
</body>
</html>
"""

HOME_CONTENT = """
<h2 style="margin-bottom:1.5rem;color:#1a472a;">Welcome to Tolkien Knowledge Graph</h2>
<form action="/search" method="get" class="search-box">
    <input type="text" name="q" placeholder="Search (Gandalf, Rivendell, One Ring...)">
    <button type="submit">Search</button>
</form>
<div class="stats-grid">
    <div class="stat-card"><div class="value">{{ stats.total_triples }}</div><div class="label">Triples</div></div>
    <div class="stat-card"><div class="value">{{ stats.entities }}</div><div class="label">Entities</div></div>
</div>
<div class="section">
    <div class="section-header">📊 Top Types</div>
    <table>
        <tr><th>Type</th><th>Count</th></tr>
        {% for type_uri, count in stats.types %}<tr><td>{{ type_uri | uri_label }}</td><td>{{ count }}</td></tr>{% endfor %}
    </table>
</div>
<div class="section">
    <div class="section-header">🔗 Popular</div>
    <table>
        <tr><td><a href="/resource/Gandalf">Gandalf</a></td><td><a href="/resource/Frodo_Baggins">Frodo</a></td><td><a href="/resource/Rivendell">Rivendell</a></td><td><a href="/resource/Mordor">Mordor</a></td></tr>
    </table>
</div>
"""

ENTITY_CONTENT = """
<div class="entity-header">
    {% if image %}<div class="entity-image"><img src="{{ image }}" alt="{{ name }}"></div>{% endif %}
    <div class="entity-info">
        <h2>{{ name }}</h2>
        <div class="entity-uri">{{ uri }}</div>
        <div class="entity-types">
            {% for cls in classes %}<span class="tag {% if cls.direct %}tag-type{% else %}tag-inferred{% endif %}">{{ cls.label }}{% if not cls.direct %} ↑{% endif %}</span>{% endfor %}
        </div>
        {% if description %}<p style="color:#555;font-style:italic;">{{ description }}</p>{% endif %}
        <div class="formats">
            <strong>Formats (View):</strong> 
            <a href="{{ request_path }}?format=turtle" target="_blank">Turtle (.ttl)</a> 
            <a href="{{ request_path }}?format=ntriples" target="_blank">N-Triples (.nt)</a>
        </div>
    </div>
</div>

<div class="filter-bar">
    <div class="filter-group"><label>Language:</label>
        <select id="lang-filter"><option value="all">All</option><option value="en">EN</option><option value="fr">FR</option><option value="de">DE</option><option value="es">ES</option><option value="it">IT</option></select>
    </div>
    <div class="filter-group"><label>Source:</label>
        <select id="source-filter"><option value="all">All</option><option value="wiki">Wiki</option><option value="card">Card</option><option value="external">External</option></select>
    </div>
</div>

{% if sameas %}
<div class="section">
    <div class="section-header">🔗 Same As</div>
    <table>{% for link in sameas %}<tr><td><span class="sameas-badge {{ link.source }}">{{ link.source }}</span></td><td><a href="{{ link.uri }}" target="_blank">{{ link.uri }}</a></td></tr>{% endfor %}</table>
</div>
{% endif %}

{% if labels %}
<div class="section">
    <div class="section-header">🏷️ Labels</div>
    <table>
        {% for label in labels %}<tr data-filterable data-lang="{{ label.lang or 'default' }}" data-source="wiki"><td>{{ label.value }}</td><td><span class="lang-tag lang-{{ label.lang or 'default' }}">{{ label.lang or '—' }}</span></td></tr>{% endfor %}
    </table>
</div>
{% endif %}

{% if card_data %}
<div class="section">
    <div class="section-header">🎴 Card Data <span class="tag tag-card">Card</span></div>
    <table>
        {% for prop in card_data %}
        <tr data-filterable data-source="card" data-lang="{{ prop.lang or '' }}">
            <td>{{ prop.predicate | uri_label }} <span class="tag tag-card">Card</span></td>
            <td>{% if prop.is_uri %}<a href="/resource/{{ prop.value | uri_to_path }}">{{ prop.value | uri_label }}</a>{% else %}{{ prop.value }}{% if prop.lang %}<span class="lang-tag lang-{{ prop.lang }}">{{ prop.lang }}</span>{% endif %}{% endif %}</td>
        </tr>
        {% endfor %}
    </table>
</div>
{% endif %}

{% if outgoing %}
<div class="section">
    <div class="section-header">➡️ Properties <span class="tag tag-wiki">Wiki</span></div>
    <table>
        {% for prop in outgoing %}
        <tr data-filterable data-source="{{ prop.source }}" data-lang="{{ prop.lang or '' }}">
            <td>{{ prop.predicate | uri_label }}{% if prop.source == 'card' %} <span class="tag tag-card">Card</span>{% endif %}</td>
            <td>
                {% if prop.is_uri %}
                    {% if prop.external %}
                        <a href="{{ prop.value }}" target="_blank" style="color:#c2185b;">{{ prop.value | uri_label }} ↗</a>
                    {% else %}
                        <a href="/resource/{{ prop.value | uri_to_path }}">{{ prop.value | uri_label }}</a>
                    {% endif %}
                {% else %}
                    {{ prop.value }}
                    {% if prop.lang %}<span class="lang-tag lang-{{ prop.lang }}">{{ prop.lang }}</span>{% endif %}
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </table>
</div>
{% endif %}

{% if incoming %}
<div class="section">
    <div class="section-header">⬅️ Referenced By</div>
    <table>
        {% for prop in incoming %}
        <tr data-filterable data-source="{{ prop.source }}">
            <td><a href="/resource/{{ prop.subject | uri_to_path }}">{{ prop.subject | uri_label }}</a>{% if prop.source == 'card' %} <span class="tag tag-card">Card</span>{% endif %}</td>
            <td>{{ prop.predicate | uri_label }}</td>
        </tr>
        {% endfor %}
    </table>
</div>
{% endif %}
"""

BROWSE_CONTENT = """
<h2 style="margin-bottom:1rem;color:#1a472a;">{{ type_name }}</h2>
<div class="section">
    <div class="section-header">📋 {{ results | length }} found</div>
    <table>{% for r in results %}<tr><td><a href="/resource/{{ r.entity | uri_to_path }}">{{ r.label }}</a></td></tr>{% endfor %}</table>
</div>
"""

SEARCH_CONTENT = """
<h2 style="margin-bottom:1rem;color:#1a472a;">Search</h2>
<form action="/search" method="get" class="search-box"><input type="text" name="q" value="{{ query }}" placeholder="Search..."><button type="submit">Search</button></form>
{% if results %}<div class="section"><div class="section-header">🔍 {{ results | length }} results</div><table>{% for r in results %}<tr><td><a href="/resource/{{ r.entity | uri_to_path }}">{{ r.label }}</a></td><td>{{ r.type | uri_label if r.type else '—' }}</td></tr>{% endfor %}</table></div>{% elif query %}<div class="error">No results for "{{ query }}"</div>{% endif %}
"""

SPARQL_CONTENT = """
<h2 style="margin-bottom:1rem;color:#1a472a;">SPARQL</h2>
<div class="section"><div class="section-header">📡 Endpoint</div><table><tr><th>URL</th><td><code>{{ endpoint }}</code></td></tr></table></div>
<div class="section"><div class="section-header">🧪 Query</div>
<form action="/sparql" method="get" style="padding:1rem;"><textarea name="query" rows="5" style="width:100%;font-family:monospace;padding:0.5rem;">{{ query or 'SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10' }}</textarea><br><br><button type="submit" style="padding:0.5rem 1rem;background:#1a472a;color:white;border:none;border-radius:4px;cursor:pointer;">Run</button></form>
{% if results %}<div style="padding:1rem;overflow-x:auto;"><table><tr>{% for var in variables %}<th>{{ var }}</th>{% endfor %}</tr>{% for row in results %}<tr>{% for var in variables %}<td>{{ row[var][:60] }}...</td>{% endfor %}</tr>{% endfor %}</table></div>{% endif %}
</div>
"""


# =============================================================================
# JINJA FILTERS
# =============================================================================

@app.template_filter('uri_label')
def uri_label_filter(uri):
    return uri_to_label(uri) if uri else ""

@app.template_filter('uri_to_path')
def uri_to_path_filter(uri):
    if not uri:
        return ""
    if uri.startswith(BASE_URI):
        return uri[len(BASE_URI):]
    return quote(uri_to_label(uri).replace(" ", "_"), safe="")


# =============================================================================
# ROUTES
# =============================================================================

@app.route("/")
def home():
    stats = get_statistics()
    content = render_template_string(HOME_CONTENT, stats=stats)
    return render_template_string(HTML_TEMPLATE, title="Home", content=content, infobox_types=INFOBOX_TYPES)


@app.route("/resource/<path:entity_name>")
def resource(entity_name: str):
    entity_uri = BASE_URI + entity_name
    
    fmt = request.args.get("format", "") or parse_accept_header(request.headers.get("Accept", ""))
    
    # GESTION DES FORMATS (MODIFIÉ POUR AFFICHAGE INLINE)
    if fmt in ("turtle", "ttl"):
        data = query_entity_turtle(entity_uri)
        return Response(
            data, 
            mimetype="text/turtle",
            headers={"Content-Disposition": f"inline; filename={entity_name}.ttl"}
        )
    if fmt == "ntriples":
        data = query_entity_turtle(entity_uri)
        return Response(
            data, 
            mimetype="application/n-triples",
            headers={"Content-Disposition": f"inline; filename={entity_name}.nt"}
        )
    
    # GESTION DE L'AFFICHAGE HTML (V2)
    bindings = query_entity_description(entity_uri)
    if not bindings:
        return render_template_string(HTML_TEMPLATE, title="Not Found", content="<div class='error'>Entity not found</div>", infobox_types=INFOBOX_TYPES), 404
    
    name = unquote(entity_name.replace("_", " "))
    description, image = None, None
    labels, outgoing, incoming, card_data = [], [], [], []
    
    for b in bindings:
        pred, obj = b["predicate"]["value"], b["object"]
        is_in = b.get("isIncoming", {}).get("value") == "true"
        source = "card" if "meccg" in pred.lower() or "MECCG" in pred else get_data_source(pred, obj.get("value", ""))
        
        if is_in:
            incoming.append({"subject": obj["value"], "predicate": pred, "source": source})
        else:
            if "label" in pred.lower():
                labels.append({"value": obj["value"], "lang": obj.get("xml:lang", "")})
            elif "description" in pred.lower():
                description = obj["value"]
            # ICI LE CHANGEMENT : On ne fait plus de 'elif' pour l'image qui excluait la propriété
            elif "type" not in pred.lower():
                val = obj["value"]
                is_uri = obj["type"] == "uri"
                
                # Détermine si c'est un lien externe
                # C'est externe si :
                # 1. Ce n'est pas sur tolkiengateway.net
                # 2. OU c'est un fichier/media sur tolkiengateway (File:, /media/)
                is_external = is_uri and (
                    "tolkiengateway.net" not in val 
                    or "File:" in val 
                    or "/media/" in val
                )

                prop = {
                    "predicate": pred,
                    "value": val,
                    "is_uri": is_uri,
                    "lang": obj.get("xml:lang", ""),
                    "external": is_external, # On passe ce flag au template
                    "source": source
                }
                (card_data if source == "card" else outgoing).append(prop)
                
    # Ajout des données de cartes liées
    for rel in query_card_data_for_entity(entity_uri):
        if "type" not in rel["predicate"]["value"].lower():
            card_data.append({"predicate": rel["predicate"]["value"], "value": rel["object"]["value"], "is_uri": rel["object"]["type"] == "uri", "lang": rel["object"].get("xml:lang", ""), "source": "card"})
    
    classes = [{"uri": c["class"]["value"], "label": c.get("classLabel", {}).get("value", uri_to_label(c["class"]["value"])), "direct": c.get("isDirect", {}).get("value") == "true"} for c in query_all_classes_with_superclasses(entity_uri)]
    sameas = [{"uri": u, "source": categorize_uri(u)} for u in query_sameas_links(entity_uri)]
    
    content = render_template_string(ENTITY_CONTENT, name=name, uri=entity_uri, description=description, image=image, classes=classes, labels=labels, sameas=sameas, card_data=card_data, outgoing=outgoing, incoming=incoming, request_path=request.path)
    return render_template_string(HTML_TEMPLATE, title=name, content=content, infobox_types=INFOBOX_TYPES)


@app.route("/browse/<entity_type>")
def browse(entity_type: str):
    type_name = dict(INFOBOX_TYPES).get(entity_type, entity_type)
    results = [{"entity": r["entity"]["value"], "label": r["label"]["value"]} for r in query_entities_by_type(entity_type)]
    content = render_template_string(BROWSE_CONTENT, type_name=type_name, results=results)
    return render_template_string(HTML_TEMPLATE, title=type_name, content=content, infobox_types=INFOBOX_TYPES)


@app.route("/search")
def search():
    q = request.args.get("q", "")
    results = [{"entity": r["entity"]["value"], "label": r["label"]["value"], "type": r.get("type", {}).get("value", "")} for r in search_entities(q)] if q else []
    content = render_template_string(SEARCH_CONTENT, query=q, results=results)
    return render_template_string(HTML_TEMPLATE, title="Search", content=content, infobox_types=INFOBOX_TYPES)


@app.route("/sparql")
def sparql_page():
    q = request.args.get("query", "")
    results, variables = [], []
    if q:
        try:
            sparql = get_sparql()
            sparql.setQuery(SPARQL_PREFIXES + "\n" + q)
            sparql.setReturnFormat(JSON)
            resp = sparql.query().convert()
            variables = resp["head"]["vars"]
            results = [{v: b.get(v, {}).get("value", "") for v in variables} for b in resp["results"]["bindings"]]
        except Exception as e:
            results, variables = [{"error": str(e)}], ["error"]
    content = render_template_string(SPARQL_CONTENT, endpoint=FUSEKI_ENDPOINT, query=q, results=results, variables=variables)
    return render_template_string(HTML_TEMPLATE, title="SPARQL", content=content, infobox_types=INFOBOX_TYPES)


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║     Tolkien KG - Linked Data Server v2.2                  ║
╠═══════════════════════════════════════════════════════════╣
║  1. fuseki-server --update --mem /tolkien                 ║
║  2. Load KG at http://localhost:3030                      ║
║  3. pip install flask SPARQLWrapper                       ║
╠═══════════════════════════════════════════════════════════╣
║  http://localhost:5000/resource/Gandalf                   ║
║  http://localhost:5000/browse/Character                   ║
║  http://localhost:5000/search                             ║
║  http://localhost:5000/sparql                             ║
╚═══════════════════════════════════════════════════════════╝
    """)
    app.run(host="0.0.0.0", port=5000, debug=True)