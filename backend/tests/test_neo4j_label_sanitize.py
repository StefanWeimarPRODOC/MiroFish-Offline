"""
Unit tests for MIR-31: Cypher-label sanitization.

Verifies that _sanitize_label normalizes labels with diacritics, separators, and
leading digits into Cypher-safe identifiers — and rejects only inputs that have
no usable characters left after stripping.
"""

import pytest

from app.storage.neo4j_storage import _sanitize_label


# ----- Valid normalisations --------------------------------------------------

@pytest.mark.parametrize(
    "raw, expected",
    [
        # No-op: already valid Cypher identifier
        ("Patient", "Patient"),
        ("Entity", "Entity"),
        # Separator handling: dash, slash, whitespace, backslash, tab
        ("GKV-Verband", "GKV_Verband"),
        ("Medication/Drug", "Medication_Drug"),
        ("foo bar baz", "foo_bar_baz"),
        ("foo\tbar", "foo_bar"),
        ("foo\\bar", "foo_bar"),
        # Diacritics: German umlauts + sharp-s
        ("Müller", "Mueller"),
        ("Größe", "Groesse"),
        ("Ärzteverband", "Aerzteverband"),
        # Diacritics: other European accents
        ("Café", "Cafe"),
        ("Señor", "Senor"),
        # Combined: diacritics + separator
        ("Müller-Verein", "Mueller_Verein"),
        ("Größeres Verband", "Groesseres_Verband"),
        # Leading digit gets L_ prefix
        ("123abc", "L_123abc"),
        ("9Lives", "L_9Lives"),
        # Underscore is not isalpha() → also gets prefixed (current behaviour)
        ("_internal", "L__internal"),
    ],
)
def test_sanitize_label_normalizes(raw, expected):
    assert _sanitize_label(raw) == expected


# ----- Rejected inputs -------------------------------------------------------

@pytest.mark.parametrize(
    "raw",
    [
        None,        # None input
        "",          # empty string
        "   ",       # whitespace only — strip leaves nothing
        "//",        # only separators → after sub becomes "_", but wait: see below
    ],
)
def test_sanitize_label_returns_none(raw):
    # Note: "//" becomes "_" after separator-replace, which IS a safe char,
    # so it does NOT return None — see test_sanitize_label_separator_only_becomes_underscore.
    # This test only covers genuinely empty inputs.
    if raw == "//":
        pytest.skip("see separate test")
    assert _sanitize_label(raw) is None


def test_sanitize_label_only_separators_normalize_to_underscore():
    """Edge case: pure separators collapse to a single underscore, then get L_ prefix."""
    # "/" is in [\s/\\\-]+ → replaced with "_". "_" is not isalpha → prefixed with L_.
    assert _sanitize_label("//") == "L__"
    assert _sanitize_label("---") == "L__"


def test_sanitize_label_only_unsafe_chars_returns_none():
    """Inputs with chars that don't survive any pipeline stage → None."""
    # "!" is not in separators and not in [A-Za-z0-9_] → stripped. Result: empty → None.
    assert _sanitize_label("!!!") is None
    assert _sanitize_label("@#$") is None


# ----- Cypher injection safety ----------------------------------------------

@pytest.mark.parametrize(
    "raw",
    [
        "Foo`); DROP TABLE",
        "Bar' OR '1'='1",
        "Baz`{",
        "Label;DELETE",
    ],
)
def test_sanitize_label_strips_injection_chars(raw):
    """All non-[A-Za-z0-9_] characters must be stripped — no backticks, semicolons, quotes."""
    result = _sanitize_label(raw)
    assert result is not None
    assert all(c.isalnum() or c == "_" for c in result)
