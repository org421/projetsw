"""
Parsers pour extraire les infoboxes du wikitext avec mwparserfromhell.
Support de multiples types d'infobox avec parsers spécialisés.
"""

import re
from typing import Dict, List, Any, Optional, Tuple
import mwparserfromhell as mwp


class WikitextParser:
    """Parse les infoboxes du wikitext MediaWiki."""
    
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
        self._infobox_names = set(name.lower() for name in self.KNOWN_INFOBOX_TEMPLATES)
    
    def parse(self, wikitext: str) -> mwp.wikicode.Wikicode:
        return mwp.parse(wikitext)
    
    def is_infobox_template(self, template_name: str) -> bool:
        name_lower = template_name.lower().strip()
        return name_lower in self._infobox_names or 'infobox' in name_lower
    
    def extract_infoboxes(self, wikitext: str) -> List[Dict[str, Any]]:
        """Extrait toutes les infoboxes du wikitext."""
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
        params = {}
        
        for param in template.params:
            name = str(param.name).strip()
            value = str(param.value).strip()
            
            if value:
                params[name] = value
        
        return params
    
    def extract_first_infobox(self, wikitext: str) -> Optional[Dict[str, Any]]:
        infoboxes = self.extract_infoboxes(wikitext)
        return infoboxes[0] if infoboxes else None
    
    def extract_links(self, wikitext: str) -> List[Dict[str, str]]:
        """Extrait tous les liens internes du wikitext."""
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
        links = self.extract_links(value)
        return [link['target'] for link in links]
    
    def clean_value(self, value: str) -> str:
        """Nettoie une valeur en retirant le markup wiki."""
        parsed = self.parse(value)
        return parsed.strip_code().strip()
    
    def parse_infobox_value(self, value: str) -> Dict[str, Any]:
        """Parse une valeur d'infobox en structure enrichie."""
        return {
            'raw': value,
            'clean': self.clean_value(value),
            'links': self.extract_links_from_value(value),
            'has_ref': '{{' in value or '<ref' in value
        }
    
    def extract_infobox_structured(self, wikitext: str) -> Optional[Dict[str, Any]]:
        """Extrait la première infobox avec valeurs structurées."""
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


def _parse_date_templates(value: str, parser: WikitextParser) -> Dict[str, Any]:
    """Parse les templates de dates Tolkien Gateway."""
    result = {
        'raw': value,
        'dates': [],
        'text': ''
    }
    
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
    """Parse un champ selon son type."""
    if field_type == 'string':
        return parser.clean_value(value)
    
    elif field_type == 'link':
        links = parser.extract_links_from_value(value)
        return links[0] if links else parser.clean_value(value)
    
    elif field_type == 'link_list':
        links = parser.extract_links_from_value(value)
        if links:
            return links
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
    
    #elif field_type == 'date':
    #   return _parse_date_templates(value, parser)
    elif field_type == 'date':
        # MODIFICATION ICI : On extrait le texte lisible pour éviter le "b0"
        date_data = _parse_date_templates(value, parser)
        return date_data['text'] if date_data['text'] else parser.clean_value(value)
    
    #elif field_type == 'date_range':
    #    return _parse_date_templates(value, parser)
    
    elif field_type == 'date_range':
        # MODIFICATION ICI AUSSI
        date_data = _parse_date_templates(value, parser)
        return date_data['text'] if date_data['text'] else parser.clean_value(value)

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


class CharacterInfoboxParser(WikitextParser):
    """Parse les infoboxes de personnages."""
    
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
    
    CHARACTER_FIELDS = {
        'name': 'string',
        'image': 'file',
        'caption': 'string',
        'pronun': 'string',
        'othernames': 'string_list',
        'people': 'link',
        'race': 'link',
        'titles': 'string_list',
        'position': 'string',
        'location': 'link_list',
        'affiliation': 'link_list',
        'language': 'link_list',
        'birth': 'date',
        'birthlocation': 'link',
        'death': 'date',
        'deathlocation': 'link',
        'age': 'number',
        'rule': 'date_range',
        'sailedwest': 'date',
        'sailedfrom': 'link',
        'house': 'link',
        'family': 'link',
        'heritage': 'string',
        'parentage': 'link_list',
        'siblings': 'link_list',
        'spouse': 'link_list',
        'children': 'link_list',
        'gender': 'string',
        'height': 'string',
        'hair': 'string',
        'eyes': 'string',
        'clothing': 'string',
        'weapons': 'link_list',
        'weapon': 'link_list',
        'steed': 'link',
        'notablefor': 'string',
        'audio': 'file',
        'audiocaption': 'string',
        'timeline': 'string',
        'gallery': 'string',
    }
    
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
        infobox = self.extract_first_infobox(wikitext)
        
        if not infobox:
            return None
        
        template_name = infobox.pop('_template_name', '').lower()
        
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
        
        if 'name' not in character and page_title:
            character['name'] = page_title
        
        return character
    
    def _parse_field(self, value: str, field_type: str) -> Any:
        return _parse_field(value, field_type, self)


class BattleInfoboxParser(WikitextParser):
    """Parse les infoboxes de batailles."""
    
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


class CampaignInfoboxParser(WikitextParser):
    """Parse les infoboxes de campagnes militaires."""
    
    TEMPLATE_NAMES = ['campaign']
    
    FIELDS = {
        'name': 'string',
        'battles': 'link_list',
    }
    
    def parse_campaign(self, wikitext: str, page_title: str = None) -> Optional[Dict[str, Any]]:
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


class KingdomInfoboxParser(WikitextParser):
    """Parse les infoboxes de royaumes."""
    
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


class LocationInfoboxParser(WikitextParser):
    """Parse les infoboxes de lieux."""
    
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
        infobox = self.extract_first_infobox(wikitext)
        
        if not infobox:
            return None
        
        template_name = infobox.pop('_template_name', '').lower()
        
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
        return _parse_field(value, field_type, self)



class ObjectInfoboxParser(WikitextParser):
    """Parse les infoboxes d'objets et armes."""
    
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


class PersonInfoboxParser(WikitextParser):
    """Parse les infoboxes de personnes réelles."""
    
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


class RaceInfoboxParser(WikitextParser):
    """Parse les infoboxes de races et peuples."""
    
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


class WarInfoboxParser(WikitextParser):
    """Parse les infoboxes de guerres."""
    
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



class BookInfoboxParser(WikitextParser):
    """Parse les infoboxes de livres."""
    
    TEMPLATE_NAMES = ['book']
    
    FIELDS = {
        'title': 'string',
        'image': 'file',
        'author': 'link_list',
        'foreword': 'link_list',
        'introduction': 'link_list',
        'editor': 'link_list',
        'contributors': 'link_list',
        'translator': 'link_list',
        'illustrator': 'link_list',
        'genre': 'string_list',
        'subject': 'string_list',
        'publisher': 'link',
        'publisheruk': 'link',
        'publisherus': 'link',
        'date': 'date',
        'dateuk': 'date',
        'dateus': 'date',
        'format': 'string',
        'pages': 'number',
        'isbn': 'string',
        'isbn2': 'string',
        'noisbn': 'string',
        'issn': 'string',
        'ice': 'string',
        'coverprice': 'string',
        'series': 'link',
        'precededby': 'link',
        'followedby': 'link',
        'gallery': 'string',
    }
    
    SCHEMA_MAPPING = {
        'title': 'schema:name',
        'image': 'schema:image',
        'author': 'schema:author',
        'illustrator': 'schema:illustrator',
        'translator': 'schema:translator',
        'publisher': 'schema:publisher',
        'date': 'schema:datePublished',
        'isbn': 'schema:isbn',
        'pages': 'schema:numberOfPages',
        'genre': 'schema:genre',
        'language': 'schema:inLanguage',
    }
    
    def parse_book(self, wikitext: str, page_title: str = None) -> Optional[Dict[str, Any]]:
        infobox = self.extract_first_infobox(wikitext)
        
        if not infobox:
            return None
        
        template_name = infobox.pop('_template_name', '').lower()
        
        if 'book' not in template_name:
            return None
        
        book = {
            '_type': 'Book',
            '_template': template_name,
            '_schema_type': 'schema:Book',
        }
        
        for field, value in infobox.items():
            field_lower = field.lower()
            field_type = self.FIELDS.get(field_lower, 'string')
            book[field_lower] = _parse_field(value, field_type, self)
        
        # Gestion des ISBN multiples (facultatif, pour regrouper)
        isbns = []
        if 'isbn' in book and book['isbn']: isbns.append(book['isbn'])
        if 'isbn2' in book and book['isbn2']: isbns.append(book['isbn2'])
        if isbns:
            book['all_isbns'] = isbns

        if 'title' not in book and page_title:
            book['title'] = page_title
            book['name'] = page_title # Fallback standard
        
        return book
    
class GenericInfoboxParser(WikitextParser):
    """Parser générique fonctionnant pour tous les types d'infobox."""
    
    COMMON_FIELD_TYPES = {
        'name': 'string',
        'image': 'file',
        'caption': 'string',
        'pronun': 'string',
        'othernames': 'string_list',
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
        'location': 'link_list',
        'birthlocation': 'link',
        'deathlocation': 'link',
        'capital': 'link',
        'regions': 'link_list',
        'realms': 'link_list',
        'place': 'link_list',
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
        'people': 'link',
        'race': 'link',
        'house': 'link',
        'affiliation': 'link_list',
        'language': 'link_list',
        'side1': 'link_list',
        'side2': 'link_list',
        'commanders1': 'link_list',
        'commanders2': 'link_list',
        'battles': 'link_list',
        'conflict': 'link',
        'age': 'number',
        'pages': 'number',
        'runtime': 'number',
        'chapters': 'number',
        'titles': 'string_list',
        'inhabitants': 'string_list',
        'participants': 'link_list',
        'members': 'link_list',
        'settlements': 'link_list',
        'weapons': 'link_list',
        'gender': 'string',
        'position': 'string',
        'notablefor': 'string',
        'description': 'string',
        'summary': 'string',
        'result': 'string',
        'outcome': 'string',
    }
    
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
            'Book': BookInfoboxParser(),  # <--- AJOUTER CETTE LIGNE
        }
    
    def parse_any(self, wikitext: str, page_title: str = None) -> Optional[Dict[str, Any]]:
        """Parse n'importe quel type d'infobox avec le parser approprié."""
        infobox = self.extract_first_infobox(wikitext)
        
        if not infobox:
            return None
        
        template_name = infobox.pop('_template_name', '').lower().strip()
        entity_type = self.TEMPLATE_TYPE_MAPPING.get(template_name, 'Thing')
        
        if entity_type == 'Thing' and 'infobox' in template_name:
            type_part = template_name.replace('infobox', '').strip()
            if type_part:
                entity_type = type_part.title().replace(' ', '')
        
        if entity_type in self._specialized_parsers:
            parser = self._specialized_parsers[entity_type]
            method_name = f"parse_{entity_type.lower()}"
            if hasattr(parser, method_name):
                result = getattr(parser, method_name)(wikitext, page_title)
                if result:
                    return result
        
        entity = {
            '_type': entity_type,
            '_template': template_name,
        }
        
        for field, value in infobox.items():
            field_lower = field.lower().strip()
            field_type = self.COMMON_FIELD_TYPES.get(field_lower, 'string')
            entity[field_lower] = _parse_field(value, field_type, self)
        
        if 'name' not in entity and page_title:
            entity['name'] = page_title
        
        return entity
    
    def _parse_field(self, value: str, field_type: str) -> Any:
        return _parse_field(value, field_type, self)
    
    def detect_entity_type(self, template_name: str) -> str:
        """Détecte le type d'entité à partir du nom du template."""
        template_lower = template_name.lower().strip()
        return self.TEMPLATE_TYPE_MAPPING.get(template_lower, 'Thing')


class UnifiedInfoboxParser(GenericInfoboxParser):
    """Parser unifié combinant tous les parsers spécialisés."""
    
    def parse(self, wikitext: str, page_title: str = None) -> Optional[Dict[str, Any]]:
        return self.parse_any(wikitext, page_title)
    
    def parse_with_type(self, wikitext: str, entity_type: str, page_title: str = None) -> Optional[Dict[str, Any]]:
        """Parse avec un type d'entité spécifié."""
        entity_type_title = entity_type.title()
        
        if entity_type_title in self._specialized_parsers:
            parser = self._specialized_parsers[entity_type_title]
            method_name = f"parse_{entity_type.lower()}"
            if hasattr(parser, method_name):
                return getattr(parser, method_name)(wikitext, page_title)
        
        return self.parse_any(wikitext, page_title)


def get_parser_for_template(template_name: str) -> Optional[WikitextParser]:
    """Retourne le parser approprié pour un template."""
    template_lower = template_name.lower().strip()
    
    parsers_map = {
        'infobox character': CharacterInfoboxParser(),
        'men infobox': CharacterInfoboxParser(),
        'elves infobox': CharacterInfoboxParser(),
        'battle': BattleInfoboxParser(),
        'book': BookInfoboxParser(),
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
                         PersonInfoboxParser, RaceInfoboxParser, WarInfoboxParser, BookInfoboxParser]:
        templates.extend(parser_class.TEMPLATE_NAMES)
    return templates


__all__ = [
    'WikitextParser',
    'GenericInfoboxParser',
    'CharacterInfoboxParser',
    'BattleInfoboxParser',
    'CampaignInfoboxParser',
    'KingdomInfoboxParser',
    'LocationInfoboxParser',
    'BookInfoboxParser',
    'ObjectInfoboxParser',
    'PersonInfoboxParser',
    'RaceInfoboxParser',
    'WarInfoboxParser',
    'UnifiedInfoboxParser',
    'get_parser_for_template',
    'get_all_supported_templates',
]