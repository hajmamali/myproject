# Mahoun API Reference

## Core Models

### LegalDocument
```python
from mahoun.core.models import LegalDocument

doc = LegalDocument(
    id="doc-1",
    text="Document content",
    doc_type=LegalDocType.LAW
)
```

### ReasoningResult
```python
from mahoun.core.models import ReasoningResult

result = ReasoningResult(
    question="Q",
    context="C",
    facts=["F1"],
    reasoning_chain=[],
    causal_chain=[],
    primary_cause=None,
    final_answer="A",
    confidence=0.8,
    supporting_evidence=["E1"],
    evidence_strength="strong"
)
```

## Schemas

### VerdictStruct
Complete structured verdict (L2 Schema).

```python
from mahoun.schemas.legal_struct_schema import VerdictStruct

verdict = VerdictStruct(
    case_meta=CaseMeta(...),
    parties=Parties(...),
    claims=Claims(...)
)
```

### TextDocument
```python
from mahoun.schemas.text_schema import TextDocument

doc = TextDocument(
    content="text",
    metadata={}
)
```

## Ledger

### LedgerEntry
```python
from mahoun.ledger.models import LedgerEntry

entry = LedgerEntry(
    entry_id="e1",
    timestamp=datetime.now(),
    event_type="verdict",
    data={}
)
```

## Invariants

7 core invariants (EL-I1 to EL-I7):
- EL-I1: 100% groundedness
- EL-I2: Hash chain integrity
- EL-I3: Immutability
- EL-I4: Timestamp monotonicity
- EL-I5: Evidence completeness
- EL-I6: Contradiction detection
- EL-I7: Privacy preservation
