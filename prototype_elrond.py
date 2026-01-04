import mwparserfromhell
from rdflib import Graph, Literal, RDF, RDFS, Namespace

# 1. CONFIGURATION
# ---------------------------------------------------------
TOLKIEN = Namespace("http://tolkien-kg.org/ontology/")
RES = Namespace("http://tolkien-kg.org/resource/")
SCHEMA = Namespace("http://schema.org/")

# Initialisation du graphe
g = Graph()
g.bind("tolkien", TOLKIEN)
g.bind("schema1", SCHEMA) # On force schema1 pour coller à votre exemple
g.bind("res", RES)

# 2. LOGIQUE DE NETTOYAGE
# ---------------------------------------------------------
def clean_value(wikicode):
    if not wikicode: return "None"
    
    if isinstance(wikicode, str):
        parsed = mwparserfromhell.parse(wikicode)
    else:
        parsed = wikicode

    # Enlever les refs
    for tag in parsed.filter_tags():
        if tag.tag == "ref":
            parsed.remove(tag)

    # Traiter les templates (ex: {{FA|532}} -> FA 532)
    for template in parsed.filter_templates():
        tmpl_name = str(template.name).strip()
        params = [str(p.value) for p in template.params]
        if len(params) > 0: 
            replacement = f"{tmpl_name} {' '.join(params)}"
            parsed.replace(template, replacement)

    text_content = parsed.strip_code().strip()
    text_content = text_content.replace("<br/>", ", ").replace("<br>", ", ").replace("\n", " ")
    
    return text_content if text_content else "None"

# 3. PARSING
# ---------------------------------------------------------
def process_page_to_rdf(wikitext, page_title):
    wikicode = mwparserfromhell.parse(wikitext)
    
    # CORRECTION ICI : .lower() pour gérer "infobox" vs "Infobox"
    templates = wikicode.filter_templates(matches=lambda t: "infobox character" in str(t.name).lower())
    
    if not templates:
        print("Erreur : Infobox non trouvée")
        return

    infobox = templates[0]
    subject_uri = RES[page_title.replace(" ", "_")]
    
    # Typage
    g.add((subject_uri, RDF.type, SCHEMA.Person))
    g.add((subject_uri, RDF.type, TOLKIEN.Character))
    g.add((subject_uri, RDFS.label, Literal(page_title, lang="en")))
    
    # Mapping
    mappings = {
        "name": SCHEMA.name,
        "people": TOLKIEN.race,
        "race": TOLKIEN.race,
        "birth": SCHEMA.birthDate,
        "spouse": SCHEMA.spouse,
        "titles": TOLKIEN.title
    }

    for wiki_field, rdf_prop in mappings.items():
        # On vérifie si le champ existe, même vide
        if infobox.has(wiki_field):
            raw_val = infobox.get(wiki_field).value
            clean_val = clean_value(raw_val)
            g.add((subject_uri, rdf_prop, Literal(clean_val)))
        else:
            # Optionnel : Si vous voulez forcer "None" même si le champ est absent
            # g.add((subject_uri, rdf_prop, Literal("None")))
            pass

# 4. EXÉCUTION
# ---------------------------------------------------------
print("--- TEST SUR LES DONNÉES D'ELROND ---")

wikitext_elrond = """
{{short description|Lord of Rivendell and wielder of Vilya}}
{{infobox character
| name=Elrond
| people=[[Half-elven|Half-elf]]
| image=Tatyafinwe - Portrait of Elrond.jpg
| caption="Portrait of Elrond" by [[:Category:Images by Tatyafinwe|Tatyafinwe]]
| titles=Lord of [[Rivendell]]
| position=Ring-bearer of [[Vilya]]<br/> Vice-regent of Eriador
| location=[[Rivendell]]<br/>[[Aman]] (after {{TA|3021}})
| affiliation=[[White Council]]
| language=[[Sindarin]], [[Quenya]], [[Westron]]
| birth={{FA|532}}<ref>{{WJ|Years}}</ref>
| spouse=[[Celebrían]]
| children=[[Elladan]] & [[Elrohir]] ([[twins]])<br/>[[Arwen]]
}}
"""

process_page_to_rdf(wikitext_elrond, "Elrond")

print("\n--- RÉSULTAT RDF (Turtle) ---\n")
print(g.serialize(format="turtle"))