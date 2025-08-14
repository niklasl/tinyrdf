from __future__ import annotations

from collections.abc import Set
from typing import Literal as Exactly
from typing import NamedTuple

type Term = Basic | Triple  # RDF12
type Basic = Subject | Literal
type Subject = IRI | BNode

Direction = Exactly['ltr'] | Exactly['rtl']  # RDF12
LTR: Direction = 'ltr'
RTL: Direction = 'rtl'


class IRI(NamedTuple):
    string: str


class BNode(NamedTuple):
    string: str


class Literal(NamedTuple):
    string: str
    datatype: IRI
    language: str | None = None
    direction: Direction | None = None

    @classmethod
    def from_text(
        cls,
        string: str,
        language: str | None = None,
        direction: Direction | None = None,
    ) -> Literal:
        if language is None:
            return cls(string, XSD_STRING)

        datatype = RDF_DIRLANGSTRING if direction else RDF_LANGSTRING
        return cls(string, datatype, language, direction)


class Triple(NamedTuple):
    s: Subject
    p: IRI
    o: Term


class Quad(NamedTuple):
    s: Subject
    p: IRI
    o: Term
    g: Subject


type Graph = Set[Triple]
type Dataset = Set[Triple | Quad]


RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDF_FIRST = IRI(f"{RDF}first")
RDF_NIL = IRI(f"{RDF}nil")
RDF_REST = IRI(f"{RDF}rest")
RDF_TYPE = IRI(f"{RDF}type")
RDF_REIFIES = IRI(f"{RDF}reifies")  # RDF12
RDF_LANGSTRING = IRI(f"{RDF}langString")  # RDF12
RDF_DIRLANGSTRING = IRI(f"{RDF}dirLangString")  # RDF12

XSD = "http://www.w3.org/2001/XMLSchema#"
XSD_STRING = IRI(f"{XSD}string")
