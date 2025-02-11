# TinyRDF

A tiny RDF library.

## Example Usage

Graph terms:
```python
>>> from tinyrdf.terms import BNode, Graph, IRI, DataLiteral, TextLiteral, Triple, TripleTerm, XSD

>>> IRI('s1')
IRI(string='s1')

>>> DataLiteral("a")
DataLiteral(string='a', datatype=IRI(string='http://www.w3.org/2001/XMLSchema#string'))

>>> DataLiteral("1", datatype=IRI(f'{XSD}integer'))
DataLiteral(string='1', datatype=IRI(string='http://www.w3.org/2001/XMLSchema#integer'))

>>> tl = TextLiteral("a", language="en")
>>> tl
TextLiteral(string='a', language='en', direction=None)
>>> tl.datatype
IRI(string='http://www.w3.org/1999/02/22-rdf-syntax-ns#langString')

>>> tld = TextLiteral("b", language="en", direction="rtl")
>>> tld
TextLiteral(string='b', language='en', direction='rtl')
>>> tld.datatype
IRI(string='http://www.w3.org/1999/02/22-rdf-syntax-ns#dirLangString')

>>> Triple(IRI("s1"), IRI("p1"), DataLiteral("a"))
Triple(s=IRI(string='s1'), p=IRI(string='p1'), o=DataLiteral(string='a', datatype=IRI(string='http://www.w3.org/2001/XMLSchema#string')))
>>>
```
Graphs are sets of triples:
```python
>>> g1 = set[Triple]()
>>> g1.add(Triple(IRI("s1"), IRI("p1"), DataLiteral("1")))
>>> g1.add(Triple(IRI("s1"), IRI("p1"), DataLiteral("2", datatype=IRI(f'{XSD}integer'))))

>>> g2 = set[Triple]()
>>> g2.add(Triple(IRI("s1"), IRI("p2"), DataLiteral("a")))
>>> g2.add(Triple(IRI("s2"), IRI("p1"), TextLiteral("b", language="en")))

>>> g = g1 | g2
>>> for triple in sorted(g): print(triple)
Triple(s=IRI(string='s1'), p=IRI(string='p1'), o=DataLiteral(string='1', datatype=IRI(string='http://www.w3.org/2001/XMLSchema#string')))
Triple(s=IRI(string='s1'), p=IRI(string='p1'), o=DataLiteral(string='2', datatype=IRI(string='http://www.w3.org/2001/XMLSchema#integer')))
Triple(s=IRI(string='s1'), p=IRI(string='p2'), o=DataLiteral(string='a', datatype=IRI(string='http://www.w3.org/2001/XMLSchema#string')))
Triple(s=IRI(string='s2'), p=IRI(string='p1'), o=TextLiteral(string='b', language='en', direction=None))
>>>
```

Interpretation:
```python
>>> from tinyrdf.interpretation import GraphInterpretation, InterpretationSpace

>>> meaning = GraphInterpretation()
>>> entity = meaning.get(IRI("urn:x-test:1"))
>>> entity.add(IRI("urn:x-test:ns:rel1"), meaning.get(IRI("urn:x-test:2")))
True
>>> assert entity.remove(IRI("urn:x-test:ns:rel1"), meaning.get(IRI("urn:x-test:2")))

>>> space = InterpretationSpace()
>>> space.interpret(g)
4
>>> meaning = space.main
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

>>> for s in meaning.get(DataLiteral("a")).get_subjects(IRI("p2")):
...     print(s.term)
IRI(string='s1')
>>>
```

Order of resources:
```python
>>> meaning = GraphInterpretation()
>>> for r in sorted(meaning.get(x) for x in [
...     DataLiteral('a'),
...     BNode('a'),
...     IRI('urn:x-a'),
...     TextLiteral('a', 'en'),
...     TripleTerm(IRI('a'), IRI('a'), IRI('a'))
... ]):
...     print(r.term)
IRI(string='urn:x-a')
BNode(string='a')
DataLiteral(string='a', datatype=IRI(string='http://www.w3.org/2001/XMLSchema#string'))
TextLiteral(string='a', language='en', direction=None)
TripleTerm(s=IRI(string='a'), p=IRI(string='a'), o=IRI(string='a'))
>>>
```

## Maintenance

```sh
$ python3 -m doctest README.md
```
