"""
aiml/tests/const_pattern_test.py
"""

from aiml.brain import Brain

def main():
    brain = Brain()
    pattern = ' One word after  another!!'
    brain.learn_strtoks([pattern], 1)
    pattern = 'One term and then more'
    brain.learn_strtoks([pattern], 2)
    pattern = 'Before underscore _ after'
    brain.learn_strtoks([pattern], 3)
    pattern = 'Before asterisk * after'
    brain.learn_strtoks([pattern], 4)
    pattern = 'Before underscore $priority after'
    brain.learn_strtoks([pattern], 5)
    pattern = '^ Testing zeros'
    brain.learn_strtoks([pattern], 6)
    assert(brain.pattern_tree.match(['one', 'word', 'after', 'another'], brain).translatable == 1)
    assert(brain.pattern_tree.match(['one', 'word', 'after'], brain) is None)
    assert(brain.pattern_tree.match(['before', 'underscore', 'and', 'after'], brain).translatable == 3)
    assert(brain.pattern_tree.match(['before', 'underscore', 'and', 'then', 'after'], brain).translatable == 3)
    assert(brain.pattern_tree.match(['before', 'underscore', 'after'], brain) == None)
    assert(brain.pattern_tree.match(['before', 'underscore', 'and'], brain) == None)
    assert(brain.pattern_tree.match(['before', 'underscore', 'priority', 'after'], brain).translatable == 5)
    assert(brain.pattern_tree.match(['testing', 'zeros'], brain).translatable == 6)
    assert(brain.pattern_tree.match(['i', 'am', 'busy', 'testing', 'zeros'], brain).translatable == 6)
    print('Passed')

if __name__=='__main__':
    main()