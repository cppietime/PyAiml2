"""
aiml/tests/parser_test.py
"""
import json

from aiml.parser import AimlParser

source = """\
<aiml>
<category>
<pattern>Bring it <set><name>setname</name></set> _</pattern>
<that>I like * too</that>
<template><srai>I like <bot><name>name</name></bot></srai>
<learn>
    <category>
        <pattern>you must like * like <bot var="var" /></pattern>
        <template>I like <sr/> and <eval><thatstar /></eval></template>
    </category>
</learn>
</template>
</category>
</aiml>
"""

def main():
    parser = AimlParser()
    tree = parser.parse_string(source)
    print((tree))

if __name__=='__main__':
    main()