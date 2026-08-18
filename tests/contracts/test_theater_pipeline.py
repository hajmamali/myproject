import pytest
from mahoun.contracts.gate import evaluate_gate
from mahoun.contracts.coverage import generate_coverage
from mahoun.contracts.determinism_test import run_determinism_check
from mahoun.contracts.schema_validator import validate_schema

def test_gate_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        evaluate_gate("contracts", "coverage", 85)

def test_coverage_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        generate_coverage("contracts", "tests", "out.json")

def test_determinism_test_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        run_determinism_check(5)

def test_schema_validator_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        validate_schema("schema.json")
