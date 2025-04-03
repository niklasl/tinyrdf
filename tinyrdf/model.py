from __future__ import annotations

from collections.abc import Sequence, Set
from typing import Final, Iterable, Iterator, Mapping, NamedTuple, cast

from .terms import (IRI, RDF_FIRST, RDF_NIL, RDF_REIFIES, RDF_REST, RDF_TYPE,
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
                model = self.default
            else:
                s, p, o, g = datum
                if g not in self.named:
                    assert isinstance(self.named, dict)
                    self.named[g] = self._new_model()
                model = self.named[g]

            subj = model.get(s)
            obj = model.get_object(o)

            if model.add(subj, p, obj):
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

    def get(self, ref: Reference) -> DescribedResource:
        return cast(DescribedResource, self.get_object(ref))

    def get_object(self, term: Term) -> Resource:
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

    def add(self, subj: DescribedResource, pred: IRI, obj: Resource) -> bool:
        if pred not in subj._description:
            subj._description[pred] = set()

        propositions = subj._description[pred]

        if obj in propositions:
            return False

        proposition = cast(
            Proposition, self.get_object(Triple(subj.term, pred, obj.term))
        )
        propositions.add(proposition)

        if pred not in obj._object_of:
            reverse_subjects = obj._object_of[pred] = set()
        else:
            reverse_subjects = obj._object_of[pred]

        reverse_subjects.add(proposition)

        return True

    def remove(self, subj: DescribedResource, pred: IRI, obj: Resource | None) -> bool:
        if pred not in subj._description:
            return False

        if obj is None:
            del subj._description[pred]
            return True

        proposition = cast(
            Proposition, self.get_object(Triple(subj.term, pred, obj.term))
        )
        propositions = subj._description[pred]
        if proposition in propositions:
            propositions.remove(proposition)

            subjs = obj._object_of.get(pred)
            if subjs is not None:
                subjs.remove(proposition)
                if len(subjs) == 0:
                    del obj._object_of[pred]

            return True
        else:
            return False

    def get_resources(self) -> Iterator[Resource]:
        return iter(self._resources.values())

    def get_subjects(self) -> Iterator[DescribedResource]:
        for resource in self.get_resources():
            if isinstance(resource, DescribedResource):
                yield resource

    def get_facts(self) -> Iterator[Proposition]:
        for resource in self.get_subjects():
            yield from resource.get_facts()

    def get_triples(self) -> Iterator[Triple]:
        for resource in self._resources.values():
            if not isinstance(resource, DescribedResource):
                continue
            for pred, propositions in resource._description.items():
                if not isinstance(pred, IRI):
                    continue
                for proposition in propositions:
                    yield proposition.term


class Resource:
    model: Model
    term: Term

    _object_of: dict[IRI, set[Proposition]]  # ops index

    def __init__(self, model, term: Term):
        self.model = model
        self.term = term
        self._object_of = dict()

    def __hash__(self):
        return hash(self.term)

    def __lt__(self, other: object) -> int:
        if isinstance(other, Resource):
            if type(self.term) == type(other.term):
                return self.term < other.term

            return _get_order_of(self.term) < _get_order_of(other.term)

        raise TypeError(f"'<' is not supported for instances of {type(other)!r}")

    def get_subjects(self, predicate: IRI) -> Iterator[Resource]:
        if predicate not in self._object_of:
            return
        for proposition in self._object_of[predicate]:
            yield proposition._subject


class DescribedResource(Resource):
    term: Reference

    _description: dict[IRI, set[Proposition]]  # spo index

    def __init__(self, model: Model, term: Reference):
        super().__init__(model, term)
        self._description = dict()

    def get_objects(self, predicate: IRI) -> Iterator[Resource]:
        for proposition in self.get_facts(predicate):
            yield proposition._object

    def get_facts(self, predicate: IRI | None = None) -> Iterator[Proposition]:
        if predicate is None:
            for pred, propositions in self._description.items():
                prop = self.model.get(pred)
                if isinstance(prop, IdentifiedResource):
                    yield from propositions
        elif predicate in self._description:
            yield from self._description[predicate]

    def add(self, pred: IRI, obj: Resource) -> bool:
        return self.model.add(self, pred, obj)

    def remove(self, pred: IRI, obj: Resource | None = None) -> bool:
        return self.model.remove(self, pred, obj)

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


class BlankResource(DescribedResource):
    term: BNode


class IdentifiedResource(DescribedResource):
    term: IRI

    _in_propositions_by_subject: dict[DescribedResource, Proposition]  # pso index
    _in_propositions_by_object: dict[Resource, Proposition]  # pos index
    # def predicate_of(s=None, o=None) -> Propositions: ...

    def __init__(self, model: Model, term: IRI):
        super().__init__(model, term)
        self._in_propositions_by_subject = {}
        self._in_propositions_by_object = {}


class Proposition(Resource):
    term: Triple

    _subject: Final[DescribedResource]
    _predicate: Final[IdentifiedResource]
    _object: Final[Resource]

    def __init__(self, model: Model, term: Triple):
        super().__init__(model, term)
        self._subject = self.model.get(self.term.s)
        self._predicate = cast(IdentifiedResource, self.model.get(self.term.p))
        self._object = self.model.get_object(self.term.o)

    @property
    def subject(self) -> DescribedResource:
        return self._subject

    @property
    def predicate(self) -> IdentifiedResource:
        return self._predicate

    @property
    def object(self) -> Resource:
        return self._object


class Value(Resource):
    term: Literal

    def __str__(self) -> str:
        return self.term.string

    @property
    def type(self) -> IdentifiedResource:
        datatype = self.model.get(self.term.datatype)
        return cast(IdentifiedResource, datatype)


class DataValue[D: object](Value):
    data: D | None

    def __init__(self, model: Model, literal: Literal, data: D | None):
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
