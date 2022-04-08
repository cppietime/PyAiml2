"""
aiml/tests/response_test.py
"""
import json
import logging

from aiml.parser import AimlParser
from aiml.brain import Brain

source = """\
<aiml>
<category>
<pattern>A simple pattern</pattern>
<template>Recognizing a simple pattern<think><set name="topic">test big</set></think></template>
</category>
<category>
<pattern>Before * after</pattern>
<template>You said <star /></template>
</category>
<category>
<pattern>What did you say?</pattern>
<template>I said <that /></template>
</category>
<category>
<pattern>you did not *</pattern>
<that>I said *</that>
<template><star /> and <thatstar /></template>
</category>
<category>
<pattern>Inner topic</pattern>
<topic>test *</topic>
<template>Yes to the inner <topicstar /></template>
</category>
<topic name="test *">
<category>
<pattern>Outer topic</pattern>
<template>Yes to the bigboy <topicstar /></template>
</category>
</topic>
<category>
<pattern>redirect for *</pattern>
<template>I will fetch <sr /></template>
</category>
<category>
<pattern>what is my topic?</pattern>
<template>The topic is <get><name>topic</name></get></template>
</category>
<category>
<pattern>learn anything</pattern>
<template>Now I know something
<learn>
<category>
<pattern>did you learn</pattern>
<template>I learned</template>
</category>
</learn>
</template>
</category>
<category>
<pattern>learn that * is *</pattern>
<template>Now I know that <star index="1" /> is <star index="2" />
<learn>
<category>
<pattern>is <eval><star index="1" /> <star index="2" /></eval> in *</pattern>
<template><eval><star index="1" /> is <star index="2" /></eval> even not in <star /></template>
</category>
</learn>
</template>
</category>
</aiml>
"""

def main():
    logging.basicConfig(level='DEBUG')
    parser = AimlParser()
    tree = parser.parse_string(source)
    brain = Brain()
    brain.pattern_tree = tree
    try:
        while True:
            line = input('Say something: ')
            output = brain.get_string_for(line)
            print(output)
    except KeyboardInterrupt:
        pass

if __name__=='__main__':
    main()