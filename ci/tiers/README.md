# MAHOUN Test Execution Tiers

Four execution tiers classify tests by criticality and runtime budget.

| Tier | Target Runtime | Schedule | Scope |
|------|----------------|----------|-------|
| P0 | < 3 min | Every PR | governance, contracts, determinism, fortress, ledger |
| P1 | < 10 min | Every PR | P0 + core integration, reasoning, golden path |
| P2 | < 30 min | Pre-merge | P1 + graph, rag, comprehensive/property tests |
| P3 | Nightly | Nightly | Full `tests/` suite |

## Usage

```bash
# P0 — fast critical gate
./ci/tiers/p0_critical.sh

# P1 — core integration
./ci/tiers/p1_integration.sh

# P2 — extended validation
./ci/tiers/p2_extended.sh

# P3 — full nightly suite
./ci/tiers/p3_full.sh
```

## Environment

All tiers set:

- `PYTHONHASHSEED=0`
- `MAHOUN_NO_EXTERNAL_CALLS=1`
- `MAHOUN_TEST_MODE=1`
