# Mypy Non-Regression System

## 📋 Overview

This directory contains a **baseline-driven, non-regression** mypy checking system.

**Key principle:** CI will **NOT fail** if existing mypy errors remain, but **WILL fail** if NEW errors are introduced.

## 🗂️ Files

- **`baseline.txt`** - Snapshot of current mypy errors (authoritative)
- **`run_mypy.sh`** - Runs mypy with stable, parseable output
- **`check_mypy_non_regression.py`** - Compares current vs baseline; fails on new errors
- **`README.md`** - This file

## 🚀 Usage

### Check for new errors (CI / local)

```bash
# From project root
python ci/mypy/check_mypy_non_regression.py
```

**Exit codes:**
- `0` - No new errors (pass)
- `1` - New errors detected (fail)
- `2` - Configuration/runtime error

### Update baseline (after intentional fixes)

After fixing mypy errors, update the baseline to reflect the new state:

```bash
python ci/mypy/check_mypy_non_regression.py --update-baseline
```

**When to update baseline:**
- ✅ After fixing mypy errors (improvements)
- ✅ After intentional refactors that change type signatures
- ❌ **NOT** to bypass failing CI checks from new bugs!

### Run mypy manually

To see full mypy output:

```bash
bash ci/mypy/run_mypy.sh
# Or equivalently:
mypy mahoun/ api/ --config-file=mypy.ini
```

## 🎯 Non-Regression Logic

### What counts as a "new error"?

An error line in current output that does NOT appear in baseline.

**Error format:**
```
filename.py:123: error: Message here  [error-code]
```

**Normalization:**
- Strips column numbers (`:45` → ignored)
- Uses basename only (`mahoun/core/foo.py` → `foo.py`)
- Sorts errors for deterministic comparison

**Ignored:**
- Summary lines (e.g., "Found X errors in Y files")
- Path differences across systems

### Why normalize to basename?

**Stability:** Different CI runners or local setups may have different absolute paths.  
By using basename + line number, we get stable, portable error fingerprints.

## 📊 Baseline Management

### How often to update?

- **After each PR that fixes mypy errors** - Update baseline to track progress
- **Not every commit** - Only when type safety actually improves

### Baseline is NOT a "cheat"

The baseline system is designed to:
- ✅ **Prevent regressions** (new bugs)
- ✅ **Track gradual improvement** (shrinking baseline)
- ❌ **NOT hide problems** (all errors are in baseline.txt, visible to all)

### Tracking progress

```bash
# See error trend over time
git log --oneline -p -- ci/mypy/baseline.txt | grep "^[-+]" | grep "error:" | wc -l
```

## 🔧 Integration with CI

See `.github/workflows/ci.yml` for how this is wired into GitHub Actions.

**Key points:**
- Runs on every PR and push to main
- Fast (< 30 seconds typical)
- Deterministic (same code → same result)

## 🎓 Type Safety Philosophy

**"Ratchet" approach:**
1. Start with current state (811 errors)
2. Fix errors incrementally
3. Update baseline after each improvement
4. **Never allow regression**

Over time, baseline shrinks → 0 errors → full type safety! 🎯

## 📞 Troubleshooting

### "New errors" but I didn't change anything!

**Possible causes:**
1. Dependency update changed type stubs
2. Mypy version changed
3. Implicit type narrowing changed in Python

**Solution:** Review errors carefully. If legitimate, fix them. If false positive, consider `# type: ignore` with comment.

### CI passes locally but fails in GitHub Actions

**Possible causes:**
1. Different mypy version
2. Different Python version
3. Baseline out of sync

**Solution:** Ensure baseline is committed. Run exact mypy version as CI.

### Too many errors to fix at once!

**Strategy:**
1. Fix high-value errors first (`[valid-type]`, `[var-annotated]`, `[attr-defined]` in core)
2. Update baseline
3. Repeat

**Don't try to fix all 811 at once!** Incremental progress is sustainable progress.

---

**Last updated:** $(date)
**Baseline error count:** $(wc -l < baseline.txt)

