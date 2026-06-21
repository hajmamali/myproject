# Installation & Usage Guide

## Quick Start

### 1. Install Dependencies
```bash
cd /home/haji/Desktop/Platform
source venv/bin/activate
pip install pytest pytest-asyncio
```

### 2. Run Tests

#### Option A: Run All Tests (Recommended)
```bash
cd /home/haji/Desktop/Platform
source venv/bin/activate
pytest first_step_ci_cd/ -v
```

#### Option B: Run Individual Test Files
```bash
# Import tests only
pytest first_step_ci_cd/test_1_imports.py -v

# Structure tests only
pytest first_step_ci_cd/test_2_structure.py -v

# Contract tests only
pytest first_step_ci_cd/test_3_contracts.py -v

# Light logic tests
pytest first_step_ci_cd/test_4_logic_light.py -v

# Anti-mock tests (proof of real implementation)
pytest first_step_ci_cd/test_5_anti_mock.py -v
```

#### Option C: Run the CI Script
```bash
cd /home/haji/Desktop/Platform
source venv/bin/activate
bash first_step_ci_cd/run_safe_ci.sh
```

### 3. Quick Test
```bash
# Quick test (<30 seconds)
cd /home/haji/Desktop/Platform
source venv/bin/activate
pytest first_step_ci_cd/ -q
```

---

## Test Results

### ✅ All Tests Passing

As of December 26, 2025:
- **Total Tests:** 137
- **Passed:** 137 (100%)
- **Failed:** 0
- **Execution Time:** ~27 seconds
- **Memory Usage:** < 100 MB
- **CPU Usage:** Low

---

## What is Tested

### 1. Import Integrity (18 tests)
- All modules import successfully
- No circular dependencies
- Required classes and functions exist

### 2. Structure Verification (33 tests)
- Classes have expected methods
- Proper inheritance hierarchy
- Correct dataclass structure

### 3. Contract Compliance (29 tests)
- Method signatures match specifications
- Async/sync methods are correctly defined
- Type hints are present

### 4. Light Logic (27 tests)
- Basic functionality works
- Configuration system works
- State management functions correctly

### 5. Anti-Mock Verification (30 tests)
- Functions are NOT placeholders
- Code has real logic (not just `pass`)
- Implementation complexity is sufficient

---

## Troubleshooting

### Issue: pytest not found
```bash
pip install pytest pytest-asyncio
```

### Issue: Module import errors
```bash
# Make sure you're in the project root
cd /home/haji/Desktop/Platform

# Activate venv
source venv/bin/activate
```

### Issue: Tests run slowly
This is normal - the first run loads all modules. Subsequent runs are faster.

---

## CI/CD Integration

### Pre-commit Hook
Add this to `.git/hooks/pre-commit`:
```bash
#!/bin/bash
cd /home/haji/Desktop/Platform
source venv/bin/activate
pytest first_step_ci_cd/ -q
```

### GitHub Actions (example)
```yaml
name: Reality Check CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install pytest pytest-asyncio pydantic numpy
      - name: Run tests
        run: |
          pytest first_step_ci_cd/ -v
```

---

## Next Steps

After this phase passes, consider:

1. **Phase 2:** Integration tests with mocked services
2. **Phase 3:** Performance benchmarks
3. **Phase 4:** Full E2E tests (requires more resources)

---

**Created:** December 26, 2025  
**Last Updated:** December 26, 2025  
**Status:** ✅ All Systems Operational

