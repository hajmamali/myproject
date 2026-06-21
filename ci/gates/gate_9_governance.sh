#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

"${PROJECT_ROOT}/ci/first_step/gate_9_governance.sh"
    File: mahoun/rag/ultra_evaluation_system.py
    Pattern: 'SentenceTransformer('
    isBugCondition() returned True — violation still present.
    Lines: [337]
assert not True
FAILED tests/test_di_bug_condition.py::TestIsBugConditionProperty::test_violation_site_is_detectable[mahoun/pipelines/query_rewriter.py-from openai import OpenAI-Class C: hidden OpenAI import in query_rewriter] - AssertionError: BUG CONFIRMED — Class C: hidden OpenAI import in query_rewriter
    File: mahoun/pipelines/query_rewriter.py
    Pattern: 'from openai import OpenAI'
    isBugCondition() returned True — violation still present.
    Lines: [305]
assert not True
================================ 15 failed, 21 passed in 15.70s =================================
❯ 
~/De/KingMahouN main ?1 ❯            