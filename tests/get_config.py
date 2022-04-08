
from dataclasses import (
    dataclass,
    field
)

@dataclass
class BrainConfig:
    max_history: int
    max_srai_recursion: int

@dataclass
class Brain(object):
    config: BrainConfig = field(default_factory = lambda: None)