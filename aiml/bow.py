"""
aiml/aiml/bow.py
c Yaakov Schectman 2022

A mapping for Bag Of Words

The first intent specified for any BagOfBags will always be the default, such as for when
an input contains NO recognized words.
"""

import json
import math
import string
import re
from dataclasses import (
    dataclass
)
from io import IOBase
from typing import (
    Dict,
    Iterable,
    List,
    Set,
    Tuple
)

_strip = string.punctuation + string.whitespace

@dataclass
class Document:
    """A document being processed when constructing a BOW
    This is only used in the loading process"""
    sentence: str
    bags: Iterable[str]

class BagOfBags:
    """Stores the IDF of each term, and the TF for each term with each document"""
    def __init__(self) -> None:
        self.word_indices: Dict[str, int] = {}
        self.intents: List[int] = []
        self.outputs: List[str] = []
        self.bags: List[Dict[int, float]] = []
        self.idf: List[float] = []
    
    #==========Public facing functions meant to be used as is==========
    
    def load(self, src: IOBase) -> None:
        """Populate this bag of bags with the provided file like containing JSON.
        Does not call .finalize() after, in case you want to run on multiple
        sources, so call that yourself afterwards"""
        d: Dict[str, List[str]] = json.load(src)
        bags: Iterable[Document] = map(lambda x: Document(*x), d.items())
        self.load_docs(bags)
    
    def process(self, sentence: str) -> str:
        """Get the best fitting result for an input sentence.
        No need to preprocess it
        Essentially, this is the whole point of a BagOfBags"""
        words: List[str] = re.split('\\s+', sentence.strip(_strip).lower())
        bag_in: Dict[int, float] = {}
        delta: float = 1 / len(words)
        for word in words:
            if word not in self.word_indices:
                continue
            index: int = self.word_indices[word]
            bag_in[index] = bag_in.get(index, 0) + delta * self.idf[index]
        if len(bag_in) == 0:
            return self.outputs[0]
        queue: List[Tuple[float, int]] = []
        for i, bag in enumerate(self.bags):
            similarity: float = BagOfBags.cosine_similarity_sq(bag_in, bag)
            queue.append((similarity, i))
        queue.sort(reverse=True)
        return self.outputs[self.intents[queue[0][1]]]
    
    #==========Functions for inernal use mainly==========
    
    def load_docs(self, documents: Iterable[Document]) -> None:
        """Load a list of documents to populate this BOW"""
        for doc_i, document in enumerate(documents):
            self.outputs.append(document.sentence)
            for sentence in document.bags:
                self.intents.append(doc_i)
                freqs: Dict[int, float] = {}
                self.bags.append(freqs)
                words: List[str] = re.split('\\s+', sentence.strip(_strip).lower())
                delta: float = 1 / len(words)
                encountered: Set[str] = set()
                for word in words:
                    if word not in self.word_indices:
                        self.word_indices[word] = len(self.word_indices)
                        self.idf.append(0)
                    index: int = self.word_indices[word]
                    if word not in encountered:
                        encountered.add(word)
                        self.idf[index] += 1
                    freqs[index] = freqs.get(index, 0) + delta
    
    def finalize(self) -> None:
        """Calculate the IDFs of each term.
        Call this once you've loaded all your sources,
        before you start calling .process()"""
        for index, freq in enumerate(self.idf):
            self.idf[index] = math.log(len(self.intents) / freq)
        for bag in self.bags:
            for index, freq in bag.items():
                bag[index] *= self.idf[index]
    
    @staticmethod
    def cosine_similarity_sq(bag_a: Dict[int, float], bag_b: Dict[int, float]) -> float:
        """Actually returns the square of cosine similarity, which can still be sorted,
        as all elements will be non-negative"""
        dot_prod: float = sum(map(lambda x: bag_a[x] * bag_b.get(x, 0), bag_a))
        sq_a: float = sum(map(lambda x: x*x, bag_a.values()))
        sq_b: float = sum(map(lambda x: x*x, bag_b.values()))
        return dot_prod * dot_prod / (sq_a * sq_b)
        