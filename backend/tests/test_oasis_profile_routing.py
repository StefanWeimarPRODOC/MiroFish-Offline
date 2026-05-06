"""
Unit tests for MIR-27: Persona-routing heuristics.

Verifies that custom entity-types from ontology generation (e.g. DiabetesPatient,
NovaSulinSalesRep, Diabetologist) are correctly classified as individual or group
based on substring/suffix patterns, not just exact-match against the hardcoded lists.
"""

from unittest.mock import patch

import pytest

from app.services.oasis_profile_generator import OasisProfileGenerator


@pytest.fixture
def generator():
    """Build a generator without touching the network — we only need the routing."""
    with patch("app.services.oasis_profile_generator.OpenAI"):
        return OasisProfileGenerator(api_key="test", base_url="http://localhost:11434/v1")


# ----- Individual classification ---------------------------------------------

@pytest.mark.parametrize(
    "entity_type",
    [
        # Exact matches (existing behaviour)
        "person", "Person", "PERSON",
        "student", "expert", "journalist",
        # Substring matches (new MIR-27 behaviour)
        "DiabetesPatient",
        "NovaSulinSalesRep",
        "KOLDiabetology",
        "MedicalDoctor",
        "ChiefPhysician",
        "ResearchScientist",
        # Suffix matches
        "Diabetologist",
        "Cardiologist",
        "Specialist",
    ],
)
def test_is_individual_entity_true(generator, entity_type):
    assert generator._is_individual_entity(entity_type) is True


@pytest.mark.parametrize(
    "entity_type",
    [
        "Medication",     # neither individual nor group — falls through
        "Location",       # same
        "Hospital",       # group
        "DiabetesAG",     # group (suffix)
        "GKV-Verband",    # group (substring)
        "",               # empty
    ],
)
def test_is_individual_entity_false(generator, entity_type):
    assert generator._is_individual_entity(entity_type) is False


# ----- Group classification --------------------------------------------------

@pytest.mark.parametrize(
    "entity_type",
    [
        # Exact matches
        "organization", "ngo", "company",
        # Substring matches
        "GKV-Verband",
        "Krankenkasse",
        "UniversityHospital",
        "DiabetesKlinik",
        "MedTechCorp",
        "Sportverein",
        # Suffix matches
        "PharmaAG",
        "MedTechGmbH",
        "AcmeInc",
        "GlobalLtd",
    ],
)
def test_is_group_entity_true(generator, entity_type):
    assert generator._is_group_entity(entity_type) is True


@pytest.mark.parametrize(
    "entity_type",
    [
        "DiabetesPatient",  # individual
        "Diabetologist",    # individual
        "Person",
        "Medication",
        "",
    ],
)
def test_is_group_entity_false(generator, entity_type):
    assert generator._is_group_entity(entity_type) is False
