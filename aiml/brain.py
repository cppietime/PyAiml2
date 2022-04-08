"""
aiml/src/brain.py
c Yaakov Schectman 2022
"""

import json
import locale
import logging
import re
import string
from dataclasses import (
    dataclass,
    field
)
from datetime import (
    datetime,
    timedelta
)
from os import path
from typing import (
    Dict,
    Set,
    List,
    Optional,
    Iterable,
    Callable,
    ClassVar
)
from xml.etree import ElementTree as ET

from . import (
    config,
    parser,
    pattern,
    translatable
)

_strip: str = '!"#$%&\'()*+,-./:;<=>?@[\\]^_{|}~' + string.whitespace
@dataclass
class Brain(object):
    """The "thinking" part of an AIML bot_name
    Contains the maps, sets, variables, bot properties, history, and pattern matching"""
    brain_config: config.BrainConfig = field(default_factory = lambda: None)
    bot_vars: Dict[str, str] = field(default_factory = dict)
    user_vars: Dict[str, str] = field(default_factory = dict)
    substitutions: Dict[str, Dict[str, str]] = field(default_factory = dict)
    maps: Dict[str, Dict[str, str]] = field(default_factory = dict)
    sets: Dict[str, Set[str]] = field(default_factory = dict)
    history: Dict[str, List[str]] = field(default_factory =\
        lambda: {'input': [], 'request': [], 'response': []})
    that_history: List[List[str]] = field(default_factory = list)
    stars: List[str] = field(default_factory = list)
    that_stars: List[str] = field(default_factory = list)
    topic_stars: List[str] = field(default_factory = list)
    pattern_tree: pattern.PatternTree = field(default_factory = pattern.PatternTree)
    learned_tree: ET.Element = field(default_factory = lambda: ET.Element('aiml'))
    aiml_parser: parser.AimlParser = field(default_factory = parser.AimlParser)
    
    def load_props(self) -> None:
        """Load properties from files"""
        if self.brain_config is None:
            return
        try:
            self.bot_vars = json.load(self.brain_config.bot_file_path)
        except:
            print(f'Could not load bot vars from {self.brain_config.bot_file_path}')
        try:
            self.user_vars = json.load(self.brain_config.init_vars_path)
        except:
            print(f'Could not load user vars from {self.brain_config.init_vars_path}')
        for set_file in (self.brain_config.set_files or ()):
            try:
                self.sets[path.splitext(path.basename(set_file))[0].lower()] =\
                    json.load(set_file)
            except:
                print(f'Could not load set from {set_file}')
        for map_file in (self.brain_config.map_files or ()):
            try:
                self.maps[path.splitext(path.basename(map_file))[0].lower()] =\
                    json.load(map_file)
            except:
                print(f'Could not load map from {map_file}')
        for sub_file in (self.brain_config.sub_files or ()):
            try:
                self.substitutions[path.splitext(path.basename(sub_file))[0].lower()] =\
                    json.load(sub_file)
            except:
                print(f'Could not load substitution from {sub_file}')
    
    def load_learnt_rules(self) -> None:
        if self.pattern_tree is None:
            self.pattern_tree = pattern.PatternTree()
        try:
            learnt_tree: pattern.PatternTree = self.aiml_parser.parse(self.config.learn_file_path)
            self.pattern_tree.merge(learnt_tree)
        except:
            print(f'Failed to load learnt rules from {self.brain_config.learn_file_path}')
    
    def get_srai(self, subquery: str) -> str:
        """Perform a SRAI subquery and return the result.
        Side-effects will take place regardless of what happens to the output"""
        return self.get_string_for(subquery, False)
    
    _builtin_sets: ClassVar[Dict[str, Callable[[str], bool]]] = {
        'integers': lambda x: x and (x.isdigit() or x[0] == '-' and x[1:].isdigit())
    }
    def get_in_set(self, set_name: str, key: str) -> bool:
        """Return True if key is in the set named set_name"""
        set_name = set_name.lower()
        key = key.lower()
        if set_name in Brain._builtin_sets:
            res: bool = Brain._builtin_sets[set_name](key)
            return res
        return set_name in self.sets and key in self.sets[set_name]
    
    _builtin_maps: ClassVar[Dict[str, Callable[[str], str]]] = {
        'successor': lambda x: str(int(x) + 1) if x and (x.isdigit() or x[0] == '-' and x[1:].isdigit()) else '',
        'predecessor': lambda x: str(int(x) - 1) if x and (x.isdigit() or x[0] == '-' and x[1:].isdigit()) else ''
    }
    def get_map(self, map_name: str, key: str) -> str:
        """Return the proper value corresponding to key in map_name
        Return '' if there is no match"""
        map_name = map_name.lower()
        key = key.lower()
        if map_name in Brain._builtin_maps:
            return Brain._builtin_maps[map_name](key)
        return '' if (map_name not in self.maps or key.lower() not in self.maps[map_name])\
            else self.maps[map_name][key.lower()]
    
    def get_bot(self, bot_name: str) -> str:
        """Get the bot property named bot_name
        Return '' if no bot matters"""
        return '' if bot_name.lower() not in self.bot_vars else self.bot_vars[bot_name.lower()]
    
    def get_var(self, var_name: str) -> str:
        """Get the predicate variable named var_name
        Return '' if no variable matches"""
        return '' if var_name.lower() not in self.user_vars else self.user_vars[var_name.lower()]
    
    def get_substitution(self, subst_name: str, value: str) -> str:
        """Perform piece by piece substitution on value with subst_name
        If the substitution name is invalid, return the provided input"""
        if subst_name.lower() not in self.substitutions:
            return value
        substitutions: Dict[str, str] = self.substitutions[subst_name.lower()]
        build: str = ''
        remaining: str = value.lower()
        while len(remaining) > 0:
            pos: int = len(remaining)
            match_key: Optional[str] = None
            for key in substitutions:
                npos: int = remaining.find(key.lower())
                if npos != -1 and npos < pos:
                    pos = npos
                    match_key = key
            build += remaining[:pos]
            if match_key is not None:
                substr: str = remaining[pos : pos + len(match_key)]
                pos += len(match_key)
                build += substitutions[match_key]
            remaining = remaining[pos:]
        return build
    
    def get_repeat(self, index: int, repeat_type: str) -> str:
        """Get a history value at index (1 = most recent), and given repeat_type
        If the index is out of bounds for repeat_type, return ''"""
        if repeat_type.lower() in self.history and index <= len(self.history[repeat_type.lower()]):
            return self.history[repeat_type.lower()][-index]
        return ''
    
    def get_that(self, index: int, sentence: int) -> str:
        """Get a "that" context result
        If the indices are out of bounds, return ''"""
        if index <= len(self.that_history) and sentence <= len(self.that_history[-index]):
            return self.that_history[-index][-sentence]
        return ''
    
    def get_date(self, dformat: str, localet: Optional[str], timezone: Optional[str]) -> str:
        """Get a formatted date"""
        if localet is not None:
            locale.setlocale(locale.LC_TIME, localet)
        if timezone is None:
            now = datetime.now()
        else:
            now = datetime.utcnow() - timedelta(hours = timezone)
        return now.strftime(dformat)
    
    def set_var(self, var_name: str, value: str) -> None:
        """Set a predicate variable"""
        self.user_vars[var_name.lower()] = value
    
    def get_star(self, index: int, star_type: str) -> str:
        """Get any type of star with a provided index
        If there is no appropriate star at the given index, return ''"""
        choice: List[str]
        if star_type.lower() == 'star':
            choice = self.stars
        elif star_type.lower() == 'thatstar':
            choice = self.that_stars
        else:
            choice = self.topic_stars
        if len(choice) == 0:
            return ''
        if index - 1 < 0 or index - 1 >= len(choice):
            return choice[0]
        return choice[index]
        return pattern_toks
    
    def learn_strtoks(self, pattern: Iterable[str],\
            template: 'Translatable',\
            that: Optional[Iterable[str]] = None,\
            topic: Optional[Iterable[str]] = None,\
            learned: bool = False) -> None:
        """Learn a new pattern from the <learn> tag
        Desired spaces will be encoded in the literal segments of the pattern, so I will
        join on the empty string"""
        pattern_str: str = ''.join(pattern)
        that_str: str = '' if that is None else ''.join(that)
        topic_str: str = '' if topic is None else ''.join(topic)
        pattern_toks: List[pattern.PatternToken] = parser.AimlParser.literal_to_pattern(pattern_str)
        that_toks = None if topic is None else\
            parser.AimlParser.literal_to_pattern(that_str)
        topic_toks = None if topic is None else\
            parser.AimlParser.literal_to_pattern(topic_str)
        self.pattern_tree.add(pattern_toks, template, that_toks, topic_toks)
        if learned:
            category: ET.Element = ET.SubElement(self.learned_tree, 'category')
            pat_elem: ET.Element = ET.SubElement(category, 'pattern')
            pat_elem.text = pattern_str
            if that_str:
                that_elem: ET.Element = ET.SubElement(category, 'that')
                that_elem.text = that_str
            if topic_str:
                topic_elem: ET.Element = ET.SubElement(category, 'topic')
                topic_elem.text = topic_str
            templ_elem: ET.Element = ET.SubElement(category, 'template')
            template.append_to(templ_elem)
    
    def get_string_for(self, provided: str, strip: bool = True) -> str:
        """Calculate and return the string response for a string input,
        performing any side effects in the process.
        provided can be multiple sentences, separated by periods.
        Each sentence will map to one output sentence, joind by periods"""
        self.history['request'].append(provided)
        if strip:
            provided = provided.replace('`', '')
        sentences: List[str] = re.split('[.!?]+ ', provided.strip(_strip))
        output: List[str] = []
        that_lst: List[str] = []
        for sentence in sentences:
            self.history['input'].append(sentence.split)
            words = re.split('\\s+', sentence.lower().strip())
            match: Optional[PatternMatch] = self.pattern_tree.match(words, self)
            if match is None:
                output.append(None)
            else:
                self.stars = match.stars
                self.that_stars = match.that_stars
                self.topic_stars = match.topic_stars
                rendered: str = match.translatable.translate(self).strip()
                if rendered != '' and not rendered[-1] in string.punctuation:
                    rendered += '.'
                that_lst.append(rendered)
                output.append(rendered)
        self.that_history.append(that_lst)
        response: str = ' '.join(filter(bool, output))
        self.history['response'].append(response)
        return response
