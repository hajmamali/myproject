# MAHOUN IMPORT GRAPH REPORT
Date: 2026-05-25

## Production Import Surface for Graph/Neo4j
- mahoun/graph/neo4j/connection.py (canonical, imports nothing suspicious)
- mahoun/core/governance/* (enforcement)
- All other neo4j usage should route through above.

## Actual Import Graph for Driver Creation (Non-Canonical)
1. tests/fixtures/seed_data.py -> direct "from neo4j import GraphDatabase"
2. mahoun/graph/gnn/gnn_graph_builder.py -> direct import + driver
3. mahoun/graph/graph_query_service.py -> direct import + driver
4. api/database.py -> from neo4j import AsyncGraphDatabase
5. mahoun/reasoning/kg_adapters.py -> direct import
6. mahoun/infrastructure/health/checker.py and integrity_probe.py -> direct
7. Various tests and scripts

## Dynamic / Reflection Imports
- importlib.import_module used for:
  - guardrails (hardened)
  - switchboard ultra registration (current modules)
- No importlib or spec_from_file_location targeting /archive, /backup, .kilo/worktrees, or legacy paths.
- No __import__ with variable paths from untrusted input.

## Archive / Legacy Reachability via Import
- Zero static "from archive..." or "import archive..." in any .py outside the archive dirs themselves.
- No sys.path manipulation that adds archive/ or worktree paths in production launchers.
- Therefore, archived Python code is not import-reachable under normal execution.

## Risk Classification
- Import surface duplication (multiple driver creations): ARCHITECTURAL_DUPLICATION / EXECUTION_RISK for future bypass.
- No active import-based governance bypass via legacy code.
- Potential future risk if any training script or notebook adds archive to path.

## Recommendations
Add a CI static analysis gate that greps for any "from neo4j import" or "GraphDatabase.driver" outside the two canonical files (connection.py and the governance boundary itself), and fails the build.
