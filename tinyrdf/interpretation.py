from __future__ import annotations

from collections.abc import Set
from typing import Iterable, Iterator, Mapping, NamedTuple, cast

from .terms import (IRI, RDF_REIFIES, RDF_TYPE, BNode, DataLiteral, Dataset,
                    Graph, Literal, Quad, Reference, Term, TextLiteral, Triple,
                    TripleTerm)

type NominalResource = NamedResource | IdentifiedResource
type StructuredResource = Proposition | Value


class InterpretationSpace:
    main: GraphInterpretation
    named: Mapping[Reference, GraphInterpretation]

    _bnode_uniq: str
    _bnode_counter: int = 0

    def __init__(self, main: GraphInterpretation | None = None):
        self.main = main if main is not None else self._new_intrepretation()
        self.named = {}

        self._bnode_uniq = hex(id(self))[2:]
        self._bnode_counter = 0

    def _new_intrepretation(self) -> GraphInterpretation:
        return GraphInterpretation(self)

    def new_bnode_id(self) -> str:
        self._bnode_counter += 1
        return f"b-{self._bnode_uniq}-{self._bnode_counter}"

    def interpret(self, datastream: Iterable[Triple | Quad]) -> int:
        i = 0
        for datum in datastream:
            if isinstance(datum, Triple):
                s, p, o = datum
                graph = self.main
            else:
                s, p, o, g = datum
                if g not in self.named:
                    assert isinstance(self.named, dict)
                    self.named[g] = self._new_intrepretation()
                graph = self.named[g]

            subj = graph.get(s)
            obj = graph.get(o)

            if graph.add(subj, p, obj):
                i += 1

        return i

    def represent(self) -> Iterator[Triple | Quad]:
        for triple in self.main.get_triples():
            yield triple

        for name, model in self.named.items():
            for s, p, o in model.get_triples():
                yield Quad(s, p, o, name)

    def __iter__(self) -> Iterator[Triple | Quad]:
        return self.represent()


class GraphInterpretation:
    space: InterpretationSpace

    _resources: dict[Term, Resource]

    def __init__(self, space: InterpretationSpace | None = None):
        self.space = space or self._new_space()
        self._resources = {}

    def _new_space(self) -> InterpretationSpace:
        return InterpretationSpace(self)

    def get(self, term: Term) -> Resource:
        resource = self._resources.get(term)
        if resource is None:
            resource = self._new_resource(term)
            self._resources[term] = resource

        return resource

    def _new_resource(self, term: Term) -> Resource:
        match term:
            case TripleTerm(_):
                return Proposition(self, cast(TripleTerm, term))
            case DataLiteral(_):
                return DataValue(self, term)
            case TextLiteral(_):
                return TextValue(self, term)
            case IRI(_):
                return IdentifiedResource(self, cast(IRI, term))
            case BNode(_):
                return NamedResource(self, cast(Reference, term))

    def add(self, subj: Resource, pred: Reference, obj: Resource) -> bool:
        if pred not in subj._description:
            subj._description[pred] = set()

        objects = subj._description[pred]

        if obj in objects:
            return False
        else:
            objects.add(obj)

            if pred not in obj._object_of:
                reverse_subjects = obj._object_of[pred] = set()
            else:
                reverse_subjects = obj._object_of[pred]

            reverse_subjects.add(subj)

            return True

    def remove(self, subj: Resource, pred: Reference, obj: Resource | None) -> bool:
        if pred not in subj._description:
            return False

        if obj is None:
            del subj._description[pred]
            return True

        objects = subj._description[pred]
        if obj in objects:
            objects.remove(obj)
            return True
        else:
            return False

    def get_resources(self) -> Iterator[Resource]:
        return iter(self._resources.values())

    def get_statements(self) -> Iterator[Statement]:
        for resource in self.get_resources():
            if isinstance(resource, NamedResource):
                yield from resource.get_statements()

    def get_triples(self) -> Iterator[Triple]:
        for resource in self._resources.values():
            if not isinstance(resource, NamedResource):
                continue
            for pred, objs in resource._description.items():
                if not isinstance(pred, IRI):
                    continue
                for obj in objs:
                    yield Triple(resource.ref, pred, obj.term)


class Statement(NamedTuple):
    subject: NamedResource
    predicate: IdentifiedResource
    object: Resource

    def to_proposition(self) -> Proposition:
        return Proposition(self.subject.model, cast(TripleTerm, self.to_triple()))

    def to_triple(self) -> Triple | None:
        s = self.subject

        if not isinstance(s, NamedResource):
            return None

        p = self.predicate.ref

        if not isinstance(p, IRI):
            return None

        return Triple(s.ref, p, self.object.term)


class Resource:
    model: GraphInterpretation
    term: Term

    _description: dict[Reference, set[Resource]]  # spo index
    _object_of: dict[Reference, set[Resource]]  # ops index

    def __init__(self, model, term: Term):
        self.model = model
        self.term = term
        self._description = dict()
        self._object_of = dict()

    def __hash__(self):
        return hash(self.term)

    def __lt__(self, other: object) -> int:
        if isinstance(other, Resource):
            if type(self.term) == type(other.term):
                return self.term < other.term  # type: ignore[operator]

            return _get_order_of(self.term) < _get_order_of(other.term)

        raise TypeError(f"'<' is not supported for instances of {type(other)!r}")

    def get_objects(self, predicate: Reference) -> Set[Resource]:
        return self._description.get(predicate) or set()

    def get_subjects(self, predicate: Reference) -> Set[Resource]:
        return self._object_of.get(predicate) or set()

    def add(self, pred: IRI, obj: Resource) -> bool:
        return self.model.add(self, pred, obj)

    def remove(self, pred: IRI, obj: Resource | None = None) -> bool:
        return self.model.remove(self, pred, obj)


class NamedResource(Resource):

    def __init__(self, model, ref: Reference):
        super().__init__(model, ref)

    @property
    def ref(self) -> Reference:
        return cast(Reference, self.term)

    def _new_statement(self, p: IdentifiedResource, o: Resource) -> Statement:
        return Statement(self, p, o)

    def get_statements(self, predicate: Reference | None = None) -> Iterator[Statement]:
        if predicate is None:
            for pred, objects in self._description.items():
                prop = self.model.get(pred)
                if isinstance(prop, IdentifiedResource):
                    for obj in objects:
                        yield self._new_statement(prop, obj)
        else:
            prop = self.model.get(predicate)
            if isinstance(prop, IdentifiedResource):
                for obj in self._description[predicate]:
                    yield self._new_statement(prop, obj)


class IdentifiedResource(NamedResource):

    def __init__(self, model: GraphInterpretation, name: IRI):
        super().__init__(model, name)

    @property
    def iri(self) -> IRI:
        return cast(IRI, self.term)


class Proposition(Resource):

    term: TripleTerm

    def __init__(self, model: GraphInterpretation, term: TripleTerm):
        super().__init__(model, term)

    @property
    def subject(self) -> NamedResource:
        return cast(NamedResource, self.model.get(self.term.s))

    @property
    def predicate(self) -> IdentifiedResource:
        return cast(IdentifiedResource, self.model.get(self.term.p))

    @property
    def object(self) -> Resource:
        return self.model.get(self.term.o)


class Value(Resource):

    term: Literal


class DataValue(Value):

    term: DataLiteral

    @property
    def type(self) -> IdentifiedResource:
        datatype = self.model.get(self.term.datatype)
        return cast(IdentifiedResource, datatype)


class TextValue(Value):

    term: TextLiteral

    def __init__(self, model: GraphInterpretation, literal: TextLiteral):
        super().__init__(model, literal)


def _get_order_of(term: Term):
    match term:
        case IRI(_):
            return 1
        case BNode(_):
            return 2
        case DataLiteral(_):
            return 3
        case TextLiteral(_):
            return 4
        case TripleTerm(_):
            return 5
