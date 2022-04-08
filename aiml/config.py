"""
aiml/aiml/config.py
c Yaakov Schectman 2022

Configuration data class(es) for spinning up AIML brains
"""

from dataclasses import (
    dataclass,
    field
)
from typing import (
    Iterable
)

@dataclass
class BrainConfig:
    """The configuration used to start/load a brain
    max_history: max number of previous input/output to save
    max_srai_recursion: max number of resursive calls to SRAI
    brain_files: set of paths to .aiml files containing AIML brain definitions
    map_files: set of paths to .json files, base names are the map names
    set_files: set of paths to .json files
    sub_files: set of paths to .json files
    learn_file_path: path to read and write rules from <learn>
    bot_file_path: path to .json file with bot properties
    init_vars_file_path: path to .json file with current variable values
    bow_file_path: path to .json with the bag of words intent classifications"""
    max_history: int = field(default=-1)
    max_srai_recursion: int = field(default=30)
    brain_files: Iterable[str] = field(default_factory=list)
    map_files: Iterable[str] = field(default_factory=list)
    set_files: Iterable[str] = field(default_factory=list)
    sub_files: Iterable[str] = field(default_factory=list)
    brain_files: Iterable[str] = field(default_factory=list)
    learn_file_path: str = 'knowledge.aiml'
    bot_file_path: str = 'bot.json'
    init_vars_file_path: str = 'var.json'
    bow_file_path: str = 'bow.json'