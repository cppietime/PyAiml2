"""
aiml/tests/response_test.py
"""
import json
import logging
from xml.etree import ElementTree as ET

from aiml.brain import Brain
from aiml.config import *
from aiml.parser import AimlParser
from aiml import bow

source = """\
<aiml>
    <category>
        <pattern>Last dance for mary jane</pattern>
        <template>One more time to kill the pain</template>
    </category>
    <category>
        <pattern><set name='testset'/> in my set</pattern>
        <template><star/> is in that set</template>
    </category>
</aiml>
"""

def callback(a, b, c):
    print(f'{a} has been updated from {b} to {c}')

def main():
    logging.basicConfig(level='DEBUG')
    # with open('test_bow.json') as file:
        # d: Dict[str, List[str]] = json.load(file)
    # bags: Iterable[bow.Document] = map(lambda x: bow.Document(*x), d.items())
    # bab: bow.BagOfBags = bow.BagOfBags()
    # bab.load_docs(bags)
    # bab.finalize()
    bc = BrainConfig(
        max_history=2,
        max_srai_recursion=4,
        set_files={'testset.json'},
        brain_files={'brain.aiml'},
        sub_files={'person.json'},
        learn_file_path='learn.aiml',
        bot_file_path='bot.json',
        init_vars_file_path='vars.json',
        bow_file_path='test_bow.json'
    )
    parser = AimlParser(bc)
    tree = parser.parse_string(source)
    brain = Brain(brain_config = bc)
    brain.pattern_tree.merge(tree)
    brain.bind('outfit', callback)
    # brain.bow = bab
    # brain.load_props()
    # brain.load_learnt_rules()
    try:
        while True:
            line = input('Say something: ')
            output = brain.process(line)
            print(output)
    except KeyboardInterrupt:
        pass
    # brain.save_vars()
    # brain.save_learnt_rules()

if __name__=='__main__':
    main()