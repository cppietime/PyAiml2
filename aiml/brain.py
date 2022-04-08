"""
aiml/src/brain.py
c Yaakov Schectman 2022
"""

import locale
import string
from dataclasses import (
    dataclass,
    field
)
from datetime import datetime, timedelta
import logging
from typing import (
    Dict,
    Set,
    List,
    Optional,
    Iterable
)
import re

from . import (
    translatable,
    pattern
)

@dataclass
class BrainConfig:
    max_history: int
    max_srai_recursion: int
    learn_file_path: str
    bot_file_path: str

@dataclass
class Brain(object):
    config: BrainConfig = field(default_factory = lambda: None)
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
    learned_tree: pattern.PatternTree = field(default_factory = pattern.PatternTree)
    
    def get_srai(self, subquery: str) -> str:
        return self.get_string_for(subquery)
    
    def get_in_set(self, set_name: str, key: str) -> bool:
        return set_name.lower() in self.sets and key.lower() in self.sets[set_name.lower()]
    
    def get_map(self, map_name: str, key: str) -> str:
        return '' if map_name.lower() not in self.maps else self.maps[map_name.lower()][key.lower()]
    
    def get_bot(self, bot_name: str) -> str:
        return '' if bot_name.lower() not in self.bot_vars else self.bot_vars[bot_name.lower()]
    
    def get_var(self, var_name: str) -> str:
        return '' if var_name.lower() not in self.user_vars else self.user_vars[var_name.lower()]
    
    def get_substitution(self, subst_name: str, value: str) -> str:
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
        if repeat_type.lower() in self.history and index < len(self.history[repeat_type.lower()]):
            return self.history[repeat_type.lower()][-index]
        return ''
    
    def get_that(self, index: int, sentence: int) -> str:
        if index <= len(self.that_history) and sentence <= len(self.that_history[-index]):
            return self.that_history[-index][-sentence]
        return ''
    
    def get_date(self, dformat: str, localet: Optional[str], timezone: Optional[str]) -> str:
        if localet is not None:
            locale.setlocale(localet)
        if timezone is None:
            now = datetime.now()
        else:
            now = datetime.utcnow() - datetime.timedelta(hours = timezone)
        return now.strftime
    
    def set_var(self, var_name: str, value: str) -> None:
        self.user_vars[var_name.lower()] = value
    
    def get_star(self, index: int, star_type: str) -> str:
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

    @staticmethod
    def literal_to_pattern(toks: str) -> List[pattern.PatternToken]:
        """Lowercases and whitespace-strips the provided string,
        then tokenizes it into words splitting by whitespace and returns
        a list of PatternTokens in sequential order"""
        words: List[str] = re.split('\\s+', toks.lower().strip())
        pattern_toks: List[pattern.PatternToken] = []
        for word in words:
            if word[0] == '$':
                pattern_toks.append(pattern.PatternTokens.PRIORITY)
                pattern_toks.append(pattern.PatternToken(\
                    literal_value = word[1:].translate(str.maketrans('', '', string.punctuation))))
            elif word == '#':
                pattern_toks.append(pattern.PatternTokens.OCTOTHORPE)
            elif word == '_':
                pattern_toks.append(pattern.PatternTokens.UNDERSCORE)
            elif word == '^':
                pattern_toks.append(pattern.PatternTokens.CARAT)
            elif word == '*':
                pattern_toks.append(pattern.PatternTokens.ASTERISK)
            else:
                pattern_toks.append(pattern.PatternToken(\
                    literal_value = word.translate(str.maketrans('', '', string.punctuation))))
        return pattern_toks
    
    def learn_strtoks(self, pattern: Iterable[str],\
            template: 'Translatable',\
            that: Optional[Iterable[str]] = None,\
            topic: Optional[Iterable[str]] = None,\
            learned: bool = False) -> None:
        """Learn a new pattern from the <learn> tag
        Desired spaces will be encoded in the literal segments of the pattern, so I will
        join on the empty string"""
        pattern_toks: List[pattern.PatternToken] = Brain.literal_to_pattern(''.join(pattern))
        that_toks = None if that is None else\
            Brain.literal_to_pattern(' '.join(that))
        topic_toks = None if topic is None else\
            Brain.literal_to_pattern(' '.join(topic))
        self.pattern_tree.add(pattern_toks, template, that_toks, topic_toks)
        if learned:
            self.learned_tree.add(pattern_toks, template, that_toks, topic_toks)
    
    def get_string_for(self, provided: str) -> str:
        self.history['request'].append(provided)
        sentences: List[str] = provided.split('.')
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
                rendered: str = match.translatable.translate(self)
                that_lst.append(rendered)
                output.append(rendered)
        self.that_history.append(that_lst)
        response: str = '. '.join(filter(bool, output))
        self.history['response'].append(response)
        return response
