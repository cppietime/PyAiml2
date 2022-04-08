"""
aiml/tests/bow_test.py
"""

import json
from typing import (
    Dict,
    Iterable,
    List
)

from aiml import bow

def main():
    with open('test_bow.json') as file:
        d: Dict[str, List[str]] = json.load(file)
    bags: Iterable[bow.Document] = map(lambda x: bow.Document(*x), d.items())
    bab: bow.BagOfBags = bow.BagOfBags()
    bab.load_docs(bags)
    bab.finalize()
    while True:
        sentence: str = input('Say something: ')
        result: str = bab.process(sentence)
        print(result)

if __name__ == '__main__':
    main()