# Enterprise Architecture Governance Platform

Enterprise Governance Platform is a modular static architecture analysis toolkit for Python repositories. It provides configuration management, AST-based parsing, semantic dependency analysis, governance detectors, baseline comparison, and multiple output formats.

## Features

- Hierarchical configuration with env overrides and deep merge support
- AST-driven symbol and dependency extraction for Python
- Semantic graph and startup-flow heuristics
- Governance detectors for raw SQL, raw HTTP, bare except, missing validation, and duplicate registration
- Console, JSON, HTML, Markdown, JUnit XML, and SARIF reporting
- Deterministic fingerprint-based baseline comparison

## Quick Start

```bash
python -m pip install -e .
governance scan /path/to/repo
```