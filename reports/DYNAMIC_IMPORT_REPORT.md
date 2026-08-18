# MAHOUN DYNAMIC_IMPORT_REPORT
Date: 2026-05-25

## Dynamic Import Mechanisms in Use
- importlib.import_module (standard, for guardrails and ultra/base switching)
- No SourceFileLoader or spec_from_file_location found in production code
- exec() found in:
  - mahoun/graph/ingestion/document_classifier.py (for numpy import hack and other code blocks)
- No pickle, dill, or shelve used for loading executable code (only potential for data)

## Targets of Dynamic Imports
All resolved module names are static strings pointing to current mahoun.* packages.
No variable paths, no paths constructed from user input, no references to "archive", "backup", ".kilo", "worktree", "legacy", "tmp".

## Risk from Dynamic Loading
- Low for loading malicious archived code (no path to them).
- Medium for document_classifier.py exec() usage: allows arbitrary Python at import time for that module. Although currently used only for numpy fallback, it is a code injection surface if the file is ever edited or if globals are polluted.

## Subprocess as Indirect Dynamic Execution
Multiple scripts use subprocess to run python, git, docker, pytest, etc. These are controlled admin/CI operations, not arbitrary user-controlled code execution.

## Conclusion
No evidence of dynamic loading of archived, worktree, or experimental code at runtime.
The exec() in document_classifier.py is the only notable dynamic code execution risk and should be removed.
