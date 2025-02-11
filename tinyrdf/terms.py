from typing import NamedTuple


class IRI(NamedTuple):
    string: str


RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
XSD = "http://www.w3.org/2001/XMLSchema#"

RDF_TYPE = IRI(RDF + "type")
RDF_REIFIES = IRI(RDF + "reifies")  # RDF12
RDF_LANGSTRING = IRI(RDF + "langString")  # RDF12
RDF_DIRLANGSTRING = IRI(RDF + "dirLangString")  # RDF12

XSD_STRING = IRI(XSD + "string")

type Term = Reference | Structure
type Reference = IRI | BNode
type Structure = Literal | TripleTerm
type Literal = DataLiteral | TextLiteral

type Graph = set[Triple]
type Dataset = set[Triple | Quad]


class BNode(NamedTuple):
    string: str


class DataLiteral(NamedTuple):
    string: str
    datatype: IRI = XSD_STRING


class TextLiteral(NamedTuple):
    string: str
    language: str
    direction: str | None = None  # RDF12

    @property
    def datatype(self):
        return RDF_DIRLANGSTRING if self.direction else RDF_LANGSTRING


class TripleTerm(NamedTuple):  # RDF12
    s: Reference
    p: IRI
    o: Term


class Triple(NamedTuple):
    s: Reference
    p: IRI
    o: Term


class Quad(NamedTuple):
    s: Reference
    p: IRI
    o: Term
    g: Reference
