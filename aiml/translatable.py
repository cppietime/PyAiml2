"""
aiml/aiml/elements.py
c Yaakov Schectman 2022

A Translatable is an element in a response template that can be performed.
When translate is called on a Translatable, any side effects it has are
performed, and the output is returned.
"""

import copy
import random
import string
import xml.etree.ElementTree as ET
from abc import ABC
from dataclasses import (
    dataclass,
    field
)
from typing import (
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    Union
)

from .protocols import ContextLike

#==========Abstract base class out of which all Translatables are derived==========

class Translatable(ABC):
    """
    Anything that can be translated to a text value
    """
    def translate(self, context: ContextLike) -> str:
        raise NotImplementedError()
    
    def bind_closure(self) -> bool:
        """Override to return True for binds in closures, i.e. <eval>"""
        False
    
    def eval_closure(self, context: ContextLike) -> None:
        """Recursivley go through each child and replace <eval>s with their value"""
        pass
    
    def append_to(self, tree: ET.Element) -> None:
        raise NotImplementedError()
    
    def __str__(self) -> str:
        tree: ET.Element = ET.Element('aiml')
        self.append_to(tree)
        return ET.tostring(tree, 'unicode', short_empty_elements = True)

#==========Concrete Translatable classes===========================
#==========Simple Translatables that require no recursion==========

@dataclass
class TranslatableWord(Translatable):
    """A simple literal"""
    word: str
    def translate(self, context: ContextLike) -> str:
        return self.word
        
    def append_to(self, tree: ET.Element) -> None:
        if len(tree) == 0:
            if not tree.text:
                tree.text = self.word
            else:
                tree.text += self.word
        else:
            tail: str = tree[-1].tail
            if tail is None:
                tail = self.word
            else:
                tail = tail + ' ' + self.word
            tree[-1].tail = tail

@dataclass
class TranslatableUnlearn(Translatable):
    """<unlearn />
    I made this one up. Resets the learned rules
    Does not take effect until next reload though"""
    def translate(self, context: ContextLike) -> str:
        context.unlearn()
        return ''
    
    def append_to(self, tree: ET.Element) -> None:
        ET.SubElement(tree, 'unlearn')

@dataclass
class TranslatableNull(Translatable):
    """Literally an empty element"""
    def translate(self, context: ContextLike) -> str:
        return ''
    
    def append_to(self, tree: ET.Element) -> None:
        pass

#==========Format/transform applications==========

@dataclass
class TranslatableStringop(Translatable):
    """<sentence | uppercase | lowercase | formal | explode>
    Performs a string operation"""
    inner: Translatable
    transform: str
    def translate(self, context: ContextLike) -> str:
        return _stringops[self.transform.lower()](self.inner.translate(context))
    
    def eval_closure(self, context: ContextLike) -> None:
        self.inner.eval_closure(context)
        if self.inner.bind_closure():
            self.inner = TranslatableWord(self.inner.translate(context))
        
    def append_to(self, tree: ET.Element) -> None:
        root: ET.Element = ET.SubElement(tree, self.transform)
        self.inner.append_to(root)

@dataclass
class TranslatableDate(Translatable):
    """<date locale="..." timezone="..."><format>date format</format></date>
    Returns the current date according to the provided format"""
    dformat: Translatable
    locale: Optional[str] = None
    timezone: Optional[int] = 0
    def translate(self, context: ContextLike) -> str:
        format_str: str = self.dformat.translate(context)
        return context.get_date(format_str, self.locale, self.timezone)
    
    def eval_closure(self, context: ContextLike) -> None:
        self.dformat.eval_closure(context)
        if self.dformat.bind_closure():
            self.dformat = TranslatableWord(self.dformat.translate(context))
        
    def append_to(self, tree: ET.Element) -> None:
        root: ET.Element = ET.SubElement(tree, 'date')
        if self.locale is not None:
            date.attrib['locale'] = self.locale
        if self.timezone is not None:
            date.attrib['timezone'] = str(self.timezone)
        name: ET.Element = ET.SubElement(root, 'format')
        self.dformat.append_to(name)

@dataclass
class TranslatableRandom(Translatable):
    """<random><li>output1</li><li>output2</li>...</random>
    Randomly selects one of the li elements to use as output"""
    children: Sequence[Translatable]
    def translate(self, context: ContextLike) -> str:
        child: Translatable = random.choice(self.children)
        return child.translate(context)
    
    def eval_closure(self, context: ContextLike) -> None:
        for i, child in enumerate(self.children):
            child.eval_closure(context)
            if child.bind_closure():
                self.children[i] = TranslatableWord(child.translate(context))
        
    def append_to(self, tree: ET.Element) -> None:
        root: ET.Element = ET.SubElement(tree, 'random')
        for child in self.children:
            li: ET.Element = ET.SubElement(root, 'li')
            child.append_to(li)

#==========Variable replacement tags==========

@dataclass
class TranslatableStar(Translatable):
    """<star | thatstar | topicstar>
    Replace with matching wildcard text in input"""
    index: int = 1
    star_type: str = 'star'
    def translate(self, context: ContextLike) -> str:
        return context.get_star(self.index - 1, self.star_type)
        
    def append_to(self, tree: ET.Element) -> None:
        root: ET.Element = ET.SubElement(tree, self.star_type)
        if self.index != 1:
            root.attrib['index'] = str(self.index)

@dataclass
class TranslatableRepeat(Translatable):
    """<request | response | input index="n" />
    Get the n-th input sentence, full input request, or full response"""
    repeat_type: str
    index: int = 1
    def translate(self, context: ContextLike) -> str:
        return context.get_repeat(self.index, self.repeat_type)
        
    def append_to(self, tree: ET.Element) -> None:
        root: ET.Element = ET.SubElement(tree, self.repeat_type)
        if self.index != 1:
            root.attrib['index'] = str(self.index)

@dataclass
class TranslatableThat(Translatable):
    """<that index="m,n" />
    Substitutes with the n-th to last sentence in the m-th to last response"""
    response: int = 1
    sentence: int = 1
    def translate(self, context: ContextLike) -> str:
        return context.get_that(self.response, self.sentence)
        
    def append_to(self, tree: ET.Element) -> None:
        root: ET.Element = ET.SubElement(tree, 'that')
        root.attrib['index'] = f'{self.response},{self.sentence}'

#==========Get variables/state==========

@dataclass
class TranslatableGet(Translatable):
    """<get><name>variable_name</name></get>
    Gets a variable"""
    key_expr: Translatable
    def translate(self, context: ContextLike) -> str:
        key: str = self.key_expr.translate(context)
        return context.get_var(key)
    
    def eval_closure(self, context: ContextLike) -> None:
        self.key_expr.eval_closure(context)
        if self.key_expr.bind_closure():
            self.key_expr = TranslatableWord(self.key_expr.translate(context))
        
    def append_to(self, tree: ET.Element) -> None:
        root: ET.Element = ET.SubElement(tree, 'get')
        name: ET.Element = ET.SubElement(root, 'name')
        self.key_expr.append_to(name)

@dataclass
class TranslatableBot(Translatable):
    """<bot><name>variable_name</name></bot>
    Gets a bot variable"""
    key_expr: Translatable
    def translate(self, context: ContextLike) -> str:
        key: str = self.key_expr.translate(context)
        return context.get_bot(key)
    
    def eval_closure(self, context: ContextLike) -> None:
        self.key_expr.eval_closure(context)
        if self.key_expr.bind_closure():
            self.key_expr = TranslatableWord(self.key_expr.translate(context))
        
    def append_to(self, tree: ET.Element) -> None:
        root: ET.Element = ET.SubElement(tree, 'bot')
        name: ET.Element = ET.SubElement(root, 'name')
        self.key_expr.append_to(name)

@dataclass
class TranslatableMap(Translatable):
    """<map><name>map name</name>lookup value</map>
    Gets the corresponding map value for provided map name and lookup"""
    map_expr: Translatable
    key_expr: Translatable
    def translate(self, context: ContextLike) -> str:
        map_str: str = self.map_expr.translate(context)
        key_str: str = self.key_expr.translate(context)
        return context.get_map(map_str, key_str)
    
    def eval_closure(self, context: ContextLike) -> None:
        self.map_expr.eval_closure(context)
        if self.map_expr.bind_closure():
            self.map_expr = TranslatableWord(self.map_expr.translate(context))
        self.key_expr.eval_closure(context)
        if self.key_expr.bind_closure():
            self.key_expr = TranslatableWord(self.key_expr.translate(context))
        
    def append_to(self, tree: ET.Element) -> None:
        root: ET.Element = ET.SubElement(tree, 'map')
        name: ET.Element = ET.SubElement(root, 'name')
        self.map_expr.append_to(name)
        self.key_expr.append_to(root)

@dataclass
class TranslatableSubst(Translatable):
    """<person | person2 | normalize | denormalize | gender >
    Performs word-by-word substitution in the provided substitution type"""
    subst_type: str
    expr: Translatable
    def translate(self, context: ContextLike) -> str:
        expr_str: str = self.expr.translate(context)
        return context.get_substitution(self.subst_type, expr_str)
    
    def eval_closure(self, context: ContextLike) -> None:
        self.expr.eval_closure(context)
        if self.expr.bind_closure():
            self.expr = TranslatableWord(self.expr.translate(context))
        
    def append_to(self, tree: ET.Element) -> None:
        root: ET.Element = ET.SubElement(tree, self.subst_type)
        self.expr.append_to(root)

@dataclass
class TranslatableSet(Translatable):
    """<set><name>variable_name</name><value>set_value</value></set>
    Sets a variable to an evaluated value and returns the value"""
    key_expr: Translatable
    value_expr: Translatable
    def translate(self, context: ContextLike) -> str:
        key: str = self.key_expr.translate(context)
        value: str = self.value_expr.translate(context)
        context.set_var(key, value)
        return value
    
    def eval_closure(self, context: ContextLike) -> None:
        self.key_expr.eval_closure(context)
        if self.key_expr.bind_closure():
            self.key_expr = TranslatableWord(self.key_expr.translate(context))
        self.value_expr.eval_closure(context)
        if self.value_expr.bind_closure():
            self.value_expr = TranslatableWord(self.value_expr.translate(context))
        
    def append_to(self, tree: ET.Element) -> None:
        root: ET.Element = ET.SubElement(tree, 'set')
        name: ET.Element = ET.SubElement(root, 'name')
        self.key_expr.append_to(name)
        self.value_expr.append_to(root)

#==========Recursive Translatables==========

@dataclass
class TranslatableIterable(Translatable):
    """A translatable that contains a sequence of zero or more translatables
    The pieces are joined by the empty string because separating spaces will
    end up included in the literal segments"""
    elements: Iterable[Translatable] = field(default_factory = list)
    def translate(self, context: ContextLike) -> str:
        return ''\
            .join(\
                filter(\
                    lambda y: y != '',\
                    map(\
                        lambda x: x.translate(context), self.elements)))
    
    def eval_closure(self, context: ContextLike) -> None:
        for i, element in enumerate(self.elements):
            element.eval_closure(context)
            if element.bind_closure():
                self.elements[i] = TranslatableWord(element.translate(context))
        
    def append_to(self, tree: ET.Element) -> None:
        for child in self.elements:
            child.append_to(tree)

@dataclass
class TranslatableThink(Translatable):
    """<think>inner XML</think>
    A translatable that calls its inner XML when called, but returns nothing"""
    child: Translatable
    def translate(self, context: ContextLike) -> str:
        if self.child is not None:
            self.child.translate(context)
        return ''
    
    def eval_closure(self, context: ContextLike) -> None:
        self.child.eval_closure(context)
        if self.child.bind_closure():
            self.child = TranslatableWord(self.child.translate(context))
        
    def append_to(self, tree: ET.Element) -> None:
        root: ET.Element = ET.SubElement(tree, 'think')
        self.child.append_to(root)

@dataclass
class TranslatableSrai(Translatable):
    """<srai>expression</srai>
    Performs a subquery of sorts on the contained expression"""
    inner_expr: Translatable
    def translate(self, context: ContextLike) -> str:
        inner: str = self.inner_expr.translate(context)
        return context.get_srai(inner)
    
    def eval_closure(self, context: ContextLike) -> None:
        self.inner_expr.eval_closure(context)
        if self.inner_expr.bind_closure():
            self.inner_expr = TranslatableWord(self.inner_expr.translate(context))
        
    def append_to(self, tree: ET.Element) -> None:
        root: ET.Element = ET.SubElement(tree, 'srai')
        self.inner_expr.append_to(root)

@dataclass
class TranslatableCondition(Translatable):
    """<condition><li><name>variable name</name><value>match</value>output</li>...</condition>
    Checks the value of a variable and chooses what to output by it
    Mapping is tuples of the form (name, value, expr, loop)"""
    mapping: Iterable[Tuple[Translatable, Translatable, Translatable, bool]]
    default: Optional[Tuple[Translatable, bool]] = None
    def translate(self, context: ContextLike) -> str:
        for mapping in self.mapping:
            name: str = mapping[0].translate(context)
            value: str = context.get_var(name)
            test: str = mapping[1].translate(context)
            if value.strip().lower().translate(str.maketrans('', '', string.punctuation)) ==\
                    test.strip().lower().translate(str.maketrans('', '', string.punctuation)):
                result: str = mapping[2].translate(context)
                if mapping[3]:
                    result += ' ' + self.translate(context)
                return result
        if self.default is not None:
            result: str = self.default[0].translate(context)
            if self.default[1]:
                result += ' ' + self.translate(context)
            return result
        return ''
    
    def eval_closure(self, context: ContextLike) -> None:
        for mapping in self.mapping:
            for i in range(3):
                mapping[i].eval_closure(context)
                if mapping[i].bind_closure():
                    mapping[i] = TranslatableWord(mapping[i].translate(context))
        if self.default is not None:
            self.default.eval_closure(context)
            self.default.eval_closure(context)
            if self.default.bind_closure():
                self.default = TranslatableWord(self.default.translate(context))
        
    def append_to(self, tree: ET.Element) -> None:
        root: ET.Element = ET.SubElement(tree, 'condition')
        for mapping in self.mapping:
            li: ET.Element = ET.SubElement(root, 'li')
            name: ET.Element = ET.SubElement(li, 'name')
            mapping[0].append_to(name)
            value: ET.Element = ET.SubElement(li, 'value')
            mapping[1].append_to(value)
            mapping[2].append_to(li)
            if mapping[3]:
                ET.SubElement(li, 'loop')
        if self.default is not None:
            li: ET.Element = ET.SubElement(root, 'li')
            self.default[0].append_to(li)
            if self.default[1]:
                ET.SubElement(li, 'loop')

@dataclass
class TranslatableEval(Translatable):
    """<eval>expr</eval>
    Evaluates the inner expression. Only used in learn elements"""
    child: Translatable
    def translate(self, context: ContextLike) -> str:
        return self.child.translate(context)
    
    def bind_closure(self) -> bool:
        return True
        
    def append_to(self, tree: ET.Element) -> None:
        root: ET.Element = ET.SubElement(tree, 'eval')
        self.child.append_to(root)

@dataclass
class TranslatableLearn(Translatable):
    """<learn>
    <category>
    <pattern>text | <eval/></pattern>
    [<that>text | <eval /></that>]
    [<topic>text | <eval /></topic>]
    <template>output</template>
    </category>
    </learn>
    When triggered, learns a new category
    Since this should be the only Translatable to contain eval statements,
    it can pass in its eval_closure method"""
    pattern_exprs: Iterable[Union[TranslatableWord, TranslatableEval]]
    template_exprs: Translatable
    that_exprs: Optional[Iterable[Union[TranslatableWord, TranslatableEval]]] = None
    topic_exprs: Optional[Iterable[Union[TranslatableWord, TranslatableEval]]] = None
    def translate(self, context: ContextLike) -> str:
        pattern: Iterable[str] = map(lambda x: x.translate(context), self.pattern_exprs)
        that: Optional[Iterable[str]] =\
            map(lambda x: x.translate(context), self.topic_exprs) if\
            self.that_exprs is not None else\
            None
        topic: Optional[Iterable[str]] =\
            map(lambda x: x.translate(context), self.topic_exprs) if\
            self.topic_exprs is not None else\
            None
        template: Translatable = copy.deepcopy(self.template_exprs)
        template.eval_closure(context)
        context.learn_strtoks(pattern, template, that, topic, True)
        return ''
        
    def append_to(self, tree: ET.Element) -> None:
        root: ET.Element = ET.SubElement(tree, 'learn')
        root = ET.SubElement(root, 'category')
        pattern: ET.Element = ET.SubElement(root, 'pattern')
        for expr in self.pattern_exprs:
            expr.append_to(pattern)
        if self.that_exprs is not None:
            that: ET.Element = ET.SubElement(root, 'that')
            for expr in self.that_exprs:
                expr.append_to(that)
        if self.topic_exprs is not None:
            topic: ET.Element = ET.SubElement(root, 'topic')
            for expr in self.topic_exprs:
                expr.append_to(topic)
        template: ET.Element = ET.SubElement(root, 'template')
        self.template_exprs.append_to(template)

#==========Public facing type alias==========

LearnedCategory: type = Tuple[Iterable[Union[TranslatableWord, TranslatableEval]],\
    Translatable,\
    Optional[Iterable[Union[TranslatableWord, TranslatableEval]]],\
    Optional[Iterable[Union[TranslatableWord, TranslatableEval]]]]

#==========Internal-use stringop mappings==========

_stringops: Dict[str, Callable[[str], str]] = {
    'explode': lambda x: ' '.join(list(x)),
    'uppercase': str.upper,
    'lowercase': str.lower,
    'formal': str.title,
    'sentence': str.capitalize
}

