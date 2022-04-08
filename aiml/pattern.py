"""
aiml/pattern.py
c Yaakov Schectman 2022
"""
import logging
import re
import string
from enum import (
    auto,
    Enum
)
from dataclasses import (
    dataclass,
    field
)
from typing import (
    Dict,
    List,
    Optional,
    Tuple,
    Union
)

from .protocols import ContextLike

class WildcardType(Enum):
    PRIORITY        =  0
    OCTOTHORPE      =  1
    UNDERSCORE      =  2
    BOT_VAR         =  3
    GET_VAR         =  4
    LITERAL         =  5
    SET_MAP         =  6
    CARAT           =  7
    ASTERISK        =  8
    DELIM_THAT      =  9
    DELIM_TOPIC     = 10
    END_PATTERN     = 11

@dataclass
class PatternToken(object):
    """
    A single element within a pattern to match
    """
    literal_value: Optional[str] = None
    wildcard_type: WildcardType = WildcardType.LITERAL
    
    def __hash__(self) -> int:
        return hash(self.wildcard_type.value * 257 + hash((self.literal_value or '').lower()))
    
    def __eq__(self, other: 'PatternToken') -> bool:
        return self.wildcard_type == other.wildcard_type and\
            self.literal_value.lower() ==\
            other.literal_value.lower()

class PatternTokens(object):
    """
    A namespace for constant pattern tokens
    """
    PRIORITY:       PatternToken = PatternToken(wildcard_type = WildcardType.PRIORITY)
    OCTOTHORPE:     PatternToken = PatternToken(wildcard_type = WildcardType.OCTOTHORPE)
    UNDERSCORE:     PatternToken = PatternToken(wildcard_type = WildcardType.UNDERSCORE)
    SET_MAP:        PatternToken = PatternToken(wildcard_type = WildcardType.SET_MAP)
    BOT_VAR:        PatternToken = PatternToken(wildcard_type = WildcardType.BOT_VAR)
    GET_VAR:        PatternToken = PatternToken(wildcard_type = WildcardType.GET_VAR)
    CARAT:          PatternToken = PatternToken(wildcard_type = WildcardType.CARAT)
    ASTERISK:       PatternToken = PatternToken(wildcard_type = WildcardType.ASTERISK)
    DELIM_THAT:     PatternToken = PatternToken(wildcard_type = WildcardType.DELIM_THAT)
    DELIM_TOPIC:    PatternToken = PatternToken(wildcard_type = WildcardType.DELIM_TOPIC)
    END_PATTERN:    PatternToken = PatternToken(wildcard_type = WildcardType.END_PATTERN)

@dataclass
class PatternMatch:
    """A match made on a certain pattern, including the wildcards matched along the way"""
    translatable: 'Translatable'
    stars: List[str] = field(default_factory = list)
    that_stars: List[str] = field(default_factory = list)
    topic_stars: List[str] = field(default_factory = list)
    
    def as_that(self) -> 'PatternMatch':
        """Translate stars into that_stars for sub-matching THAT clauses"""
        if len(self.stars) == 0:
            return self
        return PatternMatch(self.translatable,\
            that_stars = self.stars,\
            topic_stars = self.topic_stars)
    
    def as_topic(self) -> 'PatternMatch':
        """Translate stars into topic_stars for sub-matching TOPIC clauses"""
        if len(self.stars) == 0:
            return self
        return PatternMatch(self.translatable,\
            that_stars = self.that_stars,\
            topic_stars = self.stars)

@dataclass
class PatternTree:
    index: Dict[PatternToken, 'PatternTree'] = field(default_factory = dict)
    terminal: Optional['Translatable'] = None
    
    def add(self,\
            pattern_tokens: List[PatternToken],\
            result: 'Translatable',\
            that_tokens: Optional[List[PatternToken]] = None,\
            topic_tokens: Optional[List[PatternToken]] = None) -> None:
        """Recursively traverse a tree and add the result of a pattern to it"""
        if len(pattern_tokens) == 0:
            if that_tokens is not None:
                sub_tree: 'PatternTree' = PatternTree()
                sub_tree.add(that_tokens, result, None, topic_tokens)
                self.index[PatternTokens.DELIM_THAT] = sub_tree
            elif topic_tokens is not None:
                sub_tree: 'PatternTree' = PatternTree()
                sub_tree.add(topic_tokens, result, None, None)
                self.index[PatternTokens.DELIM_TOPIC] = sub_tree
            else:
                self.terminal = result
            return
        prefix: PatternToken = pattern_tokens[0]
        if prefix not in self.index:
            self.index[prefix] = PatternTree()
        self.index[prefix].add(pattern_tokens[1:], result, that_tokens, topic_tokens)
    
    def merge(self, other: 'PatternTree') -> None:
        """Merge all pattersn from another tree into this one
        Overrides conflicting patterns with those of the other tree"""
        for key in other.index:
            if key in self.index:
                self.index[key].merge(other.index[key])
            else:
                self.index[key] = other.index[key]
        if other.terminal is not None:
            self.terminal = other.terminal
    
    def match(self,\
            sentence: List[str],\
            context: ContextLike) -> Optional[PatternMatch]:
        """Search for a match in this pattern tree for provided word list"""
        # If there are no more words left, either we have a match here or we have no match
        if len(sentence) == 0:
            # A corresponding THAT pattern exists, and a THAT string exists
            if PatternTokens.DELIM_THAT in self.index and\
                    len(context.that_history) != 0 and\
                    len(context.that_history[-1]) != 0:
                that: str = context.that_history[-1][-1]\
                    .lower()\
                    .translate(str.maketrans('', '', string.punctuation))
                that_words: List[str] = re.split('\\s+', that)
                that_match: Optional[PatternMatch] =\
                    self.index[PatternTokens.DELIM_THAT].match(that_words, context)
                if that_match is not None:
                    return that_match.as_that()
            # A corresponding TOPIC pattern exists, and a TOPIC string exists
            if PatternTokens.DELIM_TOPIC in self.index and\
                    'topic' in context.user_vars:
                topic: str = context.user_vars['topic']\
                    .lower()\
                    .translate(str.maketrans('', '', string.punctuation))
                topic_words: List[str] = re.split('\\s+', topic)
                topic_match: Optional[PatternMatch] =\
                    self.index[PatternTokens.DELIM_TOPIC].match(topic_words, context)
                if topic_match is not None:
                    return topic_match.as_topic()
            # A pattern exists that ends here. sentence is already empty so stars will be none
            if self.terminal is not None:
                return PatternMatch(self.terminal)
            return None
        # Go through each match type, if present, in order of priority
        if PatternTokens.PRIORITY in self.index:
            match: Optional[PatternMatch] =\
                self.index[PatternTokens.PRIORITY].match(sentence, context)
            if match is not None:
                return match
        
        # Underscore and octothorpe do the same thing, just a matter of whether they require
        # skipping ahead by one word before we start
        star_index: int = -1
        # Octothorpe takes priority, I think
        if PatternTokens.OCTOTHORPE in self.index:
            star_index = 0
            next_pattern: 'PatternTree' = self.index[PatternTokens.OCTOTHORPE]
        elif PatternTokens.UNDERSCORE in self.index:
            star_index = 1
            next_pattern = self.index[PatternTokens.UNDERSCORE]
        if star_index != -1:
            for i in range(star_index, len(sentence) + 1):
                star_match: PatternMatch = next_pattern.match(sentence[i:], context)
                if star_match != None:
                    # Here I join on space since these are tokens that have already
                    # been split on whitespace
                    new_star = ' '.join(sentence[:i])
                    star_match.stars.insert(0, new_star)
                    return star_match
                    
        # If we are looking for a bot variable
        if PatternTokens.BOT_VAR in self.index:
            word: str = sentence[0].lower().translate(str.maketrans('', '', string.punctuation))
            for key, next_pattern in self.index[PatternTokens.BOT_VAR].index:
                if context.get_bot(key)\
                        .lower()\
                        .translate(str.maketrans('', '', string.punctuation)) == word:
                    bot_match: Optional[PatternMatch] =\
                        self.index[key].match(sentence[1:], context)
                    if bot_match != None:
                        bot_match.stars.insert(0, sentence[0])
                        return bot_match
        # If we are looking for a user variable
        if PatternTokens.GET_VAR in self.index:
            word: str = sentence[0].lower().translate(str.maketrans('', '', string.punctuation))
            for key, next_pattern in self.index[PatternTokens.GET_VAR].index:
                if context.get_var(key)\
                        .lower().\
                        translate(str.maketrans('', '', string.punctuation)) == word:
                    var_match: Optional[PatternMatch] =\
                        self.index[key].match(sentence[1:], context)
                    if var_match != None:
                        var_match.stars.insert(0, sentence[0])
                        return var_match
        
        # Default priority literal word
        literal: PatternToken = PatternToken(literal_value = sentence[0])
        if literal in self.index:
            lit_match: PatternMatch = self.index[literal].match(sentence[1:], context)
            if lit_match is not None:
                return lit_match
        
        # Next is matching a set
        if PatternTokens.SET_MAP in self.index:
            set_item: PatternTree = self.index[PatternTokens.SET_MAP]
            word: str = sentence[0].lower()
            for key, next_pattern in set_item.index.items():
                if context.get_in_set(key.literal_value, word):
                    set_match: Optional[PatternMatch] =\
                        next_pattern.match(sentence[1:], context)
                    if set_match is not None:
                        set_match.stars.insert(0, sentence[0])
                        return set_match
        
        # Carat and asterisk do the same thing, just a matter of whether they require
        # skipping ahead by one word before we start
        star_index: int = -1
        # Carat takes priority, I think
        if PatternTokens.CARAT in self.index:
            star_index = 0
            next_pattern: 'PatternTree' = self.index[PatternTokens.CARAT]
        elif PatternTokens.ASTERISK in self.index:
            star_index = 1
            next_pattern = self.index[PatternTokens.ASTERISK]
        if star_index != -1:
            for i in range(star_index, len(sentence) + 1):
                star_match: PatternMatch = next_pattern.match(sentence[i:], context)
                if star_match != None:
                    # See above for comment on joining on space
                    new_star = ' '.join(sentence[:i])
                    star_match.stars.insert(0, new_star)
                    return star_match
        
        # None matched
        return None
    
