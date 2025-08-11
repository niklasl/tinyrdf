"""
Decode:

    >>> decode_literal(Literal('true', XSD_BOOLEAN))
    True
    >>> decode_literal(Literal('false', XSD_BOOLEAN))
    False

    >>> decode_literal(Literal('0', XSD_INTEGER))
    0
    >>> decode_literal(Literal('1', XSD_INTEGER))
    1

    >>> decode_literal(Literal('0.0', XSD_DOUBLE))
    0.0
    >>> decode_literal(Literal('1.0', XSD_DOUBLE))
    1.0

    >>> decode_literal(Literal('x', XSD_STRING))
    'x'
    >>> decode_literal(Literal('eA==', XSD_BASE64BINARY))
    b'x'

    >>> epoch = datetime.fromtimestamp(0, UTC)
    >>> assert decode_literal(Literal('1970-01-01T00:00:00+00:00', XSD_DATETIMESTAMP)) == epoch

    >>> assert decode_literal(Literal('1970-01-01', XSD_DATE)) == epoch.date()
    >>> assert decode_literal(Literal('00:00:00+00:00', XSD_TIME)) == epoch.timetz()

Encode:

    >>> assert encode_value(True) == Literal('true', XSD_BOOLEAN)
    >>> assert encode_value(False) == Literal('false', XSD_BOOLEAN)
    >>> assert encode_value(0) == Literal('0', XSD_INTEGER)
    >>> assert encode_value(1) == Literal('1', XSD_INTEGER)
    >>> assert encode_value(0.0) == Literal('0.0', XSD_DOUBLE)
    >>> assert encode_value(1.0) == Literal('1.0', XSD_DOUBLE)

    >>> assert encode_value('x') == Literal('x', XSD_STRING)
    >>> assert encode_value(b'x') == Literal('eA==', XSD_BASE64BINARY)

    >>> epoch = datetime.fromtimestamp(0, UTC)
    >>> assert encode_value(epoch) == Literal('1970-01-01T00:00:00+00:00', XSD_DATETIMESTAMP)

    >>> assert encode_value(epoch.date()) == Literal('1970-01-01', XSD_DATE)
    >>> assert encode_value(epoch.timetz()) == Literal('00:00:00+00:00', XSD_TIME)

    >>> assert encode_value(datetime.fromtimestamp(0)).datatype == XSD_DATETIME
"""

from __future__ import annotations

from base64 import b64decode, b64encode
from datetime import UTC, date, datetime, time
from typing import NamedTuple

from .terms import (IRI, RDF_DIRLANGSTRING, RDF_LANGSTRING, XSD, XSD_STRING,
                    Direction, Literal)

XSD_BOOLEAN = IRI(f"{XSD}boolean")
XSD_INTEGER = IRI(f"{XSD}integer")
XSD_DOUBLE = IRI(f"{XSD}double")
XSD_BASE64BINARY = IRI(f"{XSD}base64Binary")
XSD_DATE = IRI(f"{XSD}date")
XSD_TIME = IRI(f"{XSD}time")
XSD_DATETIME = IRI(f"{XSD}dateTime")
XSD_DATETIMESTAMP = IRI(f"{XSD}dateTimeStamp")
# ...

# See: <https://w3c.github.io/rdf-concepts/spec/#xsd-datatypes>
type RecognizedType = bool | int | float | str | datetime


def decode_literal(literal: Literal) -> object:
    return _from_lexical_by_type(literal.string, literal.datatype)


def encode_value(
    value: RecognizedType,
    language: str | None = None,
    direction: Direction | None = None,
) -> Literal:
    if language is not None:
        if not isinstance(value, str):
            raise TypeError(f"Value {value!r} must be a string when language is given.")

        return Literal.from_text(value, language, direction)

    s, dt = _to_lexical_and_type(value)
    return Literal(s, dt)  # value=value


DECODER_BY_TYPE = {
    XSD_BOOLEAN: lambda s: s == 'true' if s in ('true', 'false') else None,
    XSD_INTEGER: lambda s: int(s),
    XSD_DOUBLE: lambda s: float(s),
    XSD_STRING: lambda s: str(s),
    XSD_BASE64BINARY: lambda s: b64decode(s),
    XSD_DATETIME: lambda s: datetime.fromisoformat(s),
    XSD_DATETIMESTAMP: lambda s: datetime.fromisoformat(s),  # TODO: assert value.tzinfo
    XSD_DATE: lambda s: date.fromisoformat(s),
    XSD_TIME: lambda s: time.fromisoformat(s),
    # ...
}


def _from_lexical_by_type(lexical: str, datatype: IRI) -> object:
    decoder = DECODER_BY_TYPE.get(datatype)
    if decoder is None:
        raise NotImplementedError

    data = decoder(lexical)
    if data is None:
        raise ValueError(f"Unrecognized lexical value: {lexical!r}")

    return data


def _to_lexical_and_type(value: RecognizedType) -> tuple[str, IRI]:
    match value:
        case bool(_):
            return ('true' if value else 'false', XSD_BOOLEAN)
        case int(_):
            return (str(value), XSD_INTEGER)
        case float(_):
            return (str(value), XSD_DOUBLE)
        case str(_):
            return (value, XSD_STRING)
        case bytes(_):
            ascii = b64encode(value).decode('ascii')
            return (ascii, XSD_BASE64BINARY)
        case datetime():
            dt = XSD_DATETIME if value.tzinfo is None else XSD_DATETIMESTAMP
            return (value.isoformat(), dt)
        case date():
            return (value.isoformat(), XSD_DATE)
        case time():
            return (value.isoformat(), XSD_TIME)
        # ...

    raise ValueError(f"Unrecognized data value: {value!r}")
