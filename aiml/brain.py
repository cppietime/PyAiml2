"""
aiml/src/brain.py
c Yaakov Schectman 2022
"""

import locale
import string
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import (
    Dict,
    Set,
    List,
    Optional,
    Iterable
)

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

class Brain(object):
    config: BrainConfig
    bot_vars: Dict[str, str]
    user_vars: Dict[str, str]
    substitutions: Dict[str, Dict[str, str]]
    maps: Dict[str, Dict[str, str]]
    sets: Dict[str, Set[str]]
    history: Dict[str, List[str]]
    that_history: List[List[str]]
    stars: List[str]
    that_stars: List[str]
    topic_stars: List[str]
    pattern_tree: pattern.PatternTree = pattern.PatternTree()
    learned_tree: pattern.PatternTree = pattern.PatternTree()
    
    def get_srai(self, subquery: str) -> str:
        raise NotImplementedError()
    
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
        if index < len(self.that_history) and sentence < len(self.that_history[index]):
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
        words: List[str] = list(filter(lambda x: x != '', toks.lower().strip().split(' ')))
        pattern_toks: List[pattern.PatternToken] = []
        for word in words:
            if word[0] == '$':
                pattern_toks.append(pattern.PatternTokens.PRIORITY)
                pattern_toks.append(pattern.PatternToken(literal_value = word[1:].strip(string.punctuation)))
            elif word == '#':
                pattern_toks.append(pattern.PatternTokens.OCTOTHORPE)
            elif word == '_':
                pattern_toks.append(pattern.PatternTokens.UNDERSCORE)
            elif word == '^':
                pattern_toks.append(pattern.PatternTokens.CARAT)
            elif word == '*':
                pattern_toks.append(pattern.PatternTokens.ASTERISK)
            else:
                pattern_toks.append(pattern.PatternToken(literal_value = word.strip(string.punctuation)))
        return pattern_toks
    
    def learn_strtoks(self, pattern: Iterable[str],\
            template: 'Translatable',\
            that: Optional[Iterable[str]] = None,\
            topic: Optional[Iterable[str]] = None,\
            learned: bool = False) -> None:
        pattern_toks: List[pattern.PatternToken] = Brain.literal_to_pattern(' '.join(pattern))
        that_toks = None if that is None else\
            Brain.literal_to_pattern(' '.join(that))
        topic_toks = None if topic is None else\
            Brain.literal_to_pattern(' '.join(topic))
        self.pattern_tree.add(pattern_toks, template, that_toks, topic_toks)
        if learned:
            self.learned_tree.add(pattern_toks, template, that_toks, topic_toks)
