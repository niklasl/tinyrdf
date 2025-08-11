# TinyRDF

A tiny RDF library. Implements RDF 1.2.

## Example Usage

Graph terms:
```python
>>> from tinyrdf.terms import BNode, Graph, IRI, Literal, Triple, XSD

>>> IRI('s1')
IRI(string='s1')

>>> Literal.from_text("a")
Literal(string='a', datatype=IRI(string='http://www.w3.org/2001/XMLSchema#string'), language=None, direction=None)

>>> Literal("1", datatype=IRI(f'{XSD}integer'))
Literal(string='1', datatype=IRI(string='http://www.w3.org/2001/XMLSchema#integer'), language=None, direction=None)

>>> tl = Literal.from_text("a", language="en")
>>> tl
Literal(string='a', datatype=IRI(string='http://www.w3.org/1999/02/22-rdf-syntax-ns#langString'), language='en', direction=None)


>>> tld = Literal.from_text("b", language="en", direction="rtl")
>>> tld
Literal(string='b', datatype=IRI(string='http://www.w3.org/1999/02/22-rdf-syntax-ns#dirLangString'), language='en', direction='rtl')

>>> Triple(IRI("s1"), IRI("p1"), Literal.from_text("a"))
Triple(s=IRI(string='s1'), p=IRI(string='p1'), o=Literal(string='a', datatype=IRI(string='http://www.w3.org/2001/XMLSchema#string'), language=None, direction=None))
>>>
```
Graphs are sets of triples:
```python
>>> g1 = set[Triple]()
>>> g1.add(Triple(IRI("s1"), IRI("p1"), Literal.from_text("1")))
>>> g1.add(Triple(IRI("s1"), IRI("p1"), Literal("2", datatype=IRI(f'{XSD}integer'))))

>>> g2 = set[Triple]()
>>> g2.add(Triple(IRI("s1"), IRI("p2"), Literal.from_text("a")))
>>> g2.add(Triple(IRI("s2"), IRI("p1"), Literal.from_text("b", language="en")))

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
>>> from tinyrdf.model import Model, ModelSpace, Proposition

>>> space = ModelSpace()
>>> space.decode(g)
4
>>> model = space.default
>>> entity = model.about(IRI("s1"))
>>> assert entity is model.get(IRI("s1"))

>>> for o in sorted(entity.get_objects(IRI("p1")), key=lambda it: it.term):
...     print(o.term.string)
1
2

>>> for o in entity.get_objects(IRI("p2")):
...     print(o.term.string)
a

>>> for o in entity.get_objects(IRI("p3")):
...     print(o.term)

>>> for s in model.get(Literal.from_text("a")).get_subjects(IRI("p2")):
...     print(s.term)
IRI(string='s1')
>>>
```

Order of resources:
```python
>>> model = Model()
>>> for r in sorted(model.get(x) for x in [
...     Literal.from_text('a'),
...     BNode('a'),
...     IRI('urn:x-a'),
...     Literal.from_text('a', 'en'),
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

Resource Access and Modification:
```python
>>> model = Model()
>>> model is model.space.default
True

>>> entity = model.about(IRI("urn:x-test:1"))
>>> rel = IRI("urn:x-test:ns:rel1")
>>> other = model.about(IRI("urn:x-test:2"))

>>> entity.has(rel, other)
False

>>> entity.add(rel, other.term)

>>> entity.has(rel, other)
True

>>> entity.has(rel, other.term)
True

>>> entity.has(IRI("urn:x-test:ns:rel2"), other)
False

>>> next(entity.get_objects(rel)) is other
True
>>> for fact in entity.get_facts(): print(fact.term)
Triple(s=IRI(string='urn:x-test:1'), p=IRI(string='urn:x-test:ns:rel1'), o=IRI(string='urn:x-test:2'))

>>> next(other.get_subjects(rel)) is entity
True

>>> for propos in model.about(rel).predicate_of(): print(propos.term)
Triple(s=IRI(string='urn:x-test:1'), p=IRI(string='urn:x-test:ns:rel1'), o=IRI(string='urn:x-test:2'))

>>> for r in model.get_subjects(): print(r.term)
IRI(string='urn:x-test:1')

>>> for r in model.get_predicates(): print(r.term)
IRI(string='urn:x-test:ns:rel1')

>>> for r in model.get_objects(): print(r.term)
IRI(string='urn:x-test:2')

>>> for fact in sorted(model.get_facts()): print(fact.term)
Triple(s=IRI(string='urn:x-test:1'), p=IRI(string='urn:x-test:ns:rel1'), o=IRI(string='urn:x-test:2'))

>>> prp = model.get(Triple(entity.term, rel, other.term))
>>> isinstance(prp, Proposition)
True
>>> prp.is_fact()
True

>>> entity.remove(rel, IRI("urn:x-test:2"))

>>> list(entity.get_objects(rel))
[]
>>> list(other.get_subjects(rel))
[]
>>> list(entity.get_facts())
[]
>>> list(model.about(rel).predicate_of())
[]

>>> [r.term for r in sorted(model.get_subjects())]
[]

>>> [r.term for r in sorted(model.get_predicates())]
[]

>>> [r.term for r in sorted(model.get_objects())]
[]

>>>
```

Resources are "interned" once used, so even unrelated nodes are kept (as singletons) in the model.
```turtle
>>> for r in sorted(model.get_resources()): print(r.term)
IRI(string='urn:x-test:1')
IRI(string='urn:x-test:2')
IRI(string='urn:x-test:ns:rel1')
Triple(s=IRI(string='urn:x-test:1'), p=IRI(string='urn:x-test:ns:rel1'), o=IRI(string='urn:x-test:2'))

>>> prp = model.get(Triple(entity.term, IRI("urn:x-test:ns:rel2"), other.term))
>>> isinstance(prp, Proposition)
True
>>> prp.is_fact()
False

>>> for r in sorted(model.get_resources()): print(r.term)
IRI(string='urn:x-test:1')
IRI(string='urn:x-test:2')
IRI(string='urn:x-test:ns:rel1')
IRI(string='urn:x-test:ns:rel2')
Triple(s=IRI(string='urn:x-test:1'), p=IRI(string='urn:x-test:ns:rel1'), o=IRI(string='urn:x-test:2'))
Triple(s=IRI(string='urn:x-test:1'), p=IRI(string='urn:x-test:ns:rel2'), o=IRI(string='urn:x-test:2'))

>>>
```

## Maintenance

```sh
$ python3 -m doctest README.md
```
