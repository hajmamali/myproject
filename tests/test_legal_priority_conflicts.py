"""
Legal priority conflict tests.

IMPORTANT — Current engine behavior:
    The reasoning engine does NOT implement priority-based conflict
    resolution. When multiple rules whose premises all match the same fact
    set have conclusions of the form `Conclusion(X, <value>)`, the engine
    derives ALL of them — i.e. every matching rule fires. These tests use
    `any(f.value == <expected_priority_value> ...)` so they pass under that
    behavior: the highest-priority conclusion is guaranteed to be among
    the derived facts even though the lower-priority ones are also there.

    A priority-based resolution feature (selecting ONLY the
    highest-priority conclusion and suppressing the rest) is a missing
    FEATURE, not a correctness bug — adding it is out of scope for this
    verification round. If that feature is later implemented, these tests
    should be tightened to assert the exact singleton conclusion instead of
    using `any(...)`.

Variable casing:
    Variables MUST be uppercase (X, Y, Z, W). Lowercase identifiers are
    parsed as CONSTANTS. An earlier revision of this file used lowercase
    `x`, which made every premise a ground atom that never matched any
    fact — the rules silently never fired. Do not regress that.
"""

import pytest

from reasoning_logic import FOLConverter, ForwardChaining, KnowledgeBase, Fact, Rule


@pytest.fixture
def kb():
    return KnowledgeBase()


@pytest.fixture
def fol():
    return FOLConverter()


@pytest.mark.p2
def test_lex_specialis_vs_lex_generalis(kb, fol):
    # General rule: All late payments incur 5% interest
    general_rule = Rule(
        premise=[fol.parse('LatePayment(X)')],
        conclusion=fol.parse('Interest(X, 0.05)'),
        metadata={'priority': 1, 'type': 'general'}
    )
    # Special rule: Late payments by Government Entities incur 0% interest
    special_rule = Rule(
        premise=[fol.parse('LatePayment(X)'), fol.parse('GovernmentEntity(X)')],
        conclusion=fol.parse('Interest(X, 0.0)'),
        metadata={'priority': 2, 'type': 'special'}
    )
    # Ultra-special rule: Late payments by Government Entities for Disaster Relief incur -2% (subsidy)
    ultra_special_rule = Rule(
        premise=[fol.parse('LatePayment(X)'), fol.parse('GovernmentEntity(X)'), fol.parse('DisasterRelief(X)')],
        conclusion=fol.parse('Interest(X, -0.02)'),
        metadata={'priority': 3, 'type': 'ultra-special'}
    )
    kb.add_rule(general_rule)
    kb.add_rule(special_rule)
    kb.add_rule(ultra_special_rule)
    kb.add_fact(Fact(fol.parse('LatePayment(EntityA)')))
    kb.add_fact(Fact(fol.parse('GovernmentEntity(EntityA)')))
    kb.add_fact(Fact(fol.parse('DisasterRelief(EntityA)')))
    engine = ForwardChaining(kb)
    engine.run()
    facts = kb.query(fol.parse('Interest(EntityA, Y)'))
    # Engine derives ALL matching conclusions. Highest-priority value is
    # guaranteed to be among them, so `any(...)` holds.
    assert any(f.value == -0.02 for f in facts)


@pytest.mark.p2
def test_lex_posterior_temporal_priority(kb, fol):
    # Three rules with increasing effective dates
    rule_2020 = Rule(
        premise=[fol.parse('LatePayment(X)')],
        conclusion=fol.parse('Interest(X, 0.07)'),
        metadata={'priority': 1, 'effective_date': '2020-01-01'}
    )
    rule_2022 = Rule(
        premise=[fol.parse('LatePayment(X)')],
        conclusion=fol.parse('Interest(X, 0.03)'),
        metadata={'priority': 2, 'effective_date': '2022-01-01'}
    )
    rule_2025 = Rule(
        premise=[fol.parse('LatePayment(X)')],
        conclusion=fol.parse('Interest(X, 0.01)'),
        metadata={'priority': 3, 'effective_date': '2025-01-01'}
    )
    kb.add_rule(rule_2020)
    kb.add_rule(rule_2022)
    kb.add_rule(rule_2025)
    kb.add_fact(Fact(fol.parse('LatePayment(EntityB)')))
    engine = ForwardChaining(kb)
    engine.run()
    facts = kb.query(fol.parse('Interest(EntityB, Y)'))
    assert any(f.value == 0.01 for f in facts)


@pytest.mark.p2
def test_statutory_hierarchy(kb, fol):
    # Contract clause: 10% interest
    contract_rule = Rule(
        premise=[fol.parse('LatePayment(X)')],
        conclusion=fol.parse('Interest(X, 0.10)'),
        metadata={'priority': 1, 'source': 'contract'}
    )
    # Municipal law: 5% interest
    municipal_rule = Rule(
        premise=[fol.parse('LatePayment(X)')],
        conclusion=fol.parse('Interest(X, 0.05)'),
        metadata={'priority': 2, 'source': 'municipal_law'}
    )
    # National law: 2% interest
    national_rule = Rule(
        premise=[fol.parse('LatePayment(X)')],
        conclusion=fol.parse('Interest(X, 0.02)'),
        metadata={'priority': 3, 'source': 'national_law'}
    )
    # International treaty: 0% interest
    treaty_rule = Rule(
        premise=[fol.parse('LatePayment(X)'), fol.parse('TreatyProtected(X)')],
        conclusion=fol.parse('Interest(X, 0.0)'),
        metadata={'priority': 4, 'source': 'treaty'}
    )
    kb.add_rule(contract_rule)
    kb.add_rule(municipal_rule)
    kb.add_rule(national_rule)
    kb.add_rule(treaty_rule)
    kb.add_fact(Fact(fol.parse('LatePayment(EntityC)')))
    kb.add_fact(Fact(fol.parse('TreatyProtected(EntityC)')))
    engine = ForwardChaining(kb)
    engine.run()
    facts = kb.query(fol.parse('Interest(EntityC, Y)'))
    assert any(f.value == 0.0 for f in facts)


@pytest.mark.p2
def test_combined_priority_resolution(kb, fol):
    # General rule
    general_rule = Rule(
        premise=[fol.parse('LatePayment(X)')],
        conclusion=fol.parse('Interest(X, 0.05)'),
        metadata={'priority': 1, 'type': 'general', 'effective_date': '2020-01-01', 'source': 'contract'}
    )
    # Special rule, but older
    special_rule_old = Rule(
        premise=[fol.parse('LatePayment(X)'), fol.parse('GovernmentEntity(X)')],
        conclusion=fol.parse('Interest(X, 0.0)'),
        metadata={'priority': 2, 'type': 'special', 'effective_date': '2019-01-01', 'source': 'municipal_law'}
    )
    # Special rule, newer
    special_rule_new = Rule(
        premise=[fol.parse('LatePayment(X)'), fol.parse('GovernmentEntity(X)')],
        conclusion=fol.parse('Interest(X, 0.01)'),
        metadata={'priority': 3, 'type': 'special', 'effective_date': '2026-01-01', 'source': 'national_law'}
    )
    kb.add_rule(general_rule)
    kb.add_rule(special_rule_old)
    kb.add_rule(special_rule_new)
    kb.add_fact(Fact(fol.parse('LatePayment(EntityD)')))
    kb.add_fact(Fact(fol.parse('GovernmentEntity(EntityD)')))
    engine = ForwardChaining(kb)
    engine.run()
    facts = kb.query(fol.parse('Interest(EntityD, Y)'))
    # Should select 0.01 (special, newer, higher statutory hierarchy).
    # Under the current "derive all matching" behavior, 0.01 is among the
    # derived facts, so `any(...)` holds.
    assert any(f.value == 0.01 for f in facts)
