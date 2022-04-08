"""
aiml/aiml/brain.py
c Yaakov Schectman 2022

The Brain is essentially the engine of the AIML bot.
"""

import json
import locale
import logging
import re
import string
import sys
from dataclasses import (
    dataclass,
    field
)
from datetime import (
    datetime,
    timedelta
)
from os import path
from threading import Lock
from typing import (
    Callable,
    ClassVar,
    Dict,
    Iterable,
    List,
    Optional,
    Set
)
from xml.etree import ElementTree as ET

from . import (
    bow,
    config,
    parser,
    pattern,
    translatable
)

_strip: str = '!?."#$%&\'()*+,-/:;<=>@[\\]^_{|}~' + string.whitespace
_remove: str = '!?."#$%&\'()*+,-/:;<=>@[\\]^_{|}~'
_callback: type = Callable[[str, str, str], None]
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
    aiml_parser: parser.AimlParser = field(init = False)
    srai_depth: int = field(init=False, default=0)
    thread_lock: Lock = field(init=False, default_factory = Lock)
    callbacks: Dict[str, List[_callback]] = field(init=False, default_factory=dict)
    bag: Optional[bow.BagOfBags] = field(init=False, default=None)
    
    #==========The meat and potatoes. The public-facing in/out function==========
    def process(self, request: str) -> str:
        """The meat and potatoes. The public-facing in/out function
        The provided request is a string with no preprocessing done, which can
        contain any number of sentences, delimited with periods (.).
        The returned response is also a string consisting of any number of sentences.
        Each input sentence corresponds to a piece of the output in order, which are
        also delimited by periods.
        This method acquires a thread lock in order to ensure one brain only ever
        handles one request at a time, and allow it to run on another thread"""
        self.thread_lock.acquire()
        result: str = self.get_string_for(request, strip=True)
        self.thread_lock.release()
        return result
    
    def bind(self, variable: str, callback: _callback) -> None:
        """Bind a callback to be called whenever a certain variable is updated.
        The callback must accept three string arguments and is not expected to return
        anything.
        The first argument of the callback is the name of set variable,
        the second is its old value, and the final is its new value."""
        variable = variable.lower()
        if variable not in self.callbacks:
            self.callbacks[variable] = []
        self.callbacks[variable].append(callback)
    
    #==========Setup methods to create the Brain==========
    
    def __post_init__(self):
        self.aiml_parser = parser.AimlParser(self.brain_config)
        self.load_brains()
        self.load_props()
        self.load_learnt_rules()
        self.load_bow()
    
    def load_brains(self) -> None:
        for brain_name in (self.brain_config.brain_files or ()):
            self.load_brain_from_path(brain_name)
    
    def load_brain_from_path(self, path: str) -> None:
        """Load a custom specified brain from a path"""
        try:
            loaded_tree: pattern.PatternTree = self.aiml_parser.parse(path)
            self.pattern_tree.merge(loaded_tree)
        except:
            print(f'Failed to load brain from {path}', file=sys.stderr)
    
    def load_props(self) -> None:
        """Load properties from files"""
        if self.brain_config is None:
            return
        self.bot_vars = Brain.deserialize(self.brain_config.bot_file_path) or {}
        self.user_vars = Brain.deserialize(self.brain_config.init_vars_file_path) or {}
        for set_file in (self.brain_config.set_files or ()):
                self.sets[path.splitext(path.basename(set_file))[0].lower()] =\
                    set(Brain.deserialize(set_file) or ())
        for map_file in (self.brain_config.map_files or ()):
                self.maps[path.splitext(path.basename(map_file))[0].lower()] =\
                    Brain.deserialize(map_file) or {}
        for sub_file in (self.brain_config.sub_files or ()):
                self.substitutions[path.splitext(path.basename(sub_file))[0].lower()] =\
                    Brain.deserialize(sub_file) or {}
    
    def load_learnt_rules(self) -> None:
        if self.pattern_tree is None or\
                self.brain_config is None:
            self.pattern_tree = pattern.PatternTree()
        if not self.brain_config.learn_file_path:
            return
        try:
            self.learned_tree = ET.parse(self.brain_config.learn_file_path).getroot()
            learnt_tree: pattern.PatternTree =\
                self.aiml_parser.parse(self.brain_config.learn_file_path)
            self.pattern_tree.merge(learnt_tree)
        except:
            print(f'Failed to load learnt rules from {self.brain_config.learn_file_path}',
                file=sys.stderr)
    
    def load_bow(self) -> None:
        if not self.brain_config.bow_file_path:
            return
        try:
            self.bow = bow.BagOfBags()
            with open(self.brain_config.bow_file_path) as file:
                self.bow.load(file)
            self.bow.finalize()
        except:
            print(f'Failed to load bag of words from {self.brain_config.bow_file_path}')
    
    #==========Methods to save state before shutting down==========
    
    def __del__(self) -> None:
        self.save_vars()
        self.save_learnt_rules()
    
    def save_vars(self) -> None:
        if self.brain_config is None or self.brain_config is None or\
                self.brain_config.init_vars_file_path is None:
            return
        filtered_vars: Dict[str, str] = dict(filter(lambda x: x[1], self.user_vars.items()))
        Brain.serialize(filtered_vars, self.brain_config.init_vars_file_path)
    
    def save_learnt_rules(self) -> None:
        if not self.brain_config.learn_file_path or self.learned_tree is None:
            return
        try:
            ltet: ET.ElementTree = ET.ElementTree(self.learned_tree)
            ltet.write(self.brain_config.learn_file_path)
        except:
            print(f'Failed to save learnt rules to {self.brain_config.learn_file_path}',\
                file = sys.stderr)
    
    #==========Protocol methods as a ContextLike that are called by Translatables==========
    
    def get_srai(self, subquery: str) -> str:
        """Perform a SRAI subquery and return the result.
        Side-effects will take place regardless of what happens to the output"""
        if self.brain_config is not None and self.brain_config.max_srai_recursion > 0\
                and self.brain_config.max_srai_recursion <= self.srai_depth:
            return ''
        self.srai_depth += 1
        result: str = self.get_string_for(subquery, False)
        self.srai_depth -= 1
        return result
    
    def get_in_set(self, set_name: str, key: str) -> bool:
        """Return True if key is in the set named set_name"""
        set_name: str = set_name.lower()
        key: str = key.lower()
        if set_name in Brain._builtin_sets:
            res: bool = Brain._builtin_sets[set_name](key)
            return res
        return set_name in self.sets and key in self.sets[set_name]
    
    def get_map(self, map_name: str, key: str) -> str:
        """Return the proper value corresponding to key in map_name
        Return '' if there is no match"""
        map_name: str = map_name.lower()
        key_lower: str = key.lower()
        if map_name in Brain._builtin_maps:
            return Brain.match_case(Brain._builtin_maps[map_name](key_lower), key)
        return '' if (map_name not in self.maps or key_lower not in self.maps[map_name])\
            else self.maps[map_name][key_lower]
    
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
                    template: str = value[npos:npos+len(key)]
            build += remaining[:pos]
            if match_key is not None:
                substr: str = remaining[pos : pos + len(match_key)]
                pos += len(match_key)
                build += Brain.match_case(substitutions[match_key], template)
            remaining = remaining[pos:]
            value = value[pos:]
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
        var_name = var_name.lower()
        if var_name in self.callbacks:
            old_val: str = '' if var_name not in self.user_vars else self.user_vars[var_name]
            for callback in self.callbacks[var_name]:
                callback(var_name, old_val, value)
        self.user_vars[var_name] = value
    
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
        
        # Actually construct an XML string and parse it to get a pattern tree to merge
        xml_str: str = f'<category><pattern>{pattern_str}</pattern>'
        if that_str:
            xml_str += f'<that>{that_str}</that>'
        if topic_str:
            xml_str += f'<topic>{topic_str}</topic>'
        xml_str += '</category>'
        dummy: ET.Element = ET.fromstring(xml_str)
        tempelm: ET.Element = ET.SubElement(dummy, 'template')
        template.append_to(tempelm)
        new_pattern: pattern.PatternTree = self.aiml_parser.parse_category(dummy)
        self.pattern_tree.merge(new_pattern)
        
        if learned:
            self.learned_tree.append(dummy)
    
    def unlearn(self) -> None:
        """Forget all learned rules"""
        self.learned_tree.clear()
    
    #==========Methods used for actual matching to return results==========
    
    def get_string_for(self, provided: str, strip: bool = True) -> str:
        """Calculate and return the string response for a string input,
        performing any side effects in the process.
        provided can be multiple sentences, separated by periods.
        Each sentence will map to one output sentence, joind by periods"""
        if strip:
            self.history['request'].append(provided)
        sentences: List[str] = re.split('[.!?]+ ', provided.strip())
        output: List[str] = []
        that_lst: List[str] = []
        for sentence in sentences:
            if strip:
                sentence = sentence.translate(str.maketrans('', '', _remove)).strip(_strip)
            if not sentence:
                continue
            if strip:
                self.history['input'].append(sentence.split)
            words = re.split('\\s+', sentence.strip())
            match: Optional[PatternMatch] = self.pattern_tree.match(words, self)
            if match is None:
                if strip and self.bow is not None:
                    intent: str = self.bow.process(provided)
                    subquery: str = self.get_string_for(intent, strip=False)
                    output.append(subquery)
                # Append None for now. Later I think I will have an intent recognizer
                else:
                    output.append(None)
                continue
            else:
                self.stars = match.stars
                self.that_stars = match.that_stars
                self.topic_stars = match.topic_stars
                rendered: str = match.translatable.translate(self).strip()
                if rendered != '' and not rendered[-1] in string.punctuation:
                    rendered += '.'
                if strip:
                    for escaped, unesc in Brain._unescapes.items():
                        rendered = rendered.replace(escaped, unesc)
                that_lst.append(rendered)
                output.append(rendered)
        response: str = ' '.join(filter(bool, output))
        if strip:
            self.that_history.append(that_lst)
            self.history['response'].append(response)
            self.trim_history()
        return response
    
    def trim_history(self):
        """Limit the size of all histories to the specified max length"""
        if self.brain_config is None or self.brain_config.max_history <= 0:
            return
        for key, hlist in self.history.items():
            self.history[key] = hlist[-self.brain_config.max_history:]
        self.that_history = self.that_history[-self.brain_config.max_history:]
    
    #==========Static methods used for utility/redundancy reduction==========
    
    @staticmethod
    def is_int(string: str) -> bool:
        try:
            int(string)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def is_float(string: str) -> bool:
        try:
            float(string)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def safe_eval(code: str) -> str:
        try:
            res = eval(code)
            return str(res)
        except Exception as e:
            return '!Error ' + str(e)
    
    @staticmethod
    def serialize(obj, filename: str):
        if filename:
            try:
                with open(filename, "w") as file:
                    return json.dump(obj, file)
            except:
                print(f'Could not serialize to {filename}',\
                file = sys.stderr   )
    
    @staticmethod
    def deserialize(filename: str):
        if filename:
            try:
                with open(filename) as file:
                    return json.load(file)
            except:
                print(f'Could not deserialize {filename}', file=sys.stderr)
        return None
    
    @staticmethod
    def match_case(operand: str, template: str) -> str:
        if not template or not operand or not operand.islower():
            return operand
        if template.istitle():
            return operand.title()
        if template.isupper():
            return operand.upper()
        if template.islower():
            return operand.lower()
        return operand
    
    #==========Internally used class vars==========

    _builtin_sets: ClassVar[Dict[str, Callable[[str], bool]]] = {
        'integers': lambda x: Brain.is_int(x),
        'reals': lambda x: Brain.is_float(x)
    }
    _builtin_maps: ClassVar[Dict[str, Callable[[str], str]]] = {
        'successor': lambda x: str(int(x) + 1) if Brain.is_int(x) else '',
        'predecessor': lambda x: str(int(x) - 1) if Brain.is_int(x) else '',
        'python': lambda x: Brain.safe_eval(x)
    }
    _unescapes: ClassVar[Dict[str, str]] = {
        '&lt;'  : '<',
        '&gt;'  : '>',
        '&amp;' : '&'
    }
    _escapes: ClassVar[Dict[str, str]] = dict(map(lambda x: (x[1], x[0]), _unescapes.items()))