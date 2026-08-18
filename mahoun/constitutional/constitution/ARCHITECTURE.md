# MAHOUN Architecture Specification

Version: 1.0.0

Status: Normative

Authority Level: Constitutional Architecture Document


# 1. Purpose

This document defines the architectural model of the MAHOUN platform.

It establishes:

- system boundaries
- component responsibilities
- dependency direction
- architectural invariants
- integration rules
- prohibited architectural patterns


The purpose is to ensure that MAHOUN evolves as a controlled, modular, and explainable system.

Architecture is not defined by folder structure alone.

Architecture is defined by:

- responsibility
- dependency direction
- authority boundaries
- data ownership
- execution rules


# 2. Architectural Philosophy

MAHOUN follows a boundary-first architecture model.

The primary architectural question is not:

"Where is this file located?"

The primary question is:

"What responsibility does this component own?"


A component MUST be classified by responsibility before architectural decisions are made.


# 3. Repository Semantic Classification

The repository contains multiple artifact categories.


## 3.1 Production Architecture

Contains components that execute system behavior.

Examples:

- core logic
- APIs
- services
- retrieval systems
- reasoning engines
- data processing


## 3.2 Constitutional Architecture

Contains governance definitions.

Examples:

- constitutional rules
- architecture rules
- security policies
- agent definitions


## 3.3 Enforcement Architecture

Contains mechanisms that verify compliance.

Examples:

- validators
- guards
- static analysis
- CI checks


## 3.4 Tooling Artifacts

Examples:

- .ai
- .cursor
- .claude
- .vscode
- IDE configuration


Tooling artifacts MUST NOT be interpreted as production architecture.

They influence development experience, not runtime architecture.


# 4. High-Level Architecture Model


MAHOUN consists of the following logical layers:


             Constitutional Layer

                     |

                     v

             Governance Layer

                     |

                     v

              Core Domain Layer

                     |

      --------------------------------

      |              |               |

      v              v               v

   API Layer    Reasoning Layer   Retrieval Layer

                     |

                     v

               Data / Knowledge Layer


Dependency direction MUST move downward.

Lower layers MUST NOT redefine higher layers.


# 5. Constitutional Layer


Purpose:

Provide immutable architectural principles.


Responsibilities:

- define invariants
- define boundaries
- define governance rules


Characteristics:

- minimal
- deterministic
- stable


The Constitutional Layer MUST NOT contain:

- business logic
- API implementation
- data access
- model execution


# 6. Constitutional Kernel Architecture


The Constitutional Kernel is the smallest trusted computing base of MAHOUN.


Its responsibilities include:

- authorization boundaries
- governance context
- mutation control
- invariant enforcement


The Kernel MUST remain:

- deterministic
- minimal
- dependency-controlled


The Kernel MUST NOT depend on:

- API frameworks
- databases
- AI providers
- vector stores
- external services
- governance enforcement tools


# 7. Governance Enforcement Architecture


Purpose:

Verify that the system remains compliant.


Responsibilities:

- integrity checking
- architecture validation
- API validation
- security auditing


Governance tools inspect architecture.

They do not become architecture.


The following principle is mandatory:


"The mechanism enforcing architecture must not become the architecture itself."


# 8. Core Domain Architecture


The Core Domain Layer contains fundamental MAHOUN capabilities.


Responsibilities:

- domain rules
- core execution logic
- internal contracts


Core modules SHOULD avoid:

- external service dependencies
- infrastructure coupling


Core logic should remain reusable and testable.


# 9. API Architecture


The API Layer is the controlled external boundary.


Responsibilities:

- request validation
- authentication
- authorization delegation
- response contracts
- API lifecycle management


The API Layer MUST NOT bypass:

- governance
- authorization
- validation
- provenance mechanisms


API endpoints are contracts, not simple wrappers.


# 10. API Contract Principle


Every API contract consists of:


- input schema
- validation rules
- authorization requirements
- execution policy
- response schema
- provenance information


A change to any contract element is an architectural change.


# 11. Reasoning Architecture


The Reasoning Layer provides intelligent decision capabilities.


Responsibilities:

- reasoning orchestration
- inference coordination
- uncertainty management


Reasoning components MUST NOT:

- directly mutate protected state
- bypass authorization
- invent unsupported facts


Reasoning output requires validation before becoming trusted system state.


# 12. Retrieval Architecture


The Retrieval Layer provides information access.


Responsibilities:

- document retrieval
- semantic search
- ranking
- evidence gathering


Retrieval MUST remain separated from authorization.


Retrieval finds information.

Governance decides whether information can be used.


# 13. Graph Architecture


The Graph Layer represents relationships and structured knowledge.


Responsibilities:

- graph storage
- relationship management
- graph reasoning support


Graph mutations MUST pass through authorized mutation boundaries.


Direct uncontrolled mutation is prohibited.


Forbidden pattern:



Application

|

v

Direct Database Mutation



Required pattern:



Application

|

Governance Boundary

|

Graph Mutation



# 14. Data Architecture


Data components own:

- storage
- retrieval
- transformation


Data ownership MUST be explicit.


Components MUST NOT:

- silently alter schemas
- bypass validation
- create undocumented data states


# 15. Dependency Rules


Allowed:



Higher abstraction

    ↓

Lower implementation detail



Forbidden:



Infrastructure

    ↓

Core authority



Examples of forbidden dependencies:

- Kernel importing API
- Domain importing database drivers
- Governance importing application logic


# 16. Boundary Protection


Every architectural boundary requires:

- clear ownership
- explicit interface
- validation path


Hidden communication paths are architectural risks.


# 17. Module Ownership Principle


Every important module MUST have:

- defined owner
- defined responsibility
- defined dependencies


Modules without clear ownership create architectural drift.


# 18. Duplicate Responsibility Prevention


Multiple components MUST NOT own the same responsibility.


Forbidden:

- two governance controllers
- two authorization engines
- two conflicting policy resolvers


One responsibility requires one authoritative owner.


# 19. Architecture Evolution Rules


Architecture changes require:

1. impact analysis
2. dependency analysis
3. security review
4. contract review
5. validation evidence


Refactoring is not only moving files.

It is changing responsibility boundaries.


# 20. AI Agent Architecture Rules


AI agents MUST analyze architecture semantically.


Before modifying code, an agent MUST determine:

- component responsibility
- dependency impact
- governance impact


Agents MUST NOT:

- infer architecture from folder names only
- treat generated files as architecture
- modify boundaries casually


# 21. Architectural Anti-Patterns


## Folder-Based Architecture Assumption

Wrong:

"A folder exists, therefore it is a subsystem."


## God Module

Wrong:

"One module controls everything."


## Hidden Dependency

Wrong:

"A component depends on something without explicit contract."


## Governance Bypass

Wrong:

"A shortcut avoids authorization."


## Tool Contamination

Wrong:

"IDE configuration becomes system design."


# 22. Architecture Validation


Architecture validation SHOULD verify:

- dependency direction
- forbidden imports
- boundary violations
- duplicate ownership
- unauthorized access paths


Validation SHOULD be automated whenever possible.


# 23. Runtime Architecture Principle


Runtime behavior MUST remain consistent with declared architecture.


A system is architecturally invalid when:

- documentation says one thing
- execution does another


Implementation reality has priority over assumptions.


# 24. Architectural Decision Records


Significant architectural decisions SHOULD be recorded.

Records SHOULD include:

- problem
- options
- decision
- consequences
- alternatives rejected


# 25. Final Architectural Principle


MAHOUN architecture is based on controlled evolution.

Components may change.

Technologies may change.

Models may change.

Storage systems may change.

Architectural boundaries and responsibilities must remain explicit.

A system without boundaries cannot be governed.

A system without governance cannot remain reliable.
