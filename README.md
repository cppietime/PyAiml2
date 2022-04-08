# PyAiml2

PyAiml2 is an AIML (Artificial Intelligence Markup Language) interpreter for Python.

This is inspired by [pyaiml](https://github.com/creatorrr/pyAIML), with some important differences.

The <learn> tag in PyAiml2 works according to the AIML 2.0 specification, and therefore will
cause a new <category> contained within the tag to be learned. Accordingly, the <eval> tag can be
used within a <learn> tag to bind evaluated expressions to their literal expansions at learn-time.

A Brain object does not support multiple sessions at one time. Each Brain has a threading Lock
which it must acquire while it is processing input.

<date> tags should only use the format attribute, not jformat.

I do not know if this was in the specification or not, but words matching a <set> tag in a
<pattern> will be stored as a wildcard.

You can bind callbacks to the Brain object to be called when predicate variables are modified.

PyAiml2 also includes an implementation of a Bag of Words based intent classifier (see bow.py,
bow_test.py, and test_bow.json), which uses cosine similarity of the TF-IDF bags of words between
input and its saved bags. A PyAiml2 Brain may optionally load a BagOfBags to use as a fallback for
when no pattern matches an input. If this is used, it will pass the input to the BagOfBags, and
whatever the BagOfBags returns for that input will be passed again as input to the AIML Brain. This
will not recurse upon failure of the BagOfBags output to match a pattern.