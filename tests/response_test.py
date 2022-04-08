"""
aiml/tests/response_test.py
"""
import json
import logging
from xml.etree import ElementTree as ET

from aiml.brain import Brain
from aiml.parser import AimlParser

source = """\
<aiml>
    <category>
        <pattern>A simple pattern</pattern>
        <template>Recognizing a simple pattern<think><set name="topic">test big</set></think></template>
    </category>
    <category>
        <pattern>Before * after</pattern>
        <template>You said "<star />" when you said "<request />"</template>
    </category>
    <category>
        <pattern>What did you say?</pattern>
        <template>I said "<that />"</template>
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
        <template>Now I know something!!!
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
    <category>
        <pattern>What is the time</pattern>
        <template><date locale="en_US" timezone="-5"><format>%yy %HH %MM</format></date></template>
    </category>
    <category>
        <pattern>is <set name="integers" /> an integer</pattern>
        <template>Yes</template>
    </category>
    <category>
        <pattern>What is the * of *</pattern>
        <template><srai>XMAPTEST <map><name><star index="1" /></name><star index="2" /></map></srai></template>
    </category>
    <category>
        <pattern>XMAPTEST *</pattern>
        <template>It is <star/></template>
    </category>
    <category>
        <pattern>XMAPTEST</pattern>
        <template>There is no good answer</template>
    </category>
    <category>
        <pattern>Set * to *</pattern>
        <template><star /> set to <set><name><star /></name><star index="2" /></set></template>
    </category>
    <category>
        <pattern>Get *</pattern>
        <template><star /> is <get><name><star /></name></get></template>
    </category>
    <category>
        <pattern>One condition on *</pattern>
        <template>First part
        <condition><name><star/></name><value>true</value><star/> is true</condition></template>
    </category>
    <category>
        <pattern>Switch condition on *</pattern>
        <template>First part=
        <condition><name><star/></name>
            <li value="one">1</li>
            <li value="two">2</li>
            <li><value><star/></value>its own name</li>
            <li>None of the above</li>
        </condition></template>
    </category>
    <category>
        <pattern>Compound condition on * and *</pattern>
        <template>First part=<condition>
            <li value="one"><name><star/></name>First var is one</li>
            <li><value>two</value><name><star index="2"/></name>Second var is two</li>
            <li><value><get><name><star index="2"/></name></get></value><name><star/></name>Both are equal</li>
            <li>None of the above</li>
        </condition></template>
    </category>
    <category>
        <pattern>Random response with *</pattern>
        <template><random>
            <li>Response one <star /></li>
            <li>Response two <star /></li>
            <li>Response three <star /></li>
        </random></template>
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
    ET.dump(brain.learned_tree)

if __name__=='__main__':
    main()