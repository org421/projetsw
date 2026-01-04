#!/usr/bin/env python3
"""
Main script - Étape 3: Exploration de l'API MediaWiki du Tolkien Gateway
Focus sur les Templates Infobox

Ce script démontre comment:
- Lister tous les templates d'infobox disponibles
- Récupérer toutes les pages utilisant un infobox spécifique (embeddedin)
- Extraire le wikitext des infoboxes
"""

from tolkien_kg.api import MediaWikiClient


def print_separator(title: str):
    """Affiche un séparateur visuel."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70 + "\n")


def demo_wiki_statistics(client: MediaWikiClient):
    """Affiche les statistiques du wiki."""
    print_separator("STATISTIQUES DU WIKI")
    
    stats = client.get_wiki_statistics()
    print(f"Nombre total de pages: {stats.get('pages', 'N/A')}")
    print(f"Nombre d'articles: {stats.get('articles', 'N/A')}")
    print(f"Nombre d'éditions: {stats.get('edits', 'N/A')}")
    print(f"Nombre d'images: {stats.get('images', 'N/A')}")
    print(f"Nombre d'utilisateurs: {stats.get('users', 'N/A')}")


def demo_list_infobox_templates(client: MediaWikiClient):
    """Liste tous les templates d'infobox disponibles."""
    print_separator("TEMPLATES INFOBOX DISPONIBLES")
    
    templates = client.get_all_infobox_templates()
    
    print(f"Nombre total de templates d'infobox: {len(templates)}\n")
    
    for i, template in enumerate(templates, 1):
        template_name = template['title'].replace('Template:', '')
        print(f"{i:2}. {template_name}")
    
    return templates


def demo_pages_using_infobox(client: MediaWikiClient, infobox_name: str, limit: int = 10):
    """Liste les pages utilisant un infobox spécifique."""
    print_separator(f"PAGES UTILISANT '{infobox_name}' (limit={limit})")
    
    pages = list(client.get_pages_using_template(infobox_name, limit=limit))
    
    print(f"Pages trouvées: {len(pages)}\n")
    
    for i, page in enumerate(pages, 1):
        print(f"{i:2}. [{page['pageid']:6}] {page['title']}")
    
    return pages


def demo_count_infobox_usage(client: MediaWikiClient, infobox_names: list):
    """Compte le nombre de pages pour chaque infobox."""
    print_separator("STATISTIQUES D'UTILISATION DES INFOBOXES")
    
    stats = {}
    for name in infobox_names:
        count = client.count_pages_using_template(name)
        stats[name] = count
        print(f"  {name}: {count} pages")
    
    return stats


def demo_page_wikitext_preview(client: MediaWikiClient, title: str, max_chars: int = 2000):
    """Affiche un aperçu du wikitext d'une page."""
    print_separator(f"WIKITEXT DE '{title}'")
    
    wikitext = client.get_page_wikitext(title)
    
    if wikitext:
        preview = wikitext[:max_chars]
        if len(wikitext) > max_chars:
            preview += f"\n\n[... tronque - {len(wikitext)} caracteres au total ...]"
        print(preview)
    else:
        print("Page non trouvee ou erreur.")
    
    return wikitext


def demo_page_templates(client: MediaWikiClient, title: str):
    """Affiche les templates utilisés dans une page."""
    print_separator(f"TEMPLATES UTILISES DANS '{title}'")
    
    templates = client.get_page_templates(title)
    
    infobox_templates = []
    other_templates = []
    
    for template in templates:
        if 'infobox' in template['title'].lower():
            infobox_templates.append(template['title'])
        else:
            other_templates.append(template['title'])
    
    if infobox_templates:
        print("Infoboxes:")
        for t in infobox_templates:
            print(f"   - {t}")
    
    print(f"\nAutres templates ({len(other_templates)}):")
    for t in other_templates[:10]:
        print(f"   - {t}")
    if len(other_templates) > 10:
        print(f"   ... et {len(other_templates) - 10} autres")
    
    return templates


def demo_full_infobox_workflow(client: MediaWikiClient, infobox_name: str, sample_size: int = 5):
    """
    Workflow complet pour un type d'infobox:
    1. Lister les pages utilisant cet infobox
    2. Pour chaque page, récupérer le wikitext
    3. Afficher un résumé
    """
    print_separator(f"WORKFLOW COMPLET: {infobox_name}")
    
    print(f"Recherche des pages avec l'infobox '{infobox_name}'...\n")
    
    pages = list(client.get_pages_using_template(infobox_name, limit=sample_size))
    
    print(f"{len(pages)} pages trouvees (echantillon de {sample_size})\n")
    
    for i, page in enumerate(pages, 1):
        title = page['title']
        print(f"\n{'-' * 50}")
        print(f"Page {i}/{len(pages)}: {title}")
        print(f"   ID: {page['pageid']}")
        
        # Récupérer les infos complètes
        info = client.get_page_full_info(title)
        
        if 'error' not in info:
            print(f"   Liens internes: {len(info['links'])}")
            print(f"   Images: {len(info['images'])}")
            print(f"   Categories: {len(info['categories'])}")
            print(f"   Taille wikitext: {len(info['wikitext']) if info['wikitext'] else 0} chars")
            
            # Afficher les premières lignes du wikitext (pour voir l'infobox)
            if info['wikitext']:
                lines = info['wikitext'].split('\n')[:15]
                print(f"\n   Apercu wikitext:")
                for line in lines:
                    if line.strip():
                        print(f"   | {line[:70]}{'...' if len(line) > 70 else ''}")


def main():
    """Fonction principale - Focus sur les Infoboxes."""
    print("\n" + "#" * 70)
    print("#" + " " * 68 + "#")
    print("#     TOLKIEN KNOWLEDGE GRAPH - Etape 3                               #")
    print("#     Exploration des Infoboxes via l'API MediaWiki                   #")
    print("#" + " " * 68 + "#")
    print("#" * 70)
    
    # Initialiser le client
    client = MediaWikiClient()
    
    # 1. Statistiques du wiki
    demo_wiki_statistics(client)
    
    # 2. Lister tous les templates d'infobox
    templates = demo_list_infobox_templates(client)
    
    # 3. Statistiques d'utilisation des principaux infoboxes
    # ATTENTION: Les noms des templates varient sur Tolkien Gateway
    # Certains sont "X infobox", d'autres "Infobox X", d'autres juste "X"
    main_infoboxes = [
        "Infobox character",   # Personnages
        "Location infobox",    # Lieux
        "Book",                # Livres
        "Object infobox",      # Objets
        "Battle",              # Batailles
        "Kingdom",             # Royaumes
        "Elves infobox",       # Elfes (template spécifique)
        "Dwarves infobox",     # Nains (template spécifique)
        "Maiar infobox",       # Maiar
        "Valar infobox",       # Valar
    ]
    demo_count_infobox_usage(client, main_infoboxes)
    
    # 4. Pages utilisant "Infobox character"
    demo_pages_using_infobox(client, "Infobox character", limit=15)
    
    # 5. Pages utilisant "Location infobox"
    demo_pages_using_infobox(client, "Location infobox", limit=10)
    
    # 6. Exemple de page avec son wikitext
    demo_page_wikitext_preview(client, "Elrond")
    
    # 7. Templates utilisés dans une page
    demo_page_templates(client, "Elrond")
    
    # 8. Workflow complet pour "Infobox character"
    demo_full_infobox_workflow(client, "Infobox character", sample_size=3)
    
    # 9. Workflow complet pour "Location infobox"
    demo_full_infobox_workflow(client, "Location infobox", sample_size=3)
    
    # 10. Workflow complet pour "Book"
    demo_full_infobox_workflow(client, "Book", sample_size=3)
    
    print("\n" + "=" * 70)
    print(" FIN DE LA DEMONSTRATION")
    print("=" * 70)
    print("\nProchaine etape: Parser les infoboxes avec mwparserfromhell\n")


if __name__ == "__main__":
    main()