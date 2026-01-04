"""
Module pour les labels multilingues - Étape 11
Ajoute des triplets rdfs:label avec les tags de langue appropriés
"""

import re
from typing import Dict, List, Set, Tuple, Any
from urllib.parse import quote
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD


# Namespaces
TOLKIEN = Namespace("https://tolkiengateway.net/wiki/")
TOLKIEN_PROP = Namespace("https://tolkiengateway.net/wiki/Property:")
SCHEMA = Namespace("http://schema.org/")


# =============================================================================
# MAPPING MULTILINGUE MANUEL POUR LES ENTITÉS PRINCIPALES
# Sources: Traductions officielles des livres, wikis multilingues
# =============================================================================

MULTILINGUAL_LABELS = {
    # =========================================================================
    # PERSONNAGES PRINCIPAUX
    # =========================================================================
    'Gandalf': {
        'en': 'Gandalf',
        'fr': 'Gandalf',
        'de': 'Gandalf',
        'es': 'Gandalf',
        'it': 'Gandalf',
        'pt': 'Gandalf',
        'ru': 'Гэндальф',
        'pl': 'Gandalf',
        'ja': 'ガンダルフ',
        'zh': '甘道夫',
        'nl': 'Gandalf',
        'fi': 'Gandalf',
    },
    'Frodo Baggins': {
        'en': 'Frodo Baggins',
        'fr': 'Frodon Sacquet',
        'de': 'Frodo Beutlin',
        'es': 'Frodo Bolsón',
        'it': 'Frodo Baggins',
        'pt': 'Frodo Bolseiro',
        'ru': 'Фродо Бэггинс',
        'pl': 'Frodo Baggins',
        'ja': 'フロド・バギンズ',
        'zh': '佛羅多·乘綢',
        'nl': 'Frodo Balings',
    },
    'Bilbo Baggins': {
        'en': 'Bilbo Baggins',
        'fr': 'Bilbon Sacquet',
        'de': 'Bilbo Beutlin',
        'es': 'Bilbo Bolsón',
        'it': 'Bilbo Baggins',
        'pt': 'Bilbo Bolseiro',
        'ru': 'Бильбо Бэггинс',
        'pl': 'Bilbo Baggins',
        'ja': 'ビルボ・バギンズ',
        'zh': '比爾博·巴金斯',
        'nl': 'Bilbo Balings',
    },
    'Samwise Gamgee': {
        'en': 'Samwise Gamgee',
        'fr': 'Samsagace Gamegie',
        'de': 'Samweis Gamdschie',
        'es': 'Samsagaz Gamyi',
        'it': 'Samwise Gamgee',
        'pt': 'Samwise Gamgee',
        'ru': 'Сэмуайз Гэмджи',
        'pl': 'Samwise Gamgee',
        'ja': 'サムワイズ・ギャムジー',
    },
    'Aragorn': {
        'en': 'Aragorn',
        'fr': 'Aragorn',
        'de': 'Aragorn',
        'es': 'Aragorn',
        'it': 'Aragorn',
        'pt': 'Aragorn',
        'ru': 'Арагорн',
        'pl': 'Aragorn',
        'ja': 'アラゴルン',
        'zh': '亞拉岡',
    },
    'Legolas': {
        'en': 'Legolas',
        'fr': 'Legolas',
        'de': 'Legolas',
        'es': 'Legolas',
        'it': 'Legolas',
        'pt': 'Legolas',
        'ru': 'Леголас',
        'pl': 'Legolas',
        'ja': 'レゴラス',
        'zh': '勒苟拉斯',
    },
    'Gimli': {
        'en': 'Gimli',
        'fr': 'Gimli',
        'de': 'Gimli',
        'es': 'Gimli',
        'it': 'Gimli',
        'pt': 'Gimli',
        'ru': 'Гимли',
        'pl': 'Gimli',
        'ja': 'ギムリ',
        'zh': '金靂',
    },
    'Boromir': {
        'en': 'Boromir',
        'fr': 'Boromir',
        'de': 'Boromir',
        'es': 'Boromir',
        'it': 'Boromir',
        'pt': 'Boromir',
        'ru': 'Боромир',
        'pl': 'Boromir',
        'ja': 'ボロミア',
    },
    'Meriadoc Brandybuck': {
        'en': 'Meriadoc Brandybuck',
        'fr': 'Meriadoc Brandebouc',
        'de': 'Meriadoc Brandybock',
        'es': 'Meriadoc Brandigamo',
        'it': 'Meriadoc Brandibuck',
        'ru': 'Мериадок Брендибак',
    },
    'Peregrin Took': {
        'en': 'Peregrin Took',
        'fr': 'Peregrïn Touque',
        'de': 'Peregrin Tuk',
        'es': 'Peregrin Tuk',
        'it': 'Peregrino Tuc',
        'ru': 'Перегрин Тук',
    },
    'Elrond': {
        'en': 'Elrond',
        'fr': 'Elrond',
        'de': 'Elrond',
        'es': 'Elrond',
        'it': 'Elrond',
        'pt': 'Elrond',
        'ru': 'Элронд',
        'pl': 'Elrond',
        'ja': 'エルロンド',
        'zh': '愛隆',
    },
    'Galadriel': {
        'en': 'Galadriel',
        'fr': 'Galadriel',
        'de': 'Galadriel',
        'es': 'Galadriel',
        'it': 'Galadriel',
        'pt': 'Galadriel',
        'ru': 'Галадриэль',
        'pl': 'Galadriel',
        'ja': 'ガラドリエル',
        'zh': '凱蘭崔爾',
    },
    'Saruman': {
        'en': 'Saruman',
        'fr': 'Saroumane',
        'de': 'Saruman',
        'es': 'Saruman',
        'it': 'Saruman',
        'pt': 'Saruman',
        'ru': 'Саруман',
        'pl': 'Saruman',
        'ja': 'サルマン',
        'zh': '薩魯曼',
    },
    'Sauron': {
        'en': 'Sauron',
        'fr': 'Sauron',
        'de': 'Sauron',
        'es': 'Sauron',
        'it': 'Sauron',
        'pt': 'Sauron',
        'ru': 'Саурон',
        'pl': 'Sauron',
        'ja': 'サウロン',
        'zh': '索倫',
    },
    'Gollum': {
        'en': 'Gollum',
        'fr': 'Gollum',
        'de': 'Gollum',
        'es': 'Gollum',
        'it': 'Gollum',
        'pt': 'Gollum',
        'ru': 'Голлум',
        'pl': 'Gollum',
        'ja': 'ゴラム',
        'zh': '咕嚕',
    },
    'Théoden': {
        'en': 'Théoden',
        'fr': 'Théoden',
        'de': 'Théoden',
        'es': 'Théoden',
        'it': 'Théoden',
        'ru': 'Теоден',
        'ja': 'セオデン',
    },
    'Éowyn': {
        'en': 'Éowyn',
        'fr': 'Éowyn',
        'de': 'Éowyn',
        'es': 'Éowyn',
        'it': 'Éowyn',
        'ru': 'Эовин',
        'ja': 'エオウィン',
    },
    'Éomer': {
        'en': 'Éomer',
        'fr': 'Éomer',
        'de': 'Éomer',
        'es': 'Éomer',
        'it': 'Éomer',
        'ru': 'Эомер',
    },
    'Faramir': {
        'en': 'Faramir',
        'fr': 'Faramir',
        'de': 'Faramir',
        'es': 'Faramir',
        'it': 'Faramir',
        'ru': 'Фарамир',
        'ja': 'ファラミア',
    },
    'Denethor': {
        'en': 'Denethor II',
        'fr': 'Denethor II',
        'de': 'Denethor II.',
        'es': 'Denethor II',
        'ru': 'Денетор II',
    },
    'Arwen': {
        'en': 'Arwen',
        'fr': 'Arwen',
        'de': 'Arwen',
        'es': 'Arwen',
        'it': 'Arwen',
        'ru': 'Арвен',
        'ja': 'アルウェン',
        'zh': '亞玟',
    },
    'Celeborn': {
        'en': 'Celeborn',
        'fr': 'Celeborn',
        'de': 'Celeborn',
        'es': 'Celeborn',
        'ru': 'Келеборн',
    },
    'Thranduil': {
        'en': 'Thranduil',
        'fr': 'Thranduil',
        'de': 'Thranduil',
        'es': 'Thranduil',
        'ru': 'Трандуил',
        'ja': 'スランドゥイル',
    },
    'Thorin': {
        'en': 'Thorin Oakenshield',
        'fr': 'Thorin Écu-de-Chêne',
        'de': 'Thorin Eichenschild',
        'es': 'Thorin Escudo de Roble',
        'it': 'Thorin Scudodiquercia',
        'ru': 'Торин Дубощит',
        'ja': 'トーリン・オーケンシールド',
    },
    'Smaug': {
        'en': 'Smaug',
        'fr': 'Smaug',
        'de': 'Smaug',
        'es': 'Smaug',
        'it': 'Smaug',
        'ru': 'Смауг',
        'ja': 'スマウグ',
        'zh': '史矛革',
    },
    'Morgoth': {
        'en': 'Morgoth',
        'fr': 'Morgoth',
        'de': 'Morgoth',
        'es': 'Morgoth',
        'it': 'Morgoth',
        'ru': 'Моргот',
        'ja': 'モルゴス',
    },
    'Fëanor': {
        'en': 'Fëanor',
        'fr': 'Fëanor',
        'de': 'Fëanor',
        'es': 'Fëanor',
        'ru': 'Феанор',
    },
    'Fingolfin': {
        'en': 'Fingolfin',
        'fr': 'Fingolfin',
        'de': 'Fingolfin',
        'es': 'Fingolfin',
        'ru': 'Финголфин',
    },
    'Beren': {
        'en': 'Beren',
        'fr': 'Beren',
        'de': 'Beren',
        'es': 'Beren',
        'ru': 'Берен',
    },
    'Lúthien': {
        'en': 'Lúthien',
        'fr': 'Lúthien',
        'de': 'Lúthien',
        'es': 'Lúthien',
        'ru': 'Лютиэн',
    },
    'Túrin Turambar': {
        'en': 'Túrin Turambar',
        'fr': 'Túrin Turambar',
        'de': 'Túrin Turambar',
        'es': 'Túrin Turambar',
        'ru': 'Турин Турамбар',
    },
    
    # =========================================================================
    # LIEUX PRINCIPAUX
    # =========================================================================
    'Rivendell': {
        'en': 'Rivendell',
        'fr': 'Fondcombe',
        'de': 'Bruchtal',
        'es': 'Rivendel',
        'it': 'Gran Burrone',
        'pt': 'Valfenda',
        'ru': 'Ривенделл',
        'pl': 'Rivendell',
        'ja': '裂け谷',
        'zh': '瑞文戴爾',
    },
    'Mordor': {
        'en': 'Mordor',
        'fr': 'Mordor',
        'de': 'Mordor',
        'es': 'Mordor',
        'it': 'Mordor',
        'pt': 'Mordor',
        'ru': 'Мордор',
        'ja': 'モルドール',
        'zh': '魔多',
    },
    'Gondor': {
        'en': 'Gondor',
        'fr': 'Gondor',
        'de': 'Gondor',
        'es': 'Gondor',
        'it': 'Gondor',
        'ru': 'Гондор',
        'ja': 'ゴンドール',
        'zh': '剛鐸',
    },
    'Rohan': {
        'en': 'Rohan',
        'fr': 'Rohan',
        'de': 'Rohan',
        'es': 'Rohan',
        'it': 'Rohan',
        'ru': 'Рохан',
        'ja': 'ローハン',
        'zh': '洛汗',
    },
    'The Shire': {
        'en': 'The Shire',
        'fr': 'La Comté',
        'de': 'Das Auenland',
        'es': 'La Comarca',
        'it': 'La Contea',
        'pt': 'O Condado',
        'ru': 'Шир',
        'ja': 'ホビット庄',
        'zh': '夏爾',
    },
    'Minas Tirith': {
        'en': 'Minas Tirith',
        'fr': 'Minas Tirith',
        'de': 'Minas Tirith',
        'es': 'Minas Tirith',
        'it': 'Minas Tirith',
        'ru': 'Минас Тирит',
        'ja': 'ミナス・ティリス',
        'zh': '米那斯提力斯',
    },
    'Isengard': {
        'en': 'Isengard',
        'fr': 'Isengard',
        'de': 'Isengart',
        'es': 'Isengard',
        'it': 'Isengard',
        'ru': 'Изенгард',
        'ja': 'アイゼンガルド',
    },
    'Lothlórien': {
        'en': 'Lothlórien',
        'fr': 'Lothlórien',
        'de': 'Lothlórien',
        'es': 'Lothlórien',
        'it': 'Lothlórien',
        'ru': 'Лотлориэн',
        'ja': 'ロスロリアン',
        'zh': '羅斯洛立安',
    },
    'Moria': {
        'en': 'Moria',
        'fr': 'Moria',
        'de': 'Moria',
        'es': 'Moria',
        'it': 'Moria',
        'ru': 'Мория',
        'ja': 'モリア',
        'zh': '摩瑞亞',
    },
    'Erebor': {
        'en': 'Erebor',
        'fr': 'Erebor',
        'de': 'Erebor',
        'es': 'Erebor',
        'it': 'Erebor',
        'ru': 'Эребор',
        'ja': 'エレボール',
    },
    'Valinor': {
        'en': 'Valinor',
        'fr': 'Valinor',
        'de': 'Valinor',
        'es': 'Valinor',
        'it': 'Valinor',
        'ru': 'Валинор',
        'ja': 'ヴァリノール',
    },
    'Númenor': {
        'en': 'Númenor',
        'fr': 'Númenor',
        'de': 'Númenor',
        'es': 'Númenor',
        'it': 'Númenor',
        'ru': 'Нуменор',
        'ja': 'ヌーメノール',
    },
    'Middle-earth': {
        'en': 'Middle-earth',
        'fr': 'Terre du Milieu',
        'de': 'Mittelerde',
        'es': 'Tierra Media',
        'it': 'Terra di Mezzo',
        'pt': 'Terra-média',
        'ru': 'Средиземье',
        'ja': '中つ国',
        'zh': '中土大陸',
    },
    'Helm\'s Deep': {
        'en': 'Helm\'s Deep',
        'fr': 'Gouffre de Helm',
        'de': 'Helms Klamm',
        'es': 'Abismo de Helm',
        'it': 'Fosso di Helm',
        'ru': 'Хельмова Падь',
    },
    'Bag End': {
        'en': 'Bag End',
        'fr': 'Cul-de-Sac',
        'de': 'Beutelsend',
        'es': 'Bolsón Cerrado',
        'it': 'Casa Baggins',
        'ru': 'Бэг Энд',
    },
    
    # =========================================================================
    # OBJETS IMPORTANTS
    # =========================================================================
    'The One Ring': {
        'en': 'The One Ring',
        'fr': 'L\'Anneau Unique',
        'de': 'Der Eine Ring',
        'es': 'El Anillo Único',
        'it': 'L\'Unico Anello',
        'pt': 'O Um Anel',
        'ru': 'Кольцо Всевластия',
        'ja': '一つの指輪',
        'zh': '至尊魔戒',
    },
    'Sting': {
        'en': 'Sting',
        'fr': 'Dard',
        'de': 'Stich',
        'es': 'Dardo',
        'it': 'Pungolo',
        'ru': 'Жало',
    },
    'Glamdring': {
        'en': 'Glamdring',
        'fr': 'Glamdring',
        'de': 'Glamdring',
        'es': 'Glamdring',
        'ru': 'Гламдринг',
    },
    'Andúril': {
        'en': 'Andúril',
        'fr': 'Andúril',
        'de': 'Andúril',
        'es': 'Andúril',
        'ru': 'Андурил',
    },
    
    # =========================================================================
    # RACES/PEUPLES
    # =========================================================================
    'Elves': {
        'en': 'Elves',
        'fr': 'Elfes',
        'de': 'Elben',
        'es': 'Elfos',
        'it': 'Elfi',
        'pt': 'Elfos',
        'ru': 'Эльфы',
        'ja': 'エルフ',
        'zh': '精靈',
    },
    'Dwarves': {
        'en': 'Dwarves',
        'fr': 'Nains',
        'de': 'Zwerge',
        'es': 'Enanos',
        'it': 'Nani',
        'pt': 'Anões',
        'ru': 'Гномы',
        'ja': 'ドワーフ',
        'zh': '矮人',
    },
    'Hobbits': {
        'en': 'Hobbits',
        'fr': 'Hobbits',
        'de': 'Hobbits',
        'es': 'Hobbits',
        'it': 'Hobbit',
        'ru': 'Хоббиты',
        'ja': 'ホビット',
        'zh': '哈比人',
    },
    'Orcs': {
        'en': 'Orcs',
        'fr': 'Orques',
        'de': 'Orks',
        'es': 'Orcos',
        'it': 'Orchi',
        'ru': 'Орки',
        'ja': 'オーク',
        'zh': '半獸人',
    },
    'Ents': {
        'en': 'Ents',
        'fr': 'Ents',
        'de': 'Ents',
        'es': 'Ents',
        'it': 'Ent',
        'ru': 'Энты',
        'ja': 'エント',
    },
    'Men': {
        'en': 'Men',
        'fr': 'Hommes',
        'de': 'Menschen',
        'es': 'Hombres',
        'it': 'Uomini',
        'ru': 'Люди',
        'ja': '人間',
    },
    'Maiar': {
        'en': 'Maiar',
        'fr': 'Maiar',
        'de': 'Maiar',
        'es': 'Maiar',
        'ru': 'Майар',
    },
    'Valar': {
        'en': 'Valar',
        'fr': 'Valar',
        'de': 'Valar',
        'es': 'Valar',
        'ru': 'Валар',
    },
}


class MultilingualLabelsGenerator:
    """
    Génère des labels multilingues pour les entités du Knowledge Graph.
    """
    
    # Langues supportées (codes ISO 639-1)
    SUPPORTED_LANGUAGES = ['en', 'fr', 'de', 'es', 'it', 'pt', 'ru', 'pl', 'ja', 'zh', 'nl', 'fi']
    
    def __init__(self):
        self.labels_added = 0
        self.entities_enriched = set()
    
    def add_labels_to_graph(self, graph: Graph, entity_names: Set[str] = None) -> int:
        """
        Ajoute les labels multilingues au graphe RDF.
        
        Args:
            graph: Graphe RDF à enrichir
            entity_names: Noms des entités à traiter (optionnel, toutes si None)
            
        Returns:
            Nombre de triplets ajoutés
        """
        count = 0
        
        # Utiliser le mapping prédéfini
        for entity_name, labels in MULTILINGUAL_LABELS.items():
            # Vérifier si l'entité est dans la liste (ou si on traite tout)
            if entity_names is not None:
                # Chercher une correspondance (case-insensitive)
                found = False
                for wiki_name in entity_names:
                    if entity_name.lower() in wiki_name.lower() or wiki_name.lower() in entity_name.lower():
                        found = True
                        break
                if not found:
                    continue
            
            # URI de l'entité
            uri = TOLKIEN[quote(entity_name.replace(" ", "_"), safe="")]
            
            # Ajouter les labels pour chaque langue
            for lang, label in labels.items():
                if label:
                    graph.add((uri, RDFS.label, Literal(label, lang=lang)))
                    count += 1
            
            self.entities_enriched.add(entity_name)
        
        self.labels_added = count
        return count
    
    def add_labels_from_meccg(self, graph: Graph, meccg_cards: List[Dict]) -> int:
        """
        Ajoute les labels multilingues extraits des cartes MECCG.
        
        Les cartes MECCG ont des noms en plusieurs langues (en, es, fr, de, it, nl, fi, ja).
        
        Args:
            graph: Graphe RDF à enrichir
            meccg_cards: Liste des cartes MECCG parsées
            
        Returns:
            Nombre de triplets ajoutés
        """
        count = 0
        
        for card in meccg_cards:
            card_type = card.get('type', '')
            
            # Traiter seulement les personnages et lieux
            if card_type not in ('Character', 'Site', 'Region'):
                continue
            
            names = card.get('name', {})
            en_name = names.get('en', '')
            
            if not en_name:
                continue
            
            # URI basée sur le nom anglais
            uri = TOLKIEN[quote(en_name.replace(" ", "_"), safe="")]
            
            # Ajouter les labels pour chaque langue disponible
            for lang, name in names.items():
                if name and lang in self.SUPPORTED_LANGUAGES:
                    # Vérifier si ce label existe déjà
                    existing = list(graph.triples((uri, RDFS.label, Literal(name, lang=lang))))
                    if not existing:
                        graph.add((uri, RDFS.label, Literal(name, lang=lang)))
                        count += 1
            
            if en_name not in self.entities_enriched:
                self.entities_enriched.add(en_name)
        
        self.labels_added += count
        return count
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques."""
        return {
            'labels_added': self.labels_added,
            'entities_enriched': len(self.entities_enriched),
            'manual_mappings': len(MULTILINGUAL_LABELS),
            'supported_languages': self.SUPPORTED_LANGUAGES,
        }


def extract_labels_from_meccg_cards(cards: List[Dict]) -> Dict[str, Dict[str, str]]:
    """
    Extrait les labels multilingues des cartes MECCG.
    
    Args:
        cards: Liste des cartes MECCG
        
    Returns:
        Dict {entity_name: {lang: label}}
    """
    labels = {}
    
    for card in cards:
        if card.get('type') not in ('Character', 'Site', 'Region'):
            continue
        
        names = card.get('name', {})
        en_name = names.get('en', '')
        
        if not en_name:
            continue
        
        if en_name not in labels:
            labels[en_name] = {}
        
        for lang, name in names.items():
            if name and len(lang) == 2:  # Codes ISO 639-1
                labels[en_name][lang] = name
    
    return labels


def print_label_statistics(graph: Graph):
    """Affiche les statistiques des labels dans le graphe."""
    print("\n📊 Statistiques des labels multilingues:")
    
    # Compter les labels par langue
    lang_counts = {}
    
    for s, p, o in graph.triples((None, RDFS.label, None)):
        if isinstance(o, Literal) and o.language:
            lang = o.language
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
    
    print(f"\n   Par langue:")
    for lang, count in sorted(lang_counts.items(), key=lambda x: -x[1]):
        lang_name = {
            'en': 'Anglais', 'fr': 'Français', 'de': 'Allemand',
            'es': 'Espagnol', 'it': 'Italien', 'pt': 'Portugais',
            'ru': 'Russe', 'pl': 'Polonais', 'ja': 'Japonais',
            'zh': 'Chinois', 'nl': 'Néerlandais', 'fi': 'Finnois',
        }.get(lang, lang)
        print(f"     {lang} ({lang_name}): {count}")
    
    total = sum(lang_counts.values())
    print(f"\n   Total: {total} labels multilingues")


def demo_multilingual():
    """Démo des labels multilingues."""
    print("\n" + "=" * 60)
    print(" DÉMO: Labels Multilingues")
    print("=" * 60)
    
    # Créer un graphe de test
    graph = Graph()
    graph.bind("tolkien", TOLKIEN)
    graph.bind("rdfs", RDFS)
    
    # Ajouter les labels
    generator = MultilingualLabelsGenerator()
    count = generator.add_labels_to_graph(graph)
    
    print(f"\n✓ {count} labels ajoutés pour {len(generator.entities_enriched)} entités")
    
    # Statistiques
    print_label_statistics(graph)
    
    # Exemples
    print("\n📝 Exemples de labels multilingues:\n")
    
    examples = ['Gandalf', 'Frodo Baggins', 'Rivendell', 'The One Ring', 'Elves']
    
    for name in examples:
        uri = TOLKIEN[quote(name.replace(" ", "_"), safe="")]
        labels = list(graph.triples((uri, RDFS.label, None)))
        
        print(f"   {name}:")
        for s, p, o in sorted(labels, key=lambda x: str(x[2].language) if x[2].language else 'zz'):
            lang = o.language or 'en'
            print(f"     @{lang}: {o}")
        print()
    
    return graph


if __name__ == "__main__":
    demo_multilingual()
