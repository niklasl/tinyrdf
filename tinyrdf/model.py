from __future__ import annotations

from collections.abc import Sequence, Set
from typing import Final, Iterable, Iterator, Mapping, NamedTuple, cast

from .terms import (IRI, RDF_FIRST, RDF_NIL, RDF_REIFIES, RDF_REST, RDF_TYPE,
                    BNode, Dataset, Graph, Literal, Quad, Reference, Term,
                    Triple)


class ModelSpace:
    default: Model
    named: Mapping[Reference, Model]

    _bnode_prefix: str
    _bnode_counter: int = 0

    def __init__(self, default: Model | None = None, bnode_prefix: str | None = None):
        self.default = default if default is not None else self._new_model()
        self.named = {}

        self._bnode_prefix = (
            f"b-{hex(id(self))[2:]}-" if bnode_prefix is None else bnode_prefix
        )
        self._bnode_counter = 0

    def _new_model(self) -> Model:
        return Model(self)

    def _new_bnode_id(self) -> str:
        self._bnode_counter += 1
        return f"{self._bnode_prefix}{self._bnode_counter}"

    def new_bnode(self, bnode_id: str | None = None) -> BNode:
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

            subj = model.about(s)
            obj = model.get(o)

            if model.add(subj, p, obj):
                i += 1

        return i

    def encode(self) -> Iterator[Triple | Quad]:
        for fact in self.default.get_facts():
            yield fact.term

        for name, model in self.named.items():
            for triple in model.get_facts():
                s, p, o = triple.term
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
                return Identified(self, term)
            case BNode(_):
                return Blank(self, term)

    def get(self, term: Term) -> Resource:
        resource = self._resources.get(term)
        if resource is None:
            resource = self._new_resource(term)
            self._resources[term] = resource

        return resource

    def about(self, ref: Reference) -> Described:
        return cast(Described, self.get(ref))

    def new_blank(self) -> Blank:
        return cast(Blank, self.get(self.space.new_bnode()))

    def _get_proposition(self, s: Reference, p: IRI, o: Term):
        return cast(Proposition, self.get(Triple(s, p, o)))

    def add(self, subj: Described, pred: IRI, obj: Resource) -> bool:
        if pred not in subj._description:
            subj._description[pred] = set()

        propositions = subj._description[pred]
        proposition = self._get_proposition(subj.term, pred, obj.term)

        if proposition in propositions:
            return False

        propositions.add(proposition)

        prop = cast(Identified, self.about(pred))
        prop._predicate_of.add(proposition)

        if pred not in obj._object_of:
            reverse_subjects = obj._object_of[pred] = set()
        else:
            reverse_subjects = obj._object_of[pred]

        reverse_subjects.add(proposition)

        return True

    def remove(self, subj: Described, pred: IRI, obj: Resource) -> bool:
        if pred not in subj._description:
            return False

        propositions = subj._description[pred]

        proposition = self._get_proposition(subj.term, pred, obj.term)

        if proposition not in propositions:
            return False

        #forget = True

        propositions.remove(proposition)
        #if forget:
        #    del self._resources[proposition.term]

        if len(propositions) == 0:
            del subj._description[pred]

        #if forget and len(subj._description) == 0:
        #    del self._resources[subj.term]

        prop = cast(Identified, self.about(pred))
        prop._predicate_of.remove(proposition)

        #if forget and len(prop._predicate_of) == 0:
        #    del self._resources[prop.term]

        subjs = obj._object_of.get(pred)
        if subjs is not None:
            subjs.remove(proposition)
            if len(subjs) == 0:
                del obj._object_of[pred]
            #if forget and len(obj._object_of) == 0:
            #    del self._resources[obj.term]

        return True

    def get_resources(self) -> Iterator[Resource]:
        return iter(self._resources.values())

    def get_subjects(self) -> Iterator[Described]:
        for resource in self.get_resources():
            if isinstance(resource, Described):
                if len(resource._description):
                    yield resource

    def get_predicates(self) -> Iterator[Identified]:
        for resource in self.get_resources():
            if isinstance(resource, Identified):
                if len(resource._predicate_of):
                    yield resource

    def get_objects(self) -> Iterator[Resource]:
        for resource in self.get_resources():
            if len(resource._object_of):
                yield resource

    def get_facts(self) -> Iterator[Proposition]:
        for resource in self.get_subjects():
            yield from resource.get_facts()


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

        raise TypeError(
            f"'<' not supported between instances of {type(self)!r} and {type(other)!r}"
        )

    def get_subjects(self, predicate: IRI) -> Iterator[Resource]:
        if predicate not in self._object_of:
            return
        for proposition in self._object_of[predicate]:
            yield proposition._subject

    def _deref(self, obj: Resource | Term) -> Resource:
        return (
            self.model.get(obj)
            if isinstance(obj, (IRI, BNode, Literal, Triple))
            else obj
        )


class Described(Resource):
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
                yield from propositions
        elif predicate in self._description:
            yield from self._description[predicate]

    def add(self, pred: IRI, obj: Resource | Term) -> None:
        self.model.add(self, pred, self._deref(obj))

    def has(self, pred: IRI, obj: Resource | Term) -> bool:
        if pred in self._description:
            o = obj.term if isinstance(obj, Resource) else obj
            return Triple(self.term, pred, o) in self.model._resources
        else:
            return False

    def remove(self, pred: IRI, obj: Resource | Term) -> None:
        self.model.remove(self, pred, self._deref(obj))

    def add_list(self, pred: IRI, items: Sequence[Resource | Term]) -> None:
        cons = self.model.new_blank()
        self.add(pred, cons)

        prev_cons: Described | None = None
        for item in items:
            if prev_cons:
                cons = self.model.new_blank()
                prev_cons.add(RDF_REST, cons)
            cons.add(RDF_FIRST, item)
            prev_cons = cons

        if prev_cons is not None:
            prev_cons.add(RDF_REST, self.model.about(RDF_NIL))


class Blank(Described):
    term: BNode

    def as_list(self) -> Sequence | None:
        items = []
        for first in self.get_objects(RDF_FIRST):
            items.append(first)
            for rest in self.get_objects(RDF_REST):
                if rest.term == RDF_NIL:
                    return items
                if not isinstance(rest, Blank):
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


class Identified(Described):
    term: IRI

    _predicate_of: set[Proposition]  # p index

    def __init__(self, model: Model, term: IRI):
        super().__init__(model, term)
        self._predicate_of = set()

    def predicate_of(self) -> Iterator[Proposition]:
        for proposition in self._predicate_of:
            yield proposition


class Proposition(Resource):
    term: Triple

    _subject: Final[Described]
    _predicate: Final[Identified]
    _object: Final[Resource]

    def __init__(self, model: Model, term: Triple):
        super().__init__(model, term)
        self._subject = self.model.about(self.term.s)
        self._predicate = cast(Identified, self.model.get(self.term.p))
        self._object = self.model.get(self.term.o)

    @property
    def subject(self) -> Described:
        return self._subject

    @property
    def predicate(self) -> Identified:
        return self._predicate

    @property
    def object(self) -> Resource:
        return self._object

    def is_fact(self) -> bool:
        return self._subject.has(self._predicate.term, self._object)


class Value(Resource):
    term: Literal

    def __str__(self) -> str:
        return self.term.string

    @property
    def type(self) -> Identified:
        datatype = self.model.about(self.term.datatype)
        return cast(Identified, datatype)


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
