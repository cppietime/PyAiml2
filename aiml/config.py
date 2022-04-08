"""
aiml/src/config.py
c Yaakov Schectman 2022
"""

from dataclasses import dataclass
from typing import (
    Iterable,
    Set
)

@dataclass
class FilesConfig:
    map_files: Set[str]
    set_files: Set[str]
    sub_files: Set[str]
    learn_file_path: str
    bot_file_path: str
    init_vars_file_path: str

@dataclass
class BrainConfig:
    max_history: int
    max_srai_recursion: int