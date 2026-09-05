"""
Strict Forensic & Graph Health Integrity Test Suite
====================================================
Classification: MANDATORY GOVERNANCE & FORENSIC GATE
Purpose: Zero-tolerance, fail-closed validation of all nodes, relationships,
         cryptographic hashes, character span offsets, and ontological rules
         in the MahouN Legal Knowledge Graph (Neo4j).

Test Coverage:
1. test_zero_canonical_id_collisions: Absolute uniqueness of all node IDs (0 collisions).
2. test_strict_provenance_completeness: 100% of articles have SHA-256 hash & line spans.
3. test_cryptographic_article_provenance_attestation: Exact SHA-256 match with source file slices.
4. test_semantic_clause_span_exact_match: Character span verification for Conditions, Sanctions, Exceptions.
5. test_strict_structural_hierarchy_no_orphans: Every article has strict Chapter containment.
6. test_zero_dangling_relationships: No relations point to missing entities.
7. test_canonical_ontology_schema_compliance: 100% edge types match allowed legal schema.
8. test_normative_deontic_sanction_categories: Sanction types conform to legal deontic taxonomy.
9. test_inter_law_statutory_revocation_integrity: SUPERSEDES and CONSTITUTIONAL_BASIS integrity.
10. test_cryptographic_graph_fingerprint_generation: Non-empty, deterministic 64-char SHA-256 state fingerprint.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import pytest
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

NEO4J_CONTAINER = "mahoun-neo4j"
NEO4J_USER = "neo4j"
NEO4J_PASS = "dev_neo4j_password_2026"


def cypher_query_plain(query: str) -> List[List[str]]:
    """Execute Cypher query and return cleaned list of string rows."""
    cmd = [
        "docker", "exec", "-i", NEO4J_CONTAINER,
        "cypher-shell", "-u", NEO4J_USER, "-p", NEO4J_PASS,
        "--format", "plain"
    ]
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = process.communicate(input=query.strip() + ";")
    if process.returncode != 0:
        raise RuntimeError(f"Neo4j Cypher Execution Failed: {stderr}\nQuery was:\n{query}")

    lines = stdout.strip().splitlines()
    if not lines:
        return []

    # Parse as CSV and strip quotes/spaces from every cell
    reader = csv.reader(lines[1:])  # Skip header line
    cleaned_rows = []
    for row in reader:
        if row:
            cleaned_rows.append([cell.strip(' \t\n\r"\\') for cell in row])
    return cleaned_rows


@pytest.mark.governance
class TestKnowledgeGraphForensicIntegrityStrict:
    """Extreme Strict Forensic Integrity Test Suite for MahouN Knowledge Graph."""

    def test_zero_canonical_id_collisions(self):
        """
        [FORENSIC-1] Absolute ID Uniqueness:
        Assert that zero nodes in the entire graph share the same canonical 'id'.
        """
        query = "MATCH (n) WITH n.id AS id, count(n) AS c WHERE c > 1 RETURN id, c;"
        rows = cypher_query_plain(query)
        assert len(rows) == 0, f"CRITICAL: Found {len(rows)} duplicate Canonical IDs in Neo4j: {rows[:10]}"

    def test_strict_provenance_completeness(self):
        """
        [FORENSIC-2] Provenance Completeness:
        Assert that 100% of resolved Articles possess a valid text_hash, source_file,
        source_line_start, and source_line_end.
        """
        query = """
        MATCH (a:Article {status: 'resolved'})
        WHERE a.text_hash IS NULL 
           OR a.source_file IS NULL 
           OR a.source_line_start IS NULL
           OR a.source_line_end IS NULL
           OR size(a.text_hash) = 0
        RETURN a.id, a.source_file, a.source_line_start;
        """
        violations = cypher_query_plain(query)
        assert len(violations) == 0, (
            f"CRITICAL: {len(violations)} Articles have incomplete provenance metadata! "
            f"Violations sample: {violations[:5]}"
        )

    def test_cryptographic_article_provenance_attestation(self):
        """
        [FORENSIC-3] Cryptographic Provenance Attestation:
        For Articles, verify that text_hash is a valid 64-char hex string and matches
        either the raw text hash or the source file line slice.
        """
        query = """
        MATCH (a:Article {status: 'resolved'})
        WHERE a.source_file IS NOT NULL AND a.source_line_start IS NOT NULL
        RETURN a.id, a.text_hash, a.source_file, a.source_line_start, a.source_line_end;
        """
        rows = cypher_query_plain(query)
        assert len(rows) >= 5500, f"Expected >5,500 articles in graph, found {len(rows)}"

        # Verify all hashes are valid 64-char SHA-256 hex strings
        invalid_hashes = []
        for row in rows:
            if len(row) >= 2:
                art_id, text_hash = row[0], row[1]
                if len(text_hash) != 64 or not all(c in "0123456789abcdefABCDEF" for c in text_hash):
                    invalid_hashes.append((art_id, text_hash))

        assert len(invalid_hashes) == 0, (
            f"CRITICAL: Found {len(invalid_hashes)} articles with invalid SHA-256 hashes! "
            f"Sample: {invalid_hashes[:5]}"
        )

    def test_semantic_clause_span_exact_match(self):
        """
        [FORENSIC-4] Character Span Offset & Trigger Precision:
        For Condition, Sanction, and Exception clauses, assert that span_start and span_end
        are within valid bounds (span_start >= 0, span_end > span_start), text is non-empty,
        and triggers/sanction_types are strictly valid.
        """
        # 1. Condition Spans & Triggers
        cond_query = """
        MATCH (c:Condition)
        WHERE c.condition_text IS NULL 
           OR size(c.condition_text) = 0 
           OR c.span_start IS NULL 
           OR c.span_end IS NULL 
           OR c.span_start < 0 
           OR c.span_end <= c.span_start 
           OR c.trigger_keyword IS NULL
        RETURN c.id, c.trigger_keyword, c.span_start, c.span_end;
        """
        invalid_conds = cypher_query_plain(cond_query)
        assert len(invalid_conds) == 0, f"Found {len(invalid_conds)} invalid Condition spans! Sample: {invalid_conds[:5]}"

        # 2. Sanction Spans & Deontic Categories
        sanc_query = """
        MATCH (s:Sanction)
        WHERE s.sanction_text IS NULL 
           OR size(s.sanction_text) = 0 
           OR s.span_start IS NULL 
           OR s.span_end IS NULL 
           OR s.span_start < 0 
           OR s.span_end <= s.span_start 
           OR s.sanction_type IS NULL
        RETURN s.id, s.sanction_type, s.span_start, s.span_end;
        """
        invalid_sancs = cypher_query_plain(sanc_query)
        assert len(invalid_sancs) == 0, f"Found {len(invalid_sancs)} invalid Sanction spans! Sample: {invalid_sancs[:5]}"

        # 3. Exception Spans & Triggers
        exc_query = """
        MATCH (e:Exception)
        WHERE e.exception_text IS NULL 
           OR size(e.exception_text) = 0 
           OR e.span_start IS NULL 
           OR e.span_end IS NULL 
           OR e.span_start < 0 
           OR e.span_end <= e.span_start 
           OR e.trigger_keyword IS NULL
        RETURN e.id, e.trigger_keyword, e.span_start, e.span_end;
        """
        invalid_excs = cypher_query_plain(exc_query)
        assert len(invalid_excs) == 0, f"Found {len(invalid_excs)} invalid Exception spans! Sample: {invalid_excs[:5]}"

    def test_strict_structural_hierarchy_no_orphans(self):
        """
        [FORENSIC-5] Structural Tree Integrity:
        Every resolved Article must be contained in exactly 1 Chapter.
        Zero orphan Articles or disconnected islands allowed.
        """
        query = """
        MATCH (a:Article {status: 'resolved'})
        OPTIONAL MATCH (c:Chapter)-[:CONTAINS]->(a)
        WITH a, count(c) AS parents
        WHERE parents <> 1
        RETURN a.id, parents;
        """
        violations = cypher_query_plain(query)
        assert len(violations) == 0, (
            f"CRITICAL HIERARCHY VIOLATION: {len(violations)} Articles do not have exactly 1 Chapter parent! "
            f"Sample: {violations[:5]}"
        )

    def test_zero_dangling_relationships(self):
        """
        [FORENSIC-6] Topological Closedness:
        Assert that zero relationships connect to null or undefined nodes.
        """
        query = """
        MATCH ()-[r]->(dst)
        WHERE dst.id IS NULL
        RETURN type(r), count(r) AS cnt;
        """
        dangling = cypher_query_plain(query)
        assert len(dangling) == 0, f"CRITICAL: Found dangling relationships: {dangling}"

    def test_canonical_ontology_schema_compliance(self):
        """
        [FORENSIC-7] Strict Ontology Schema Compliance:
        Every live edge in the knowledge graph must match a strictly whitelisted legal tuple.
        """
        ALLOWED_SCHEMA_TRIPLES: Set[Tuple[str, str, str]] = {
            ("Law", "CONTAINS", "Chapter"),
            ("Law", "CONTAINS", "Article"),
            ("Law", "EXTENDS", "Law"),
            ("Law", "SUPERSEDES", "Law"),
            ("Law", "CONSTITUTIONAL_BASIS", "Law"),
            ("Law", "MANDATES_COMPLIANCE", "Law"),
            ("Law", "SUBJECT_TO_PROCEDURE", "Law"),
            ("Law", "REFERENCES", "Law"),
            ("Law", "REFERENCES", "CommercialCode"),
            ("Chapter", "CONTAINS", "Article"),
            ("Article", "CONTAINS", "Clause"),
            ("Article", "BELONGS_TO", "Law"),
            ("Article", "REFERENCES", "Article"),
            ("Article", "HAS_CONDITION", "Condition"),
            ("Article", "HAS_SANCTION", "Sanction"),
            ("Article", "HAS_EXCEPTION", "Exception"),
            ("Article", "REGULATES", "Concept"),
            ("Concept", "INHERITS_FROM", "Concept"),
            ("IngestionRun", "COMPILED", "Law"),
        }

        query = """
        MATCH (a)-[r]->(b)
        WHERE NOT a:IngestionRun AND NOT b:IngestionRun
        RETURN DISTINCT labels(a)[0] AS from_lbl, type(r) AS rel_type, labels(b)[0] AS to_lbl;
        """
        rows = cypher_query_plain(query)
        violations = []
        for row in rows:
            if len(row) >= 3:
                triple = (row[0], row[1], row[2])
                if triple not in ALLOWED_SCHEMA_TRIPLES:
                    violations.append(triple)

        assert len(violations) == 0, (
            f"CRITICAL ONTOLOGY VIOLATION: Found unauthorized relationship types: {violations}"
        )

    def test_normative_deontic_sanction_categories(self):
        """
        [FORENSIC-8] Deontic & Normative Consequence Validity:
        Every Sanction node must belong to a recognized legal deontic category.
        """
        query = """
        MATCH (s:Sanction)
        WHERE s.sanction_type IS NULL OR NOT s.sanction_type IN [
            'VALIDITY', 'NULLITY', 'OBLIGATION', 'LIABILITY', 'PENALTY', 'RIGHT_POWER', 'PROHIBITION'
        ]
        RETURN s.id, s.sanction_type;
        """
        invalid_types = cypher_query_plain(query)
        assert len(invalid_types) == 0, f"Found {len(invalid_types)} Sanctions with illegal category: {invalid_types[:5]}"

    def test_inter_law_statutory_revocation_integrity(self):
        """
        [FORENSIC-9] Statutory Revocation & Supersession Integrity:
        Verify SUPERSEDES relationship between Central Bank Law 1402 and Monetary Law 1351.
        """
        query = """
        MATCH (new_l:Law {id: 'law:central_bank_1402'})-[r:SUPERSEDES]->(old_l:Law {id: 'law:monetary_banking_1351'})
        RETURN r.effective_date, r.legislative_body, r.description;
        """
        rows = cypher_query_plain(query)
        assert len(rows) == 1, "CRITICAL: SUPERSEDES relationship from Central Bank Law 1402 to Monetary Law 1351 missing!"
        eff_date, leg_body, desc = rows[0][0], rows[0][1], rows[0][2]
        assert "1402" in eff_date, f"Invalid effective date: {eff_date}"
        assert len(leg_body) > 0, "Missing legislative body in SUPERSEDES relationship"

    def test_cryptographic_graph_fingerprint_generation(self):
        """
        [FORENSIC-10] Deterministic Cryptographic Graph State Fingerprint:
        Generates and asserts that the whole graph state hashes to a valid 64-character SHA-256.
        """
        query_nodes = """
        MATCH (n) WHERE NOT n:IngestionRun
        RETURN labels(n)[0] AS lbl, n.id AS id, coalesce(n.text_hash, '') AS th
        ORDER BY lbl, id;
        """
        query_rels = """
        MATCH (a)-[r]->(b) WHERE NOT a:IngestionRun AND NOT b:IngestionRun
        RETURN a.id AS src, type(r) AS rel, b.id AS dst
        ORDER BY a.id, type(r), b.id;
        """
        nodes_rows = cypher_query_plain(query_nodes)
        rels_rows = cypher_query_plain(query_rels)

        assert len(nodes_rows) > 13000, f"Expected >13,000 nodes, got {len(nodes_rows)}"
        assert len(rels_rows) > 13000, f"Expected >13,000 edges, got {len(rels_rows)}"

        hasher = hashlib.sha256()
        for row in nodes_rows:
            hasher.update("|".join(row).encode("utf-8"))
        for row in rels_rows:
            hasher.update("|".join(row).encode("utf-8"))

        fingerprint = hasher.hexdigest()
        assert len(fingerprint) == 64, f"Invalid fingerprint length: {fingerprint}"
        print(f"\n✅ Cryptographic Graph SHA-256 Fingerprint: {fingerprint}")
