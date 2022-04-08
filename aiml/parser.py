"""
aiml/aiml/parser.py
c Yaakov Schectman 2022
"""

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import (
    dataclass,
    field
)
from io import IOBase
from os import path
from typing import (
    Callable,
    ClassVar,
    Tuple,
    List,
    Dict,
    Optional,
    Set
)

from .pattern import (
    PatternTree,
    PatternToken,
    PatternTokens,
    WildcardType
)
from .translatable import *
from .translatable import _stringops
from .config import BrainConfig

@dataclass
class AimlParser:
    """A parser to convert AIML XML data into a full pattern tree"""
    config: BrainConfig
    topic_pattern: Optional[List[PatternToken]] = None
    sub_names: Set[str] = field(init = False, default_factory=set)
    
    def __post_init__(self):
        if self.config is not None and self.config.sub_files:
            self.sub_names = set(map(\
                lambda x: path.splitext(path.basename(x))[0].lower(),
                self.config.sub_files))
    
    
    #==========Public facing methods to start parsing==========
    
    def parse(self, source: Union[IOBase, str]) -> PatternTree:
        # return self.parse_aiml(ET.parse(source))
        if isinstance(source, IOBase):
            src: str = source.read()
        else:
            with open(source) as file:
                src = file.read()
        return self.parse_string(src)
    
    def parse_string(self, source: str) -> PatternTree:
        """Parse a provided string"""
        preproc: str = re.sub('[\r\n\t]+', '', source)
        preproc = re.sub('\\s+', ' ', preproc)
        source\
            .replace('\n', '')\
            .replace('\\n', '\n')\
            .replace('\t', '')\
            .replace('\\t', '\t')
        root: ET.Element = ET.fromstring(preproc)
        return self.parse_aiml(root)
    
    def parse_aiml(self, elem: ET.Element) -> PatternTree:
        """Parse the root <aiml>"""
        root: PatternTree = PatternTree()
        for child in elem:
            if child.tag.lower() == 'category':
                root.merge(self.parse_category(child))
            elif child.tag.lower() == 'topic':
                root.merge(self.parse_topic(child))
            else:
                raise ValueError(f'Unexpected tag {child.tag} in <aiml>')
        return root
    
    def parse_category(self, elem: ET.Element) -> PatternTree:
        """Parse a <category>, either in <aiml> or <topic>"""
        pattern: Optional[Tuple[PatternTree, PatternTree]] = None
        that: Optional[Tuple[PatternTree, PatternTree]] = None
        topic: Optional[Tuple[PatternTree, PatternTree]] = None
        template: Optional[Translatable] = None
        for child in elem:
            if child.tag.lower() == 'pattern':
                pattern = self.parse_pattern(child)
            elif child.tag.lower() == 'that':
                that = self.parse_pattern(child)
            elif child.tag.lower() == 'topic':
                if self.topic_pattern is not None:
                    raise ValueError('Cannot declare category-level <topic> under top-level <topic>')
                topic = self.parse_pattern(child)
            elif child.tag.lower() == 'template':
                template = self.parse_template(child)
            else:
                raise ValueError(f'Unexpected tag {child.tag} in <category>')
        if pattern is None or template is None:
            raise ValueError('Missing <pattern> or <template> in <category>')
        if self.topic_pattern is not None:
            topic_root: PatternTree = PatternTree()
            topic_leaf: PatternTree = topic_root
            for tok in self.topic_pattern:
                topic_leaf.index[tok] = PatternTree()
                topic_leaf = topic_leaf.index[tok]
            topic = (topic_root, topic_leaf)
        root: PatternTree = pattern[0]
        leaf: PatternTree = pattern[1]
        if that is not None:
            leaf.index[PatternTokens.DELIM_THAT] = that[0]
            leaf = that[1]
        if topic is not None:
            leaf.index[PatternTokens.DELIM_TOPIC] = topic[0]
            leaf = topic[1]
        leaf.terminal = template
        return root
    
    #==========For the most part, these methods are only called internally==========
    #==========Methods for parsing XML elements within an IML file==================
    
    def parse_topic(self, elem: ET.Element) -> PatternTree:
        """Parses all categories in a topic into a single PatternTree for that topic"""
        if 'name' not in elem.attrib:
            raise ValueError('Top-level <topic> tag with no name attribute')
        self.topic_pattern = AimlParser.literal_to_pattern(elem.get('name'))
        root: PatternTree = PatternTree()
        for child in elem:
            if child.tag.lower() != 'category':
                raise ValueError(f'Unexpected tag {child.tag} in top-level <topic>')
            branch: PatternTree = self.parse_category(child)
            root.merge(branch)
        self.topic_pattern = None
        return root
    
    def parse_pattern(self, pattern_elem: ET.Element) -> Tuple[PatternTree, PatternTree]:
        """Parse a <pattern> element into a PatternTree
        Returns (the root of the tree, the leaf that matches the pattern)"""
        root: PatternTree = PatternTree()
        leaf: PatternTree = root
        if pattern_elem.text:
            toks: List[PatternToken] = AimlParser.literal_to_pattern(pattern_elem.text)
            for tok in toks:
                leaf.index[tok] = PatternTree()
                leaf = leaf.index[tok]
        for i, child in enumerate(pattern_elem):
            toks: List[PatternToken] = self.parse_pattern_child(child)
            for tok in toks:
                leaf.index[tok] = PatternTree()
                leaf = leaf.index[tok]
            if child.tail:
                toks = AimlParser.literal_to_pattern(child.tail)
                for tok in toks:
                    leaf.index[tok] = PatternTree()
                    leaf = leaf.index[tok]
        return (root, leaf)
    
    def parse_pattern_child(self, elem: ET.Element) -> List[PatternToken]:
        """Parses a <set>, <get>, or <bot> tag within a <pattern>"""
        if elem.tag.lower() == 'set':
            name: str = AimlParser.get_string_by_key(elem, 'name')
            return [PatternTokens.SET_MAP, PatternToken(name)]
        elif elem.tag.lower() == 'get':
            name: str = AimlParser.get_string_by_key(elem, 'name', False)
            if name is None:
                name = AimlParser.get_string_by_key(elem, 'var')
            return [PatternTokens.GET_VAR, PatternToken(name)]
        elif elem.tag.lower() == 'bot':
            name: str = AimlParser.get_string_by_key(elem, 'name', False)
            if name is None:
                name = AimlParser.get_string_by_key(elem, 'var')
            return [PatternTokens.BOT_VAR, PatternToken(name)]
        raise ValueError(f'Element with tag {elem.tag} not expected inside <pattern>, <that>, or <topic>')
        
    def parse_template(self, elem: ET.Element) -> Translatable:
        """Parse any element that has an evaluatable content, namely <template>"""
        return self._parse_template_expr(elem)
    
    def _parse_template_expr(self, elem: ET.Element, ignore: Optional[Set[str]] = None) -> Translatable:
        sequence: List[Translatable] = []
        if elem.text:
            sequence.append(TranslatableWord(elem.text))
        for child in elem:
            if ignore is None or child.tag.lower() not in ignore:
                if child.tag.lower() in self._template_funcs:
                    sequence.append(self._template_funcs[child.tag.lower()](self, child))
                elif child.tag.lower() in _stringops:
                    sequence.append(TranslatableStringop(self.parse_template(child), child.tag.lower()))
                elif child.tag.lower() in self.sub_names:
                    sequence.append(TranslatableSubst(child.tag.lower(), self.parse_template(child)))
                elif child.tag.lower() in self._repeats:
                    sequence.append(self.parse_repeat(child))
                elif child.tag.lower() in self._stars:
                    sequence.append(self.parse_star(child))
            if child.tail:
                sequence.append(TranslatableWord(child.tail))
        if len(sequence) == 1:
            return sequence[0]
        elif len(sequence) == 0:
            return TranslatableNull()
        return TranslatableIterable(sequence)
    
    def parse_condition(self, elem: ET.Element) -> TranslatableCondition:
        """Parse <condition> with its included <li>"""
        def_name: Optional[Translatable] = self.get_translatable_by_key(elem, 'name', False)
        def_val: Optional[Translatable] = self.get_translatable_by_key(elem, 'value', False)
        mapping: List[Tuple[Translatable, Translatable, Translatable, bool]] = []
        if def_name and def_val:
            inner: Translatable = self._parse_template_expr(elem, {'name', 'value', 'loop'})
            mapping.append((def_name, def_val, inner, AimlParser.has_child(elem, False)))
            return TranslatableCondition(mapping)
        default: Optional[Tuple[Translatable, bool]] = None
        for child in elem:
            if child.tag.lower() != 'li':
                if child.tag.lower() not in {'name'}:
                    raise ValueError(f'Unexpected tag {child.tag} in <condition>')
                continue
            match_val: Optional[Translatable] = self.get_translatable_by_key(child, 'value', False)
            inner: Translatable = self._parse_template_expr(child, {'name', 'value', 'loop'})
            if match_val is None:
                default = (inner, AimlParser.has_child(child, 'loop'))
            else:
                match_name: Optional[Translatable] = self.get_translatable_by_key(child, 'name', False)
                if not match_name:
                    match_name = def_name
                if not match_name:
                    raise ValueError("No name for predicate specified inside <condition>'s <li>")
                mapping.append((match_name, match_val, inner, AimlParser.has_child(child, 'loop')))
        return TranslatableCondition(mapping, default)
    
    def parse_random(self, elem: ET.Element) -> TranslatableRandom:
        """Parse <random>"""
        choices: List[Translatable] = []
        for child in elem:
            if child.tag.lower() != 'li':
                raise ValueError(f'Unexepcted tag {child.tag} in <random>')
            choice: Translatable = self.parse_template(child)
            choices.append(choice)
        return TranslatableRandom(choices)
    
    def parse_set(self, elem: ET.Element) -> TranslatableSet:
        """Parse a <set> tag that assigns a predicate"""
        name: Optional[Translatable] = self.get_translatable_by_key(elem, 'name', False)
        if name is None:
            name = self.get_translatable_by_key(elem, 'var')
        expr: Translatable = self._parse_template_expr(elem, {'name', 'value'})
        return TranslatableSet(name, expr)
    
    def parse_get(self, elem: ET.Element) -> TranslatableGet:
        """Parse <get>"""
        name: Translatable = self.get_translatable_by_key(elem, 'name', False)
        if name is None:
            name = self.get_translatable_by_key(elem, 'var')
        return TranslatableGet(name)
    
    def parse_think(self, elem: ET.Element) -> TranslatableThink:
        """Parse <think>"""
        return TranslatableThink(self.parse_template(elem))
    
    def parse_bot(self, elem: ET.Element) -> TranslatableBot:
        """Parse <bot>"""
        name: Translatable = self.get_translatable_by_key(elem, 'name', False)
        if name is None:
            name = self.get_translatable_by_key(elem, 'var')
        return TranslatableBot(name)
    
    def parse_map(self, elem: ET.Element) -> TranslatableMap:
        """Parse <map>"""
        name: Translatable = self.get_translatable_by_key(elem, 'name')
        expr: Translatable = self._parse_template_expr(elem, {'name'})
        return TranslatableMap(name, expr)
        
    def parse_learn(self, elem: ET.Element) -> TranslatableLearn:
        """Parse <learn>"""
        if len(elem) != 1 or elem[0].tag.lower() != 'category':
            raise ValueError('<learn> tag must have exactly one child <condition> tag')
        pattern, template, that, topic = self.parse_learned_category(elem[0])
        return TranslatableLearn(pattern, template, that, topic)
    
    def parse_star(self, elem: ET.Element) -> TranslatableStar:
        """Parse <star>, <thatstar>, and <topicstar>"""
        index: int = int(AimlParser.get_string_by_key(elem, 'index', False) or 1)
        return TranslatableStar(index, elem.tag.lower())
    
    def parse_repeat(self, elem: ET.Element) -> TranslatableRepeat:
        """Parse <input>, <response>, and <request>"""
        index: int = int(AimlParser.get_string_by_key(elem, 'index', False) or 1)
        return TranslatableRepeat(index = index, repeat_type = elem.tag.lower())
    
    def parse_that_template(self, elem: ET.Element) -> TranslatableThat:
        """Parse <that> inside a template"""
        a, b = map(int, (AimlParser.get_string_by_key(elem, 'index', False) or '1,1').split(','))
        return TranslatableThat(a, b)
    
    def parse_srai(self, elem: ET.Element) -> TranslatableSrai:
        """Parse <srai> or <sr />"""
        if not elem.text and len(elem) == 0:
            return TranslatableSrai(TranslatableStar(1, 'star'))
        inner: Translatable = self.parse_template(elem)
        return TranslatableSrai(inner)
    
    def parse_date(self, elem: ET.Element) -> TranslatableDate:
        """Parse <date>"""
        locale: Optional[str] = AimlParser.get_string_by_key(elem, 'locale', False)
        timezone: Optional[int] = int(AimlParser.get_string_by_key(elem, 'timezone', False) or 0)
        dformat: Translatable = self.get_translatable_by_key(elem, 'format')
        return TranslatableDate(dformat, locale, timezone)
    
    def parse_eval(self, elem: ET.Element) -> TranslatableEval:
        """Parse <eval>"""
        return TranslatableEval(self.parse_template(elem))
    
    def parse_learned_category(self, elem: ET.Element) -> LearnedCategory:
        """Parse a <category> inside a <learn>"""
        category: List = [None, None, None, None]
        for child in elem:
            if child.tag.lower() == 'pattern':
                category[0] = self.parse_learned_pattern(child)
            elif child.tag.lower() == 'template':
                category[1] = self.parse_template(child)
            elif child.tag.lower() == 'that':
                category[2] = self.parse_learned_pattern(child)
            elif child.tag.lower() == 'topic':
                category[3] = self.parse_learned_pattern(child)
        if category[0] is None or category[1] is None:
            raise ValueError('<pattern> and <template> must be present in a category')
        return tuple(category)
    
    def parse_learned_pattern(self, elem: ET.Element) ->\
            Optional[Iterable[Union[TranslatableWord, TranslatableEval]]]:
        """Parse a <pattern> within a <learn>"""
        seq: List = []
        if elem.text:
            seq.append(TranslatableWord(elem.text))
        for child in elem:
            if child.tag.lower() == 'eval':
                seq.append(self.parse_eval(child))
            else:
                seq.append(TranslatableWord(ET.tostring(child, 'unicode')))
            if child.tail:
                seq.append(TranslatableWord(child.tail))
        return seq
    
    def parse_unlearn(self, elem: ET.Element) -> TranslatableUnlearn:
        """Pretty straightforward method for <unlearn />"""
        return TranslatableUnlearn()

    #==========A public-facing static method that Brain also uses=========

    @staticmethod
    def literal_to_pattern(toks: str) -> List[PatternToken]:
        """Lowercases and whitespace-strips the provided string,
        then tokenizes it into words splitting by whitespace and returns
        a list of PatternTokens in sequential order"""
        words: List[str] = re.split('\\s+', toks.lower().strip())
        pattern_toks: List[PatternToken] = []
        for word in words:
            if word[0] == '$':
                pattern_toks.append(PatternTokens.PRIORITY)
                pattern_toks.append(PatternToken(\
                    literal_value = word[1:]))#.translate(str.maketrans('', '', string.punctuation))))
            elif word == '#':
                pattern_toks.append(PatternTokens.OCTOTHORPE)
            elif word == '_':
                pattern_toks.append(PatternTokens.UNDERSCORE)
            elif word == '^':
                pattern_toks.append(PatternTokens.CARAT)
            elif word == '*':
                pattern_toks.append(PatternTokens.ASTERISK)
            else:
                pattern_toks.append(PatternToken(\
                    literal_value = word))#.translate(str.maketrans('', '', string.punctuation))))
        return pattern_toks
    
    #==========Helper functions to reduce redundancy of code==========
    
    def get_translatable_by_key(self, elem: ET.Element, key: str, die: bool = True)\
            -> Optional[Translatable]:
        """First look if there is an attribute in elem named key, then look for a child
        node with that tag. If none is found, and die is True, raise an error,
        otherwise return None"""
        val: Optional[str] = None
        attribs: Dict[str, str] = dict(map(lambda x: (x[0].lower(), x[1]), elem.attrib.items()))
        if key in attribs and attribs[key]:
            val = attribs[key]
        if val:
            return TranslatableWord(val)
        for child in elem:
            if child.tag.lower() == key:
                return self.parse_template(child)
        if die:
            raise ValueError(f"No string named {key} in element '{elem.tag}'")
        return None
    
    @staticmethod
    def get_string_by_key(elem: ET.Element, key: str, die: bool = True) -> Optional[str]:
        """Get a literal string, same as get_translatable_by_key"""
        val: Optional[str] = None
        attribs: Dict[str, str] = dict(map(lambda x: (x[0].lower(), x[1]), elem.attrib.items()))
        if key in attribs:
            val = attribs[key]
        if not val:
            for child in elem:
                child: ET.Element = elem[0]
                if child.tag.lower() == key:
                    val = child.text
                    break
        if not val and die:
            raise ValueError(f"No string named {key} in element '{elem.tag}'")
        return val or None
    
    @staticmethod
    def has_child(elem: ET.Element, key: str) -> bool:
        """Return True iff elem conains a child node with tag == key"""
        for child in elem:
            if child.tag.lower() == key:
                return True
        return False
    
    #==========Internally used class vars, here to stay out of the way==========
    
    _repeats: ClassVar[Set[str]] = {
        'response',
        'input',
        'request'
    }
    _stars: ClassVar[Set[str]] = {
        'star',
        'thatstar',
        'topicstar'
    }
    _template_funcs: ClassVar[Dict[str, Callable[['AimlParser', ET.Element], Translatable]]] = {
        'condition':    parse_condition,
        'random':       parse_random,
        'set':          parse_set,
        'get':          parse_get,
        'think':        parse_think,
        'bot':          parse_bot,
        'map':          parse_map,
        'learn':        parse_learn,
        'that':         parse_that_template,
        'srai':         parse_srai,
        'sr':           parse_srai,
        'date':         parse_date,
        'eval':         parse_eval,
        'unlearn':      parse_unlearn
    }
        