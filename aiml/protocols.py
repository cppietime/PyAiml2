"""
aiml/aiml/protocols.py
c Yaakov Schectman 2022

Used for duck-typing for type hinting to make it clear what methods are available for
certian types not yet declared
"""
from typing import (
    List,
    Protocol,
    Iterable,
    Optional
)

class ContextLike(Protocol):
    """
    Something useful for duck-type-hinting for substitutions
    """
    def get_srai(self, subquery: str) -> str:
        raise NotImplementedError()
    
    def get_in_set(self, set_name: str, key: str) -> bool:
        raise NotImplementedError()
    
    def get_map(self, map_name: str, key: str) -> str:
        raise NotImplementedError()
    
    def get_bot(self, bot_name: str) -> str:
        raise NotImplementedError()
    
    def get_var(self, var_name: str) -> str:
        raise NotImplementedError()
    
    def get_substitution(self, subst_name: str, value: str) -> str:
        raise NotImplementedError()
    
    def get_repeat(self, index: int, repeat_type: str) -> str:
        raise NotImplementedError()
    
    def get_that(self, index: int, sentence: int) -> str:
        raise NotItmplementedError()
    
    def get_date(self, dformat: str, locale: Optional[str], timezone: Optional[int]) -> str:
        raise NotImplementedError()
    
    def set_var(self, var_name: str, value: str) -> None:
        raise NotImplementedError()
    
    def get_star(self, index: int, star_type: str) -> str:
        raise NotImplementedError()
    
    def learn_strtoks(self, pattern: Iterable[str],\
            template: 'Translatable',\
            that: Optional[Iterable[str]] = None,\
            topic: Optional[Iterable[str]] = None,\
            learned: bool = False) -> None:
        raise NotImplementedError()
    
    def unlearn(self) -> None:
        raise NotImplementedError()