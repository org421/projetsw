"""
Parser pour extraire les infoboxes du wikitext avec mwparserfromhell
Version complète avec parsers spécialisés pour chaque type d'infobox

Includes:
- WikitextParser: classe de base pour parser le wikitext
- GenericInfoboxParser: parser générique pour tous les types
- Parsers spécialisés: Character, Battle, Campaign, Kingdom, Location, Object, Person, Race, War
- UnifiedInfoboxParser: détecte automatiquement le type et utilise le bon parser
"""

import re
from typing import Dict, List, Any, Optional, Tuple
import mwparserfromhell as mwp


# =============================================================================
# CLASSE DE BASE: WikitextParser
# =============================================================================

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
        "campaign",
        "object infobox",
        "weapon infobox",
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
        "people infobox",
        "noble house infobox",
        "plant infobox",
        "organization infobox",
        "person infobox",
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
        # Variantes pour les races
        "men infobox",
        "elves infobox",
        "dwarves infobox",
        "maiar infobox",
        "valar infobox",
        "edain infobox",
        "noldor infobox",
        "sindar infobox",
        "gondorian infobox",
        "rohirrim infobox",
        "hobbit infobox",
        "eagle infobox",
        "ent infobox",
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


# =============================================================================
# MÉTHODES UTILITAIRES PARTAGÉES
# =============================================================================

def _parse_date_templates(value: str, parser: WikitextParser) -> Dict[str, Any]:
    """
    Parse les templates de dates Tolkien Gateway.
    Formats: {{FA|532}}, {{SA|1697}}, {{TA|3021}}, {{SR|1328}}, {{YT|1300}}, {{FO|1}}
    
    FA = First Age, SA = Second Age, TA = Third Age
    SR = Shire Reckoning, YT = Years of the Trees, FO = Fourth Age
    """
    result = {
        'raw': value,
        'dates': [],
        'text': ''
    }
    
    # Pattern pour les templates de date: {{XX|YYYY}} ou {{XX|YYYY|n}}
    date_pattern = r'\{\{(FA|SA|TA|SR|YT|FO)\|(\d+)(?:\|[^}]*)?\}\}'
    
    matches = re.findall(date_pattern, value)
    
    age_names = {
        'FA': 'First Age',
        'SA': 'Second Age',
        'TA': 'Third Age',
        'SR': 'Shire Reckoning',
        'YT': 'Years of the Trees',
        'FO': 'Fourth Age'
    }
    
    for age, year in matches:
        result['dates'].append({
            'age': age,
            'age_name': age_names.get(age, age),
            'year': int(year)
        })
    
    # Créer une version texte lisible
    text = value
    for age, year in matches:
        text = re.sub(
            r'\{\{' + age + r'\|' + year + r'(?:\|[^}]*)?\}\}',
            f"{age} {year}",
            text
        )
    
    result['text'] = parser.clean_value(text)
    result['links'] = parser.extract_links_from_value(value)
    
    return result


def _parse_field(value: str, field_type: str, parser: WikitextParser) -> Any:
    """
    Parse un champ selon son type.
    
    Args:
        value: Valeur brute
        field_type: Type du champ
        parser: Instance de WikitextParser pour les méthodes utilitaires
        
    Returns:
        Valeur parsée
    """
    if field_type == 'string':
        return parser.clean_value(value)
    
    elif field_type == 'link':
        links = parser.extract_links_from_value(value)
        return links[0] if links else parser.clean_value(value)
    
    elif field_type == 'link_list':
        links = parser.extract_links_from_value(value)
        if links:
            return links
        # Si pas de liens, essayer de splitter par <br> ou ; ou newline
        clean = parser.clean_value(value)
        if '<br' in value.lower() or ';' in clean or '\n' in value:
            items = re.split(r'<br\s*/?>|;|\n', value)
            result = []
            for item in items:
                cleaned = parser.clean_value(item)
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
                cleaned = parser.clean_value(item)
                if cleaned:
                    result.append(cleaned)
            return result if result else []
        clean = parser.clean_value(value)
        return [clean] if clean else []
    
    elif field_type == 'date':
        return _parse_date_templates(value, parser)
    
    elif field_type == 'date_range':
        return _parse_date_templates(value, parser)
    
    elif field_type == 'number':
        clean = parser.clean_value(value)
        try:
            return int(clean.replace(',', '').replace('.', ''))
        except ValueError:
            return clean
    
    elif field_type == 'file':
        return value.strip()
    
    else:
        return parser.clean_value(value)


# =============================================================================
# PARSER SPÉCIALISÉ: CHARACTER
# =============================================================================

class CharacterInfoboxParser(WikitextParser):
    """
    Parser spécialisé pour les infoboxes de personnages.
    Supporte: {{Infobox character}}, {{Men infobox}}, etc.
    """
    
    TEMPLATE_NAMES = [
        'infobox character',
        'men infobox',
        'elves infobox',
        'dwarves infobox',
        'maiar infobox',
        'valar infobox',
        'edain infobox',
        'noldor infobox',
        'sindar infobox',
        'gondorian infobox',
        'rohirrim infobox',
        'hobbit infobox',
        'dragon infobox',
        'eagle infobox',
        'ent infobox',
    ]
    
    # Champs connus de l'infobox character avec leurs types
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
        'family': 'link',
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
        'clothing': 'string',
        
        # Équipement
        'weapons': 'link_list',
        'weapon': 'link_list',
        'steed': 'link',
        
        # Notable
        'notablefor': 'string',
        
        # Médias
        'audio': 'file',
        'audiocaption': 'string',
        'timeline': 'string',
        'gallery': 'string',
    }
    
    # Mapping vers schema.org
    SCHEMA_MAPPING = {
        'name': 'schema:name',
        'image': 'schema:image',
        'birth': 'schema:birthDate',
        'birthlocation': 'schema:birthPlace',
        'death': 'schema:deathDate',
        'deathlocation': 'schema:deathPlace',
        'gender': 'schema:gender',
        'spouse': 'schema:spouse',
        'children': 'schema:children',
        'parentage': 'schema:parent',
        'siblings': 'schema:sibling',
        'affiliation': 'schema:affiliation',
        'position': 'schema:jobTitle',
        'othernames': 'schema:alternateName',
        'notablefor': 'schema:description',
    }
    
    def parse_character(self, wikitext: str, page_title: str = None) -> Optional[Dict[str, Any]]:
        """
        Parse une page de personnage et extrait les données structurées.
        
        Args:
            wikitext: Code source wikitext de la page
            page_title: Titre de la page (fallback pour le nom)
            
        Returns:
            Dictionnaire avec les données du personnage
        """
        infobox = self.extract_first_infobox(wikitext)
        
        if not infobox:
            return None
        
        template_name = infobox.pop('_template_name', '').lower()
        
        # Vérifier que c'est bien un infobox character ou variante
        is_character = 'character' in template_name or any(
            variant in template_name for variant in ['men', 'elves', 'dwarves', 'maiar', 
            'valar', 'hobbit', 'dragon', 'eagle', 'ent', 'edain', 'noldor', 'sindar',
            'gondorian', 'rohirrim']
        )
        
        if not is_character:
            return None
        
        character = {
            '_type': 'Character',
            '_template': template_name,
            '_schema_type': 'schema:Person',
        }
        
        for field, value in infobox.items():
            field_lower = field.lower()
            field_type = self.CHARACTER_FIELDS.get(field_lower, 'string')
            character[field_lower] = _parse_field(value, field_type, self)
        
        # Fallback pour le nom
        if 'name' not in character and page_title:
            character['name'] = page_title
        
        return character
    
    def _parse_field(self, value: str, field_type: str) -> Any:
        """Parse un champ selon son type."""
        return _parse_field(value, field_type, self)


# =============================================================================
# PARSER SPÉCIALISÉ: BATTLE
# =============================================================================

class BattleInfoboxParser(WikitextParser):
    """
    Parser spécialisé pour le template {{Battle}}.
    """
    
    TEMPLATE_NAMES = ['battle']
    
    FIELDS = {
        'name': 'string',
        'image': 'file',
        'conflict': 'link',
        'date': 'date',
        'place': 'link_list',
        'result': 'string',
        'side1': 'link_list',
        'side2': 'link_list',
        'commanders1': 'link_list',
        'commanders2': 'link_list',
        'forces1': 'string',
        'forces2': 'string',
        'casual1': 'string',
        'casual2': 'string',
    }
    
    SCHEMA_MAPPING = {
        'name': 'schema:name',
        'image': 'schema:image',
        'date': 'schema:startDate',
        'place': 'schema:location',
        'result': 'schema:result',
    }
    
    def parse_battle(self, wikitext: str, page_title: str = None) -> Optional[Dict[str, Any]]:
        """Parse une page de bataille."""
        infobox = self.extract_first_infobox(wikitext)
        
        if not infobox:
            return None
        
        template_name = infobox.pop('_template_name', '').lower()
        
        if 'battle' not in template_name:
            return None
        
        battle = {
            '_type': 'Battle',
            '_template': template_name,
            '_schema_type': 'schema:Event',
        }
        
        for field, value in infobox.items():
            field_lower = field.lower()
            field_type = self.FIELDS.get(field_lower, 'string')
            battle[field_lower] = _parse_field(value, field_type, self)
        
        if 'name' not in battle and page_title:
            battle['name'] = page_title
        
        return battle


# =============================================================================
# PARSER SPÉCIALISÉ: CAMPAIGN
# =============================================================================

class CampaignInfoboxParser(WikitextParser):
    """
    Parser spécialisé pour le template {{Campaign}}.
    """
    
    TEMPLATE_NAMES = ['campaign']
    
    FIELDS = {
        'name': 'string',
        'battles': 'link_list',
    }
    
    def parse_campaign(self, wikitext: str, page_title: str = None) -> Optional[Dict[str, Any]]:
        """Parse une page de campagne."""
        infobox = self.extract_first_infobox(wikitext)
        
        if not infobox:
            return None
        
        template_name = infobox.pop('_template_name', '').lower()
        
        if 'campaign' not in template_name:
            return None
        
        campaign = {
            '_type': 'Campaign',
            '_template': template_name,
            '_schema_type': 'schema:Event',
        }
        
        for field, value in infobox.items():
            field_lower = field.lower()
            field_type = self.FIELDS.get(field_lower, 'string')
            campaign[field_lower] = _parse_field(value, field_type, self)
        
        if 'name' not in campaign and page_title:
            campaign['name'] = page_title
        
        return campaign


# =============================================================================
# PARSER SPÉCIALISÉ: KINGDOM
# =============================================================================

class KingdomInfoboxParser(WikitextParser):
    """
    Parser spécialisé pour le template {{Kingdom}}.
    """
    
    TEMPLATE_NAMES = ['kingdom']
    
    FIELDS = {
        'name': 'string',
        'image': 'file',
        'caption': 'string',
        'pronun': 'string',
        'othernames': 'string_list',
        'location': 'link_list',
        'capital': 'link',
        'settlements': 'link_list',
        'regions': 'link_list',
        'population': 'string',
        'language': 'link_list',
        'govern1': 'string',
        'govern2': 'string',
        'govern3': 'string',
        'currency': 'string',
        'holiday': 'string',
        'precededby': 'link_list',
        'event1': 'string',
        'event1date': 'date',
        'event2': 'string',
        'event2date': 'date',
        'event3': 'string',
        'event3date': 'date',
        'event4': 'string',
        'event4date': 'date',
        'event5': 'string',
        'event5date': 'date',
        'followedby': 'link_list',
        'audio': 'file',
        'audiocaption': 'string',
        'map': 'file',
    }
    
    SCHEMA_MAPPING = {
        'name': 'schema:name',
        'image': 'schema:image',
        'capital': 'schema:capitalCity',
        'location': 'schema:containedInPlace',
        'population': 'schema:population',
        'othernames': 'schema:alternateName',
    }
    
    def parse_kingdom(self, wikitext: str, page_title: str = None) -> Optional[Dict[str, Any]]:
        """Parse une page de royaume."""
        infobox = self.extract_first_infobox(wikitext)
        
        if not infobox:
            return None
        
        template_name = infobox.pop('_template_name', '').lower()
        
        if 'kingdom' not in template_name:
            return None
        
        kingdom = {
            '_type': 'Kingdom',
            '_template': template_name,
            '_schema_type': 'schema:Country',
        }
        
        for field, value in infobox.items():
            field_lower = field.lower()
            field_type = self.FIELDS.get(field_lower, 'string')
            kingdom[field_lower] = _parse_field(value, field_type, self)
        
        if 'name' not in kingdom and page_title:
            kingdom['name'] = page_title
        
        return kingdom


# =============================================================================
# PARSER SPÉCIALISÉ: LOCATION
# =============================================================================

class LocationInfoboxParser(WikitextParser):
    """
    Parser spécialisé pour le template {{Location infobox}}.
    """
    
    TEMPLATE_NAMES = ['location infobox', 'mountain']
    
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
        'settlements': 'link_list',
        'realms': 'link_list',
        'capital': 'link',
        'governance': 'string',
        'lord': 'link_list',
        'inhabitants': 'link_list',
        'created': 'date',
        'destroyed': 'date',
        'rebuilt': 'date',
        'events': 'link_list',
        'audio': 'file',
        'audiocaption': 'string',
        'map': 'file',
        'timeline': 'string',
        'gallery': 'string',
    }
    
    SCHEMA_MAPPING = {
        'name': 'schema:name',
        'image': 'schema:image',
        'description': 'schema:description',
        'location': 'schema:containedInPlace',
        'type': 'schema:additionalType',
        'othernames': 'schema:alternateName',
    }
    
    def parse_location(self, wikitext: str, page_title: str = None) -> Optional[Dict[str, Any]]:
        """Parse une page de lieu."""
        infobox = self.extract_first_infobox(wikitext)
        
        if not infobox:
            return None
        
        template_name = infobox.pop('_template_name', '').lower()
        
        # Vérifier que c'est bien un infobox de lieu
        if 'location' not in template_name and 'mountain' not in template_name:
            return None
        
        location = {
            '_type': 'Location',
            '_template': template_name,
            '_schema_type': 'schema:Place',
        }
        
        for field, value in infobox.items():
            field_lower = field.lower()
            field_type = self.LOCATION_FIELDS.get(field_lower, 'string')
            location[field_lower] = _parse_field(value, field_type, self)
        
        if 'name' not in location and page_title:
            location['name'] = page_title
        
        return location
    
    def _parse_field(self, value: str, field_type: str) -> Any:
        """Parse un champ selon son type."""
        return _parse_field(value, field_type, self)


# =============================================================================
# PARSER SPÉCIALISÉ: OBJECT
# =============================================================================

class ObjectInfoboxParser(WikitextParser):
    """
    Parser spécialisé pour le template {{Object infobox}} et {{Weapon infobox}}.
    """
    
    TEMPLATE_NAMES = ['object infobox', 'weapon infobox']
    
    FIELDS = {
        'name': 'string',
        'image': 'file',
        'caption': 'string',
        'pronun': 'string',
        'othernames': 'string_list',
        'location': 'link_list',
        'owner': 'link_list',
        'type': 'string',
        'appearance': 'string',
        'creator': 'link_list',
        'created': 'date',
        'createdlocation': 'link',
        'destroyer': 'link_list',
        'destroyed': 'date',
        'destroyedlocation': 'link',
        'notablefor': 'string',
        'audio': 'file',
        'audiocaption': 'string',
    }
    
    SCHEMA_MAPPING = {
        'name': 'schema:name',
        'image': 'schema:image',
        'creator': 'schema:creator',
        'type': 'schema:additionalType',
        'othernames': 'schema:alternateName',
        'notablefor': 'schema:description',
    }
    
    def parse_object(self, wikitext: str, page_title: str = None) -> Optional[Dict[str, Any]]:
        """Parse une page d'objet."""
        infobox = self.extract_first_infobox(wikitext)
        
        if not infobox:
            return None
        
        template_name = infobox.pop('_template_name', '').lower()
        
        if 'object' not in template_name and 'weapon' not in template_name:
            return None
        
        obj = {
            '_type': 'Object',
            '_template': template_name,
            '_schema_type': 'schema:Thing',
        }
        
        for field, value in infobox.items():
            field_lower = field.lower()
            field_type = self.FIELDS.get(field_lower, 'string')
            obj[field_lower] = _parse_field(value, field_type, self)
        
        if 'name' not in obj and page_title:
            obj['name'] = page_title
        
        return obj


# =============================================================================
# PARSER SPÉCIALISÉ: PERSON (personnes réelles)
# =============================================================================

class PersonInfoboxParser(WikitextParser):
    """
    Parser spécialisé pour le template {{Person infobox}}.
    Pour les personnes réelles (auteurs, acteurs, artistes).
    """
    
    TEMPLATE_NAMES = ['person infobox', 'author infobox', 'artist infobox', 'actor']
    
    FIELDS = {
        'name': 'string',
        'image': 'file',
        'born': 'date',
        'died': 'date',
        'education': 'string',
        'occupation': 'string_list',
        'location': 'link_list',
        'website': 'string',
    }
    
    SCHEMA_MAPPING = {
        'name': 'schema:name',
        'image': 'schema:image',
        'born': 'schema:birthDate',
        'died': 'schema:deathDate',
        'education': 'schema:alumniOf',
        'occupation': 'schema:hasOccupation',
        'location': 'schema:homeLocation',
        'website': 'schema:url',
    }
    
    def parse_person(self, wikitext: str, page_title: str = None) -> Optional[Dict[str, Any]]:
        """Parse une page de personne réelle."""
        infobox = self.extract_first_infobox(wikitext)
        
        if not infobox:
            return None
        
        template_name = infobox.pop('_template_name', '').lower()
        
        if not any(kw in template_name for kw in ['person', 'author', 'artist', 'actor']):
            return None
        
        person = {
            '_type': 'Person',
            '_template': template_name,
            '_schema_type': 'schema:Person',
        }
        
        for field, value in infobox.items():
            field_lower = field.lower()
            field_type = self.FIELDS.get(field_lower, 'string')
            person[field_lower] = _parse_field(value, field_type, self)
        
        if 'name' not in person and page_title:
            person['name'] = page_title
        
        return person


# =============================================================================
# PARSER SPÉCIALISÉ: RACE
# =============================================================================

class RaceInfoboxParser(WikitextParser):
    """
    Parser spécialisé pour le template {{Race infobox}}.
    """
    
    TEMPLATE_NAMES = ['race infobox', 'people infobox']
    
    FIELDS = {
        'name': 'string',
        'image': 'file',
        'caption': 'string',
        'pronun': 'string',
        'othernames': 'string_list',
        'origin': 'link_list',
        'location': 'link_list',
        'affiliation': 'link_list',
        'rivalry': 'link_list',
        'language': 'link_list',
        'people': 'link_list',
        'members': 'link_list',
        'lifespan': 'string',
        'distinctions': 'string',
        'height': 'string',
        'hair': 'string',
        'skin': 'string',
        'clothing': 'string',
        'weapons': 'link_list',
    }
    
    SCHEMA_MAPPING = {
        'name': 'schema:name',
        'image': 'schema:image',
        'othernames': 'schema:alternateName',
        'location': 'schema:location',
    }
    
    def parse_race(self, wikitext: str, page_title: str = None) -> Optional[Dict[str, Any]]:
        """Parse une page de race/peuple."""
        infobox = self.extract_first_infobox(wikitext)
        
        if not infobox:
            return None
        
        template_name = infobox.pop('_template_name', '').lower()
        
        if 'race' not in template_name and 'people' not in template_name:
            return None
        
        race = {
            '_type': 'Race',
            '_template': template_name,
            '_schema_type': 'schema:Thing',
        }
        
        for field, value in infobox.items():
            field_lower = field.lower()
            field_type = self.FIELDS.get(field_lower, 'string')
            race[field_lower] = _parse_field(value, field_type, self)
        
        if 'name' not in race and page_title:
            race['name'] = page_title
        
        return race


# =============================================================================
# PARSER SPÉCIALISÉ: WAR
# =============================================================================

class WarInfoboxParser(WikitextParser):
    """
    Parser spécialisé pour le template {{War}}.
    """
    
    TEMPLATE_NAMES = ['war']
    
    FIELDS = {
        'name': 'string',
        'image': 'file',
        'previous': 'link',
        'next': 'link',
        'begin': 'date',
        'end': 'date',
        'place': 'link_list',
        'result': 'string',
        'battles': 'link_list',
        'side1': 'link_list',
        'side2': 'link_list',
        'commanders1': 'link_list',
        'commanders2': 'link_list',
    }
    
    SCHEMA_MAPPING = {
        'name': 'schema:name',
        'image': 'schema:image',
        'begin': 'schema:startDate',
        'end': 'schema:endDate',
        'place': 'schema:location',
    }
    
    def parse_war(self, wikitext: str, page_title: str = None) -> Optional[Dict[str, Any]]:
        """Parse une page de guerre."""
        infobox = self.extract_first_infobox(wikitext)
        
        if not infobox:
            return None
        
        template_name = infobox.pop('_template_name', '').lower()
        
        if 'war' not in template_name:
            return None
        
        war = {
            '_type': 'War',
            '_template': template_name,
            '_schema_type': 'schema:Event',
        }
        
        for field, value in infobox.items():
            field_lower = field.lower()
            field_type = self.FIELDS.get(field_lower, 'string')
            war[field_lower] = _parse_field(value, field_type, self)
        
        if 'name' not in war and page_title:
            war['name'] = page_title
        
        return war


# =============================================================================
# PARSER GÉNÉRIQUE (GARDE LA COMPATIBILITÉ)
# =============================================================================

class GenericInfoboxParser(WikitextParser):
    """
    Parser générique qui fonctionne pour TOUS les types d'infobox.
    Détecte automatiquement le type et parse tous les champs.
    
    GARDE LA COMPATIBILITÉ avec le code existant.
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
        'born': 'date',
        'died': 'date',
        'founded': 'date',
        'destroyed': 'date',
        'date': 'date',
        'released': 'date',
        'published': 'date',
        'created': 'date',
        'rule': 'date_range',
        'sailedwest': 'date',
        'begin': 'date',
        'end': 'date',
        
        # Lieux
        'location': 'link_list',
        'birthlocation': 'link',
        'deathlocation': 'link',
        'capital': 'link',
        'regions': 'link_list',
        'realms': 'link_list',
        'place': 'link_list',
        
        # Relations
        'parentage': 'link_list',
        'siblings': 'link_list',
        'spouse': 'link_list',
        'children': 'link_list',
        'author': 'link_list',
        'director': 'link_list',
        'actors': 'link_list',
        'characters': 'link_list',
        'creator': 'link_list',
        'owner': 'link_list',
        
        # Appartenance
        'people': 'link',
        'race': 'link',
        'house': 'link',
        'affiliation': 'link_list',
        'language': 'link_list',
        
        # Conflits
        'side1': 'link_list',
        'side2': 'link_list',
        'commanders1': 'link_list',
        'commanders2': 'link_list',
        'battles': 'link_list',
        'conflict': 'link',
        
        # Nombres
        'age': 'number',
        'pages': 'number',
        'runtime': 'number',
        'chapters': 'number',
        
        # Listes
        'titles': 'string_list',
        'inhabitants': 'string_list',
        'participants': 'link_list',
        'members': 'link_list',
        'settlements': 'link_list',
        'weapons': 'link_list',
        
        # Autres
        'gender': 'string',
        'position': 'string',
        'notablefor': 'string',
        'description': 'string',
        'summary': 'string',
        'result': 'string',
        'outcome': 'string',
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
        'campaign': 'Campaign',
        'song': 'Song',
        'poem infobox': 'Poem',
        'letter infobox': 'Letter',
        'object infobox': 'Object',
        'weapon infobox': 'Weapon',
        'race infobox': 'Race',
        'people infobox': 'People',
        'organization infobox': 'Organization',
        'noble house infobox': 'NobleHouse',
        'plant infobox': 'Plant',
        'episode infobox': 'Episode',
        'album': 'Album',
        'band': 'Band',
        'convention': 'Convention',
        'events': 'Event',
        'mountain': 'Mountain',
        'person infobox': 'Person',
        # Templates spécifiques aux races -> Character
        'men infobox': 'Character',
        'elves infobox': 'Character',
        'dwarves infobox': 'Character',
        'maiar infobox': 'Character',
        'valar infobox': 'Character',
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
    
    def __init__(self):
        super().__init__()
        # Instancier les parsers spécialisés
        self._specialized_parsers = {
            'Character': CharacterInfoboxParser(),
            'Battle': BattleInfoboxParser(),
            'Campaign': CampaignInfoboxParser(),
            'Kingdom': KingdomInfoboxParser(),
            'Location': LocationInfoboxParser(),
            'Object': ObjectInfoboxParser(),
            'Weapon': ObjectInfoboxParser(),
            'Person': PersonInfoboxParser(),
            'Author': PersonInfoboxParser(),
            'Artist': PersonInfoboxParser(),
            'Actor': PersonInfoboxParser(),
            'Race': RaceInfoboxParser(),
            'People': RaceInfoboxParser(),
            'War': WarInfoboxParser(),
        }
    
    def parse_any(self, wikitext: str, page_title: str = None) -> Optional[Dict[str, Any]]:
        """
        Parse n'importe quel type d'infobox.
        Utilise le parser spécialisé si disponible, sinon parsing générique.
        
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
            type_part = template_name.replace('infobox', '').strip()
            if type_part:
                entity_type = type_part.title().replace(' ', '')
        
        # Essayer d'utiliser un parser spécialisé
        if entity_type in self._specialized_parsers:
            parser = self._specialized_parsers[entity_type]
            method_name = f"parse_{entity_type.lower()}"
            if hasattr(parser, method_name):
                result = getattr(parser, method_name)(wikitext, page_title)
                if result:
                    return result
        
        # Parsing générique
        entity = {
            '_type': entity_type,
            '_template': template_name,
        }
        
        for field, value in infobox.items():
            field_lower = field.lower().strip()
            field_type = self.COMMON_FIELD_TYPES.get(field_lower, 'string')
            entity[field_lower] = _parse_field(value, field_type, self)
        
        # Ajouter le titre de la page comme nom si pas de nom
        if 'name' not in entity and page_title:
            entity['name'] = page_title
        
        return entity
    
    def _parse_field(self, value: str, field_type: str) -> Any:
        """Parse un champ selon son type."""
        return _parse_field(value, field_type, self)
    
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


# =============================================================================
# PARSER UNIFIÉ (NOUVEAU)
# =============================================================================

class UnifiedInfoboxParser(GenericInfoboxParser):
    """
    Parser unifié qui combine tous les parsers spécialisés.
    Détecte automatiquement le type et utilise le parser approprié.
    
    C'est la classe recommandée à utiliser dans le code principal.
    """
    
    def parse(self, wikitext: str, page_title: str = None) -> Optional[Dict[str, Any]]:
        """
        Alias pour parse_any() pour une API plus simple.
        """
        return self.parse_any(wikitext, page_title)
    
    def parse_with_type(self, wikitext: str, entity_type: str, page_title: str = None) -> Optional[Dict[str, Any]]:
        """
        Parse avec un type spécifié (force l'utilisation d'un parser spécifique).
        
        Args:
            wikitext: Code source wikitext
            entity_type: Type d'entité (Character, Battle, etc.)
            page_title: Titre de la page
        """
        entity_type_title = entity_type.title()
        
        if entity_type_title in self._specialized_parsers:
            parser = self._specialized_parsers[entity_type_title]
            method_name = f"parse_{entity_type.lower()}"
            if hasattr(parser, method_name):
                return getattr(parser, method_name)(wikitext, page_title)
        
        return self.parse_any(wikitext, page_title)


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def get_parser_for_template(template_name: str) -> Optional[WikitextParser]:
    """
    Retourne le parser approprié pour un nom de template.
    
    Args:
        template_name: Nom du template (ex: "infobox character")
        
    Returns:
        Instance du parser ou None
    """
    template_lower = template_name.lower().strip()
    
    parsers_map = {
        'infobox character': CharacterInfoboxParser(),
        'men infobox': CharacterInfoboxParser(),
        'elves infobox': CharacterInfoboxParser(),
        'battle': BattleInfoboxParser(),
        'campaign': CampaignInfoboxParser(),
        'kingdom': KingdomInfoboxParser(),
        'location infobox': LocationInfoboxParser(),
        'object infobox': ObjectInfoboxParser(),
        'weapon infobox': ObjectInfoboxParser(),
        'person infobox': PersonInfoboxParser(),
        'author infobox': PersonInfoboxParser(),
        'race infobox': RaceInfoboxParser(),
        'people infobox': RaceInfoboxParser(),
        'war': WarInfoboxParser(),
    }
    
    return parsers_map.get(template_lower)


def get_all_supported_templates() -> List[str]:
    """Retourne la liste de tous les templates supportés."""
    templates = []
    for parser_class in [CharacterInfoboxParser, BattleInfoboxParser, CampaignInfoboxParser,
                         KingdomInfoboxParser, LocationInfoboxParser, ObjectInfoboxParser,
                         PersonInfoboxParser, RaceInfoboxParser, WarInfoboxParser]:
        templates.extend(parser_class.TEMPLATE_NAMES)
    return templates


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Classes de base
    'WikitextParser',
    'GenericInfoboxParser',
    
    # Parsers spécialisés
    'CharacterInfoboxParser',
    'BattleInfoboxParser',
    'CampaignInfoboxParser',
    'KingdomInfoboxParser',
    'LocationInfoboxParser',
    'ObjectInfoboxParser',
    'PersonInfoboxParser',
    'RaceInfoboxParser',
    'WarInfoboxParser',
    
    # Parser unifié (recommandé)
    'UnifiedInfoboxParser',
    
    # Fonctions utilitaires
    'get_parser_for_template',
    'get_all_supported_templates',
]