from __future__ import annotations

from collections.abc import Sequence, Set
from typing import Iterable, Iterator, Mapping, NamedTuple, cast

from .terms import (IRI, RDF_REIFIES, RDF_FIRST, RDF_NIL, RDF_REST, RDF_TYPE,
                    BNode, Dataset, Graph, Literal, Quad, Reference, Term,
                    Triple)


class ModelSpace:
    default: Model
    named: Mapping[Reference, Model]

    _bnode_uniq: str
    _bnode_counter: int = 0

    def __init__(self, default: Model | None = None):
        self.default = default if default is not None else self._new_model()
        self.named = {}

        self._bnode_uniq = hex(id(self))[2:]
        self._bnode_counter = 0

    def _new_model(self) -> Model:
        return Model(self)

    def _new_bnode_id(self) -> str:
        self._bnode_counter += 1
        return f"b-{self._bnode_uniq}-{self._bnode_counter}"

    def new_blank(self, bnode_id: str | None = None) -> BNode:
        return BNode(bnode_id or self._new_bnode_id())

    def decode(self, datastream: Iterable[Triple | Quad]) -> int:
        i = 0
        for datum in datastream:
            if isinstance(datum, Triple):
                s, p, o = datum
                graph = self.default
            else:
                s, p, o, g = datum
                if g not in self.named:
                    assert isinstance(self.named, dict)
                    self.named[g] = self._new_model()
                graph = self.named[g]

            subj = graph.get(s)
            obj = graph.get(o)

            if graph.add(subj, p, obj):
                i += 1

        return i

    def encode(self) -> Iterator[Triple | Quad]:
        for triple in self.default.get_triples():
            yield triple

        for name, model in self.named.items():
            for s, p, o in model.get_triples():
                yield Quad(s, p, o, name)

    def __iter__(self) -> Iterator[Triple | Quad]:
        return self.encode()


class Model:
    space: ModelSpace

    _resources: dict[Term, Resource]

    def __init__(self, space: ModelSpace | None = None):
        self.space = space or self._new_space()
        self._resources = {}

    def _new_space(self) -> ModelSpace:
        return ModelSpace(self)

    def get(self, term: Term) -> Resource:
        resource = self._resources.get(term)
        if resource is None:
            resource = self._new_resource(term)
            self._resources[term] = resource

        return resource

    def _new_resource(self, term: Term) -> Resource:
        match term:
            case Triple(_):
                return Proposition(self, cast(Triple, term))
            case Literal(_):
                if term.language is not None:
                    return TextValue(self, term)
                else:
                    data = None  # TODO: values.parse(term)
                    return DataValue[object](self, term, data)
            case IRI(_):
                return IdentifiedResource(self, term)
            case BNode(_):
                return BlankResource(self, term)

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
            if isinstance(resource, DescribedResource):
                yield from resource.get_statements()

    def get_triples(self) -> Iterator[Triple]:
        for resource in self._resources.values():
            if not isinstance(resource, DescribedResource):
                continue
            for pred, objs in resource._description.items():
                if not isinstance(pred, IRI):
                    continue
                for obj in objs:
                    yield Triple(resource.ref, pred, obj.term)


class Statement(NamedTuple):
    subject: DescribedResource
    predicate: IdentifiedResource
    object: Resource

    def to_triple(self) -> Triple | None:
        return Triple(self.subject.ref, self.predicate.iri, self.object.term)

    def to_proposition(self) -> Proposition:
        triple = self.to_triple()
        assert triple is not None
        return cast(Proposition, self.subject.model.get(triple))


class Resource:
    model: Model
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
                return self.term < other.term

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


class DescribedResource(Resource):

    def __init__(self, model, ref: Reference):
        super().__init__(model, ref)

    @property
    def ref(self) -> Reference:
        return cast(Reference, self.term)

    def as_list(self) -> Sequence | None:
        items = []
        for first in self.get_objects(RDF_FIRST):
            items.append(first)
            for rest in self.get_objects(RDF_REST):
                if rest.term == RDF_NIL:
                    return items
                if not isinstance(rest, DescribedResource):
                    return None
                rlist = rest.as_list()
                if rlist is None:
                    return None
                items += rlist
                return items
                break
            else:
                return None
            break
        else:
            return None

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


class BlankResource(DescribedResource):

    def __init__(self, model: Model, bnode: BNode):
        super().__init__(model, bnode)

    @property
    def bnode(self) -> BNode:
        return cast(BNode, self.term)


class IdentifiedResource(DescribedResource):

    # _predicate_of_objects: dict[Term, Resource]  # pos index
    # _predicate_of_subjects: dict[Term, DescribedResource]  # pso index
    # def predicate_of_statements(s=None, o=None) -> Statement: ...

    def __init__(self, model: Model, iri: IRI):
        super().__init__(model, iri)

    @property
    def iri(self) -> IRI:
        return cast(IRI, self.term)


class Proposition(Resource):

    def __init__(self, model: Model, term: Triple):
        super().__init__(model, term)

    @property
    def triple(self) -> Triple:
        return cast(Triple, self.term)

    @property
    def subject(self) -> DescribedResource:
        return cast(DescribedResource, self.model.get(self.triple.s))

    @property
    def predicate(self) -> IdentifiedResource:
        return cast(IdentifiedResource, self.model.get(self.triple.p))

    @property
    def object(self) -> Resource:
        return self.model.get(self.triple.o)


class Value(Resource):

    term: Literal

    def __str__(self) -> str:
        return self.lexical_form

    @property
    def lexical_form(self) -> str:
        return self.term.string

    @property
    def type(self) -> IdentifiedResource:
        datatype = self.model.get(self.term.datatype)
        return cast(IdentifiedResource, datatype)


class DataValue[D: object](Value):

    data: D | None

    def __init__(
        self, model: Model, literal: Literal, data: D | None
    ):
        super().__init__(model, literal)
        self.data = data


class TextValue(Value):

    def __init__(self, model: Model, literal: Literal):
        assert literal.language is not None
        super().__init__(model, literal)

    @property
    def language(self) -> str:
        return cast(str, self.term.language)

    @property
    def direction(self) -> str | None:
        return self.term.direction


def _get_order_of(term: Term):
    match term:
        case IRI(_):
            return 1
        case BNode(_):
            return 2
        case Literal(_):
            return 3
        case Triple(_):
            return 4
