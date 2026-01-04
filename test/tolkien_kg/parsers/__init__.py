"""
Parser pour extraire les infoboxes du wikitext avec mwparserfromhell
"""

import re
from typing import Dict, List, Any, Optional, Tuple
import mwparserfromhell as mwp


class WikitextParser:
    """
    Parser pour extraire et analyser les infoboxes du wikitext.
    Utilise mwparserfromhell pour parser le wikitext MediaWiki.
    """
    
    # Templates d'infobox connus sur Tolkien Gateway
    KNOWN_INFOBOX_TEMPLATES = [
        "infobox character",
        "location infobox",
        "book",
        "kingdom",
        "battle",
        "war",
        "object infobox",
        "actor",
        "film infobox",
        "video game infobox",
        "song",
        "poem infobox",
        "letter infobox",
        "chapter",
        "author infobox",
        "artist infobox",
        "dragon infobox",
        "race infobox",
        "noble house infobox",
        "plant infobox",
        "organization infobox",
        "person infobox",
        "people infobox",
        "modernpeople infobox",
        "mountain",
        "episode infobox",
        "board game infobox",
        "audiobook infobox",
        "company infobox",
        "collectible card",
        "band",
        "album",
        "journal",
        "convention",
        "events",
        "scene",
    ]
    
    def __init__(self):
        # Créer un set en lowercase pour la recherche rapide
        self._infobox_names = set(name.lower() for name in self.KNOWN_INFOBOX_TEMPLATES)
    
    def parse(self, wikitext: str) -> mwp.wikicode.Wikicode:
        """
        Parse le wikitext en objet Wikicode.
        
        Args:
            wikitext: Code source wikitext
            
        Returns:
            Objet Wikicode parsé
        """
        return mwp.parse(wikitext)
    
    def is_infobox_template(self, template_name: str) -> bool:
        """
        Vérifie si un template est un infobox connu.
        
        Args:
            template_name: Nom du template
            
        Returns:
            True si c'est un infobox
        """
        name_lower = template_name.lower().strip()
        return name_lower in self._infobox_names or 'infobox' in name_lower
    
    def extract_infoboxes(self, wikitext: str) -> List[Dict[str, Any]]:
        """
        Extrait toutes les infoboxes d'un wikitext.
        
        Args:
            wikitext: Code source wikitext
            
        Returns:
            Liste de dictionnaires contenant les données de chaque infobox
        """
        parsed = self.parse(wikitext)
        templates = parsed.filter_templates()
        
        infoboxes = []
        
        for template in templates:
            template_name = str(template.name).strip()
            
            if self.is_infobox_template(template_name):
                infobox_data = self.extract_template_params(template)
                infobox_data['_template_name'] = template_name
                infoboxes.append(infobox_data)
        
        return infoboxes
    
    def extract_template_params(self, template: mwp.nodes.Template) -> Dict[str, Any]:
        """
        Extrait tous les paramètres d'un template.
        
        Args:
            template: Objet Template de mwparserfromhell
            
        Returns:
            Dictionnaire {nom_param: valeur}
        """
        params = {}
        
        for param in template.params:
            name = str(param.name).strip()
            value = str(param.value).strip()
            
            # Ignorer les paramètres vides
            if value:
                params[name] = value
        
        return params
    
    def extract_first_infobox(self, wikitext: str) -> Optional[Dict[str, Any]]:
        """
        Extrait la première infobox trouvée dans le wikitext.
        
        Args:
            wikitext: Code source wikitext
            
        Returns:
            Dictionnaire avec les données de l'infobox ou None
        """
        infoboxes = self.extract_infoboxes(wikitext)
        return infoboxes[0] if infoboxes else None
    
    def extract_links(self, wikitext: str) -> List[Dict[str, str]]:
        """
        Extrait tous les liens internes [[...]] du wikitext.
        
        Args:
            wikitext: Code source wikitext
            
        Returns:
            Liste de dictionnaires avec 'target' et 'text'
        """
        parsed = self.parse(wikitext)
        wikilinks = parsed.filter_wikilinks()
        
        links = []
        for link in wikilinks:
            target = str(link.title).strip()
            text = str(link.text).strip() if link.text else target
            links.append({
                'target': target,
                'text': text
            })
        
        return links
    
    def extract_links_from_value(self, value: str) -> List[str]:
        """
        Extrait les cibles des liens d'une valeur de paramètre.
        
        Args:
            value: Valeur d'un paramètre (peut contenir [[liens]])
            
        Returns:
            Liste des cibles de liens
        """
        links = self.extract_links(value)
        return [link['target'] for link in links]
    
    def clean_value(self, value: str) -> str:
        """
        Nettoie une valeur en retirant le markup wiki.
        
        Args:
            value: Valeur brute avec markup
            
        Returns:
            Valeur nettoyée (texte plat)
        """
        parsed = self.parse(value)
        return parsed.strip_code().strip()
    
    def parse_infobox_value(self, value: str) -> Dict[str, Any]:
        """
        Parse une valeur d'infobox et retourne une structure enrichie.
        
        Args:
            value: Valeur brute d'un paramètre
            
        Returns:
            Dictionnaire avec:
            - raw: valeur brute
            - clean: valeur nettoyée
            - links: liste des liens extraits
            - has_ref: booléen si contient des références
        """
        return {
            'raw': value,
            'clean': self.clean_value(value),
            'links': self.extract_links_from_value(value),
            'has_ref': '{{' in value or '<ref' in value
        }
    
    def extract_infobox_structured(self, wikitext: str) -> Optional[Dict[str, Any]]:
        """
        Extrait la première infobox avec des valeurs structurées.
        
        Args:
            wikitext: Code source wikitext
            
        Returns:
            Dictionnaire avec les données structurées
        """
        infobox = self.extract_first_infobox(wikitext)
        
        if not infobox:
            return None
        
        structured = {
            '_template_name': infobox.pop('_template_name'),
            '_params': {}
        }
        
        for key, value in infobox.items():
            structured['_params'][key] = self.parse_infobox_value(value)
        
        return structured


class CharacterInfoboxParser(WikitextParser):
    """
    Parser spécialisé pour les infoboxes de personnages.
    Connaît les champs spécifiques du template "Infobox character".
    """
    
    # Champs connus de l'infobox character
    CHARACTER_FIELDS = {
        # Identification
        'name': 'string',
        'image': 'file',
        'caption': 'string',
        'pronun': 'string',
        'othernames': 'string_list',
        
        # Classification
        'people': 'link',
        'race': 'link',
        
        # Statut
        'titles': 'string_list',
        'position': 'string',
        'location': 'link_list',
        'affiliation': 'link_list',
        'language': 'link_list',
        
        # Dates
        'birth': 'date',
        'birthlocation': 'link',
        'death': 'date',
        'deathlocation': 'link',
        'age': 'number',
        'rule': 'date_range',
        
        # Navigation
        'sailedwest': 'date',
        'sailedfrom': 'link',
        
        # Famille
        'house': 'link',
        'heritage': 'string',
        'parentage': 'link_list',
        'siblings': 'link_list',
        'spouse': 'link_list',
        'children': 'link_list',
        
        # Physique
        'gender': 'string',
        'height': 'string',
        'hair': 'string',
        'eyes': 'string',
        
        # Équipement
        'weapon': 'link_list',
        'steed': 'link',
        
        # Notable
        'notablefor': 'string',
    }
    
    def parse_character(self, wikitext: str) -> Optional[Dict[str, Any]]:
        """
        Parse une page de personnage et extrait les données structurées.
        
        Args:
            wikitext: Code source wikitext de la page
            
        Returns:
            Dictionnaire avec les données du personnage
        """
        infobox = self.extract_first_infobox(wikitext)
        
        if not infobox:
            return None
        
        template_name = infobox.pop('_template_name', '').lower()
        
        # Vérifier que c'est bien un infobox character
        if 'character' not in template_name:
            return None
        
        character = {
            '_type': 'Character',
            '_template': template_name,
        }
        
        for field, value in infobox.items():
            field_lower = field.lower()
            field_type = self.CHARACTER_FIELDS.get(field_lower, 'string')
            
            character[field_lower] = self._parse_field(value, field_type)
        
        return character
    
    def _parse_date_templates(self, value: str) -> Dict[str, Any]:
        """
        Parse les templates de dates Tolkien Gateway.
        Formats: {{FA|532}}, {{SA|1697}}, {{TA|3021}}, {{SR|1328}}, {{YT|1300}}
        
        FA = First Age, SA = Second Age, TA = Third Age
        SR = Shire Reckoning, YT = Years of the Trees
        
        Args:
            value: Valeur brute contenant des templates de date
            
        Returns:
            Dictionnaire avec les dates parsées
        """
        import re
        
        result = {
            'raw': value,
            'dates': [],
            'text': ''
        }
        
        # Pattern pour les templates de date: {{XX|YYYY}} ou {{XX|YYYY|n}}
        date_pattern = r'\{\{(FA|SA|TA|SR|YT)\|(\d+)(?:\|[^}]*)?\}\}'
        
        matches = re.findall(date_pattern, value)
        
        for age, year in matches:
            age_names = {
                'FA': 'First Age',
                'SA': 'Second Age', 
                'TA': 'Third Age',
                'SR': 'Shire Reckoning',
                'YT': 'Years of the Trees'
            }
            result['dates'].append({
                'age': age,
                'age_name': age_names.get(age, age),
                'year': int(year)
            })
        
        # Créer une version texte lisible
        # Remplacer les templates par leur version lisible
        text = value
        for age, year in matches:
            text = re.sub(
                r'\{\{' + age + r'\|' + year + r'(?:\|[^}]*)?\}\}',
                f"{age} {year}",
                text
            )
        
        # Nettoyer le reste du markup
        result['text'] = self.clean_value(text)
        
        # Extraire aussi les liens (pour les dates comme [[22 September]])
        result['links'] = self.extract_links_from_value(value)
        
        return result
    
    def _parse_field(self, value: str, field_type: str) -> Any:
        """
        Parse un champ selon son type.
        
        Args:
            value: Valeur brute
            field_type: Type du champ
            
        Returns:
            Valeur parsée
        """
        if field_type == 'string':
            return self.clean_value(value)
        
        elif field_type == 'link':
            links = self.extract_links_from_value(value)
            return links[0] if links else self.clean_value(value)
        
        elif field_type == 'link_list':
            links = self.extract_links_from_value(value)
            if links:
                return links
            # Si pas de liens, essayer de splitter par <br> ou ; ou newline
            clean = self.clean_value(value)
            if '<br' in value.lower() or ';' in clean or '\n' in value:
                items = re.split(r'<br\s*/?>|;|\n', value)
                # Nettoyer chaque item
                result = []
                for item in items:
                    cleaned = self.clean_value(item)
                    if cleaned:
                        result.append(cleaned)
                return result if result else [clean] if clean else []
            return [clean] if clean else []
        
        elif field_type == 'string_list':
            # Splitter par <br> ou newline, puis nettoyer
            if '<br' in value.lower() or '\n' in value:
                items = re.split(r'<br\s*/?>|\n', value)
                result = []
                for item in items:
                    cleaned = self.clean_value(item)
                    if cleaned:
                        result.append(cleaned)
                return result if result else []
            clean = self.clean_value(value)
            return [clean] if clean else []
        
        elif field_type == 'date':
            # Utiliser le nouveau parser de dates
            return self._parse_date_templates(value)
        
        elif field_type == 'date_range':
            return self._parse_date_templates(value)
        
        elif field_type == 'number':
            clean = self.clean_value(value)
            try:
                return int(clean.replace(',', ''))
            except ValueError:
                return clean
        
        elif field_type == 'file':
            # Retourner juste le nom du fichier
            return value.strip()
        
        else:
            return self.clean_value(value)


class LocationInfoboxParser(WikitextParser):
    """
    Parser spécialisé pour les infoboxes de lieux.
    """
    
    LOCATION_FIELDS = {
        'name': 'string',
        'image': 'file',
        'caption': 'string',
        'pronun': 'string',
        'othernames': 'string_list',
        'location': 'link_list',
        'type': 'string',
        'description': 'string',
        'regions': 'link_list',
        'realms': 'link_list',
        'capital': 'link',
        'governance': 'string',
        'lord': 'link_list',
        'inhabitants': 'link_list',
        'created': 'date',
        'destroyed': 'date',
        'events': 'link_list',
        'gallery': 'string',
    }
    
    def parse_location(self, wikitext: str) -> Optional[Dict[str, Any]]:
        """
        Parse une page de lieu et extrait les données structurées.
        """
        infobox = self.extract_first_infobox(wikitext)
        
        if not infobox:
            return None
        
        template_name = infobox.pop('_template_name', '').lower()
        
        # Vérifier que c'est bien un infobox de lieu
        if 'location' not in template_name and 'kingdom' not in template_name:
            return None
        
        location = {
            '_type': 'Location',
            '_template': template_name,
        }
        
        for field, value in infobox.items():
            field_lower = field.lower()
            field_type = self.LOCATION_FIELDS.get(field_lower, 'string')
            location[field_lower] = self._parse_field(value, field_type)
        
        return location
    
    def _parse_field(self, value: str, field_type: str) -> Any:
        """Parse un champ selon son type (réutilise la logique de CharacterInfoboxParser)."""
        parser = CharacterInfoboxParser()
        return parser._parse_field(value, field_type)


class GenericInfoboxParser(WikitextParser):
    """
    Parser générique qui fonctionne pour TOUS les types d'infobox.
    Détecte automatiquement le type et parse tous les champs.
    """
    
    # Mapping des champs courants vers leurs types
    COMMON_FIELD_TYPES = {
        # Identification
        'name': 'string',
        'image': 'file',
        'caption': 'string',
        'pronun': 'string',
        'othernames': 'string_list',
        
        # Dates
        'birth': 'date',
        'death': 'date',
        'founded': 'date',
        'destroyed': 'date',
        'date': 'date',
        'released': 'date',
        'published': 'date',
        'created': 'date',
        'rule': 'date_range',
        'sailedwest': 'date',
        
        # Lieux
        'location': 'link_list',
        'birthlocation': 'link',
        'deathlocation': 'link',
        'capital': 'link',
        'regions': 'link_list',
        'realms': 'link_list',
        
        # Relations
        'parentage': 'link_list',
        'siblings': 'link_list',
        'spouse': 'link_list',
        'children': 'link_list',
        'author': 'link_list',
        'director': 'link_list',
        'actors': 'link_list',
        'characters': 'link_list',
        
        # Appartenance
        'people': 'link',
        'race': 'link',
        'house': 'link',
        'affiliation': 'link_list',
        'language': 'link_list',
        
        # Nombres
        'age': 'number',
        'pages': 'number',
        'runtime': 'number',
        'chapters': 'number',
        
        # Listes
        'titles': 'string_list',
        'inhabitants': 'string_list',
        'participants': 'link_list',
        'outcome': 'string',
        
        # Autres
        'gender': 'string',
        'position': 'string',
        'notablefor': 'string',
        'description': 'string',
        'summary': 'string',
    }
    
    # Mapping des templates vers des types d'entités
    TEMPLATE_TYPE_MAPPING = {
        'infobox character': 'Character',
        'location infobox': 'Location',
        'kingdom': 'Kingdom',
        'book': 'Book',
        'chapter': 'Chapter',
        'film infobox': 'Film',
        'video game infobox': 'VideoGame',
        'actor': 'Actor',
        'director': 'Director',
        'author infobox': 'Author',
        'artist infobox': 'Artist',
        'battle': 'Battle',
        'war': 'War',
        'song': 'Song',
        'poem infobox': 'Poem',
        'letter infobox': 'Letter',
        'object infobox': 'Object',
        'weapon': 'Weapon',
        'race infobox': 'Race',
        'organization infobox': 'Organization',
        'noble house infobox': 'NobleHouse',
        'plant infobox': 'Plant',
        'episode infobox': 'Episode',
        'album': 'Album',
        'band': 'Band',
        'convention': 'Convention',
        'events': 'Event',
        'mountain': 'Mountain',
        # Templates spécifiques aux races
        'elves infobox': 'Character',
        'dwarves infobox': 'Character',
        'maiar infobox': 'Character',
        'valar infobox': 'Character',
        'men infobox': 'Character',
        'edain infobox': 'Character',
        'noldor infobox': 'Character',
        'sindar infobox': 'Character',
        'gondorian infobox': 'Character',
        'rohirrim infobox': 'Character',
        'dragon infobox': 'Character',
        'eagle infobox': 'Character',
        'ent infobox': 'Character',
        'hobbit infobox': 'Character',
    }
    
    def parse_any(self, wikitext: str, page_title: str = None) -> Optional[Dict[str, Any]]:
        """
        Parse n'importe quel type d'infobox.
        
        Args:
            wikitext: Code source wikitext
            page_title: Titre de la page (optionnel, utilisé comme fallback pour le nom)
            
        Returns:
            Dictionnaire avec les données parsées et le type détecté
        """
        infobox = self.extract_first_infobox(wikitext)
        
        if not infobox:
            return None
        
        template_name = infobox.pop('_template_name', '').lower().strip()
        
        # Déterminer le type d'entité
        entity_type = self.TEMPLATE_TYPE_MAPPING.get(template_name, 'Thing')
        
        # Si le template contient "infobox" mais n'est pas mappé, extraire le type
        if entity_type == 'Thing' and 'infobox' in template_name:
            # Ex: "dragon infobox" -> "Dragon"
            type_part = template_name.replace('infobox', '').strip()
            if type_part:
                entity_type = type_part.title().replace(' ', '')
        
        entity = {
            '_type': entity_type,
            '_template': template_name,
        }
        
        # Parser tous les champs
        for field, value in infobox.items():
            field_lower = field.lower().strip()
            field_type = self.COMMON_FIELD_TYPES.get(field_lower, 'string')
            entity[field_lower] = self._parse_field(value, field_type)
        
        # Ajouter le titre de la page comme nom si pas de nom
        if 'name' not in entity and page_title:
            entity['name'] = page_title
        
        return entity
    
    def _parse_field(self, value: str, field_type: str) -> Any:
        """Parse un champ selon son type."""
        # Réutiliser la logique de CharacterInfoboxParser
        parser = CharacterInfoboxParser()
        return parser._parse_field(value, field_type)
    
    def detect_entity_type(self, template_name: str) -> str:
        """
        Détecte le type d'entité à partir du nom du template.
        
        Args:
            template_name: Nom du template
            
        Returns:
            Type d'entité (Character, Location, Book, etc.)
        """
        template_lower = template_name.lower().strip()
        return self.TEMPLATE_TYPE_MAPPING.get(template_lower, 'Thing')
