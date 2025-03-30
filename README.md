# TinyRDF

A tiny RDF library.

## Example Usage

Graph terms:
```python
>>> from tinyrdf.terms import BNode, Graph, IRI, Literal, Triple, XSD, dataliteral, textliteral

>>> IRI('s1')
IRI(string='s1')

>>> dataliteral("a")
Literal(string='a', datatype=IRI(string='http://www.w3.org/2001/XMLSchema#string'), language=None, direction=None)

>>> dataliteral("1", datatype=IRI(f'{XSD}integer'))
Literal(string='1', datatype=IRI(string='http://www.w3.org/2001/XMLSchema#integer'), language=None, direction=None)

>>> tl = textliteral("a", language="en")
>>> tl
Literal(string='a', datatype=IRI(string='http://www.w3.org/1999/02/22-rdf-syntax-ns#langString'), language='en', direction=None)


>>> tld = textliteral("b", language="en", direction="rtl")
>>> tld
Literal(string='b', datatype=IRI(string='http://www.w3.org/1999/02/22-rdf-syntax-ns#dirLangString'), language='en', direction='rtl')

>>> Triple(IRI("s1"), IRI("p1"), dataliteral("a"))
Triple(s=IRI(string='s1'), p=IRI(string='p1'), o=Literal(string='a', datatype=IRI(string='http://www.w3.org/2001/XMLSchema#string'), language=None, direction=None))
>>>
```
Graphs are sets of triples:
```python
>>> g1 = set[Triple]()
>>> g1.add(Triple(IRI("s1"), IRI("p1"), dataliteral("1")))
>>> g1.add(Triple(IRI("s1"), IRI("p1"), dataliteral("2", datatype=IRI(f'{XSD}integer'))))

>>> g2 = set[Triple]()
>>> g2.add(Triple(IRI("s1"), IRI("p2"), dataliteral("a")))
>>> g2.add(Triple(IRI("s2"), IRI("p1"), textliteral("b", language="en")))

>>> g = g1 | g2
>>> for triple in sorted(g): print(triple)
Triple(s=IRI(string='s1'), p=IRI(string='p1'), o=Literal(string='1', datatype=IRI(string='http://www.w3.org/2001/XMLSchema#string'), language=None, direction=None))
Triple(s=IRI(string='s1'), p=IRI(string='p1'), o=Literal(string='2', datatype=IRI(string='http://www.w3.org/2001/XMLSchema#integer'), language=None, direction=None))
Triple(s=IRI(string='s1'), p=IRI(string='p2'), o=Literal(string='a', datatype=IRI(string='http://www.w3.org/2001/XMLSchema#string'), language=None, direction=None))
Triple(s=IRI(string='s2'), p=IRI(string='p1'), o=Literal(string='b', datatype=IRI(string='http://www.w3.org/1999/02/22-rdf-syntax-ns#langString'), language='en', direction=None))
>>>
```

Interpretation:
```python
>>> from tinyrdf.model import Model, ModelSpace

>>> meaning = Model()
>>> entity = meaning.get(IRI("urn:x-test:1"))
>>> entity.add(IRI("urn:x-test:ns:rel1"), meaning.get(IRI("urn:x-test:2")))
True
>>> assert entity.remove(IRI("urn:x-test:ns:rel1"), meaning.get(IRI("urn:x-test:2")))

>>> space = ModelSpace()
>>> space.decode(g)
4
>>> meaning = space.default
>>> entity = meaning.get(IRI("s1"))
>>> assert entity is meaning.get(IRI("s1"))

>>> for o in sorted(entity.get_objects(IRI("p1")), key=lambda it: it.term):
...     print(o.term.string)
1
2

>>> for o in entity.get_objects(IRI("p2")):
...     print(o.term.string)
a

>>> for o in entity.get_objects(IRI("p3")):
...     print(o.term)

>>> for s in meaning.get(dataliteral("a")).get_subjects(IRI("p2")):
...     print(s.term)
IRI(string='s1')
>>>
```

Order of resources:
```python
>>> meaning = Model()
>>> for r in sorted(meaning.get(x) for x in [
...     dataliteral('a'),
...     BNode('a'),
...     IRI('urn:x-a'),
...     textliteral('a', 'en'),
...     Triple(IRI('a'), IRI('a'), IRI('a'))
... ]):
...     print(r.term)
IRI(string='urn:x-a')
BNode(string='a')
Literal(string='a', datatype=IRI(string='http://www.w3.org/1999/02/22-rdf-syntax-ns#langString'), language='en', direction=None)
Literal(string='a', datatype=IRI(string='http://www.w3.org/2001/XMLSchema#string'), language=None, direction=None)
Triple(s=IRI(string='a'), p=IRI(string='a'), o=IRI(string='a'))
>>>
```

## Maintenance

```sh
$ python3 -m doctest README.md
```
