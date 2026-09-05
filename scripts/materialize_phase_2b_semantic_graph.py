"""
Materialize Phase 2B Semantic Layer in Neo4j
=============================================
Enriches the MahouN Legal Knowledge Graph with:
1. Canonical Legal Concepts (:Concept) and hierarchy (:INHERITS_FROM)
2. Article logical decomposition (:Condition, :Sanction, :Exception)
3. Logical relationships (:HAS_CONDITION, :HAS_SANCTION, :HAS_EXCEPTION)
4. Taxonomic semantic assertions (Article -[:REGULATES]-> Concept)
"""

import csv
import json
import logging
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.abspath("."))

from mahoun.graph.ontology.legal_concepts import CANONICAL_LEGAL_CONCEPTS
from mahoun.graph.extraction.semantic_extractor import SemanticExtractor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

NEO4J_CONTAINER = "mahoun-neo4j"
NEO4J_USER = "neo4j"
NEO4J_PASS = "dev_neo4j_password_2026"


def to_cypher_literal(obj) -> str:
    """Recursively converts Python objects into valid Cypher map / list literal syntax."""
    if isinstance(obj, str):
        return json.dumps(obj, ensure_ascii=False)
    elif isinstance(obj, list):
        return "[" + ", ".join(to_cypher_literal(x) for x in obj) + "]"
    elif isinstance(obj, dict):
        return "{" + ", ".join(f"{k}: {to_cypher_literal(v)}" for k, v in obj.items()) + "}"
    elif obj is None:
        return "null"
    elif isinstance(obj, bool):
        return "true" if obj else "false"
    elif isinstance(obj, (int, float)):
        return str(obj)
    return json.dumps(str(obj), ensure_ascii=False)


def run_cypher_statement(cypher: str) -> str:
    """Executes a single cypher statement inside the neo4j container."""
    cypher_clean = cypher.strip()
    if not cypher_clean.endswith(";"):
        cypher_clean += ";"

    cmd = [
        "docker", "exec", "-i", NEO4J_CONTAINER,
        "cypher-shell", "-u", NEO4J_USER, "-p", NEO4J_PASS
    ]
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = process.communicate(input=cypher_clean)
    if process.returncode != 0:
        logger.error("Cypher execution failed: %s\nStatement snippet:\n%s", stderr, cypher_clean[:500])
        raise RuntimeError(f"Cypher error: {stderr}")
    return stdout


def main():
    start_time = time.time()
    logger.info("Starting Phase 2B Semantic Layer Materialization...")

    extractor = SemanticExtractor(ontology=CANONICAL_LEGAL_CONCEPTS)

    # 1. Materialize Canonical Concepts and Hierarchy
    logger.info("--- Step 1: Materializing Concepts Taxonomy ---")
    concepts_list = []
    hierarchy_list = []

    for concept_id, concept in CANONICAL_LEGAL_CONCEPTS.items():
        concepts_list.append({
            "id": concept.canonical_id,
            "label_fa": concept.canonical_label_fa,
            "label_en": concept.canonical_label_en,
            "norm_label": concept.normalized_label,
            "domain": concept.domain,
            "jurisdiction": concept.jurisdiction,
            "onto_ver": concept.ontology_version,
            "schema_ver": concept.semantic_schema_version,
            "desc_fa": concept.description_fa or "",
            "aliases_fa": concept.aliases_fa,
            "aliases_en": concept.aliases_en,
        })
        if concept.parent_concept_id:
            hierarchy_list.append({
                "child_id": concept.canonical_id,
                "parent_id": concept.parent_concept_id,
            })

    concept_cypher = f"""
    UNWIND {to_cypher_literal(concepts_list)} AS c
    MERGE (node:Concept {{id: c.id}})
    SET node.canonical_label_fa = c.label_fa,
        node.canonical_label_en = c.label_en,
        node.normalized_label = c.norm_label,
        node.domain = c.domain,
        node.jurisdiction = c.jurisdiction,
        node.ontology_version = c.onto_ver,
        node.semantic_schema_version = c.schema_ver,
        node.description_fa = c.desc_fa,
        node.aliases_fa = c.aliases_fa,
        node.aliases_en = c.aliases_en;
    """
    run_cypher_statement(concept_cypher)

    hierarchy_cypher = f"""
    UNWIND {to_cypher_literal(hierarchy_list)} AS h
    MATCH (child:Concept {{id: h.child_id}})
    MATCH (parent:Concept {{id: h.parent_id}})
    MERGE (child)-[:INHERITS_FROM]->(parent);
    """
    run_cypher_statement(hierarchy_cypher)
    logger.info("Concepts and Hierarchy successfully materialized.")

    # 2. Fetch all Articles from Neo4j
    logger.info("--- Step 2: Fetching All Articles from Neo4j ---")
    fetch_cypher = """
    MATCH (a:Article)
    RETURN a.id AS id, a.law_id AS law_id, coalesce(a.normalized_text, a.raw_text, '') AS text;
    """
    cmd = [
        "docker", "exec", NEO4J_CONTAINER,
        "cypher-shell", "-u", NEO4J_USER, "-p", NEO4J_PASS,
        "--format", "plain", fetch_cypher
    ]
    raw_articles_out = subprocess.check_output(cmd, text=True)

    articles = []
    lines = raw_articles_out.strip().splitlines()
    if lines:
        reader = csv.reader(lines[1:])
        for row in reader:
            if len(row) >= 3:
                articles.append({
                    "id": row[0].strip(),
                    "law_id": row[1].strip(),
                    "text": row[2].strip()
                })

    logger.info("Fetched %d articles for semantic decomposition.", len(articles))

    # 3. Process Articles in batches
    conditions_batch = []
    sanctions_batch = []
    exceptions_batch = []
    assertions_batch = []

    for art in articles:
        art_id = art["id"]
        law_id = art["law_id"]
        text = art["text"]

        if not text:
            continue

        decomp = extractor.decompose_article(art_id, law_id, text)
        for cond in decomp.conditions:
            conditions_batch.append({
                "art_id": art_id,
                "cond_id": cond.id,
                "text": cond.condition_text,
                "trigger": cond.trigger_keyword,
                "start": cond.span_start,
                "end": cond.span_end,
            })
        for sanc in decomp.sanctions:
            sanctions_batch.append({
                "art_id": art_id,
                "sanc_id": sanc.id,
                "text": sanc.sanction_text,
                "type": sanc.sanction_type,
                "start": sanc.span_start,
                "end": sanc.span_end,
            })
        for exc in decomp.exceptions:
            exceptions_batch.append({
                "art_id": art_id,
                "exc_id": exc.id,
                "text": exc.exception_text,
                "trigger": exc.trigger_keyword,
                "start": exc.span_start,
                "end": exc.span_end,
            })

        assertions = extractor.extract_concept_assertions(art_id, text)
        for assert_obj in assertions:
            assertions_batch.append({
                "art_id": assert_obj.source_entity_id,
                "concept_id": assert_obj.target_entity_id,
                "assertion_id": assert_obj.assertion_id,
                "evidence_span": assert_obj.evidence_text_span,
                "start": assert_obj.evidence_offset_start,
                "end": assert_obj.evidence_offset_end,
                "sha256": assert_obj.evidence_sha256,
                "status": assert_obj.status.value,
                "method": assert_obj.verification_method,
            })

    logger.info("Extracted %d Conditions, %d Sanctions, %d Exceptions, %d REGULATES Assertions.",
                len(conditions_batch), len(sanctions_batch), len(exceptions_batch), len(assertions_batch))

    # 4. Ingest Conditions in Chunks
    logger.info("--- Step 3: Materializing Conditions into Neo4j ---")
    CHUNK_SIZE = 300
    for i in range(0, len(conditions_batch), CHUNK_SIZE):
        chunk = conditions_batch[i:i + CHUNK_SIZE]
        cypher = f"""
        UNWIND {to_cypher_literal(chunk)} AS row
        MATCH (a:Article {{id: row.art_id}})
        MERGE (c:Condition {{id: row.cond_id}})
        SET c.article_id = row.art_id,
            c.condition_text = row.text,
            c.trigger_keyword = row.trigger,
            c.span_start = row.start,
            c.span_end = row.end
        MERGE (a)-[:HAS_CONDITION]->(c);
        """
        run_cypher_statement(cypher)
        logger.info("  Conditions progress: %d/%d", min(i + CHUNK_SIZE, len(conditions_batch)), len(conditions_batch))

    # 5. Ingest Sanctions in Chunks
    logger.info("--- Step 4: Materializing Sanctions into Neo4j ---")
    for i in range(0, len(sanctions_batch), CHUNK_SIZE):
        chunk = sanctions_batch[i:i + CHUNK_SIZE]
        cypher = f"""
        UNWIND {to_cypher_literal(chunk)} AS row
        MATCH (a:Article {{id: row.art_id}})
        MERGE (s:Sanction {{id: row.sanc_id}})
        SET s.article_id = row.art_id,
            s.sanction_text = row.text,
            s.sanction_type = row.type,
            s.span_start = row.start,
            s.span_end = row.end
        MERGE (a)-[:HAS_SANCTION]->(s);
        """
        run_cypher_statement(cypher)
        logger.info("  Sanctions progress: %d/%d", min(i + CHUNK_SIZE, len(sanctions_batch)), len(sanctions_batch))

    # 6. Ingest Exceptions in Chunks
    logger.info("--- Step 5: Materializing Exceptions into Neo4j ---")
    for i in range(0, len(exceptions_batch), CHUNK_SIZE):
        chunk = exceptions_batch[i:i + CHUNK_SIZE]
        cypher = f"""
        UNWIND {to_cypher_literal(chunk)} AS row
        MATCH (a:Article {{id: row.art_id}})
        MERGE (e:Exception {{id: row.exc_id}})
        SET e.article_id = row.art_id,
            e.exception_text = row.text,
            e.trigger_keyword = row.trigger,
            e.span_start = row.start,
            e.span_end = row.end
        MERGE (a)-[:HAS_EXCEPTION]->(e);
        """
        run_cypher_statement(cypher)
        logger.info("  Exceptions progress: %d/%d", min(i + CHUNK_SIZE, len(exceptions_batch)), len(exceptions_batch))

    # 7. Ingest Concept REGULATES Assertions in Chunks
    logger.info("--- Step 6: Materializing REGULATES Assertions into Neo4j ---")
    for i in range(0, len(assertions_batch), CHUNK_SIZE):
        chunk = assertions_batch[i:i + CHUNK_SIZE]
        cypher = f"""
        UNWIND {to_cypher_literal(chunk)} AS row
        MATCH (a:Article {{id: row.art_id}})
        MATCH (c:Concept {{id: row.concept_id}})
        MERGE (a)-[r:REGULATES]->(c)
        SET r.assertion_id = row.assertion_id,
            r.evidence_text_span = row.evidence_span,
            r.evidence_offset_start = row.start,
            r.evidence_offset_end = row.end,
            r.evidence_sha256 = row.sha256,
            r.status = row.status,
            r.verification_method = row.method;
        """
        run_cypher_statement(cypher)
        logger.info("  REGULATES progress: %d/%d", min(i + CHUNK_SIZE, len(assertions_batch)), len(assertions_batch))

    # 8. Verification Queries
    logger.info("--- Step 7: Verifying Live Graph State ---")
    verification_metrics = {}
    for label, query in [
        ("Total Nodes", "MATCH (n) RETURN count(n) AS cnt"),
        ("Total Relationships", "MATCH ()-[r]->() RETURN count(r) AS cnt"),
        ("Concept Nodes", "MATCH (c:Concept) RETURN count(c) AS cnt"),
        ("Condition Nodes", "MATCH (c:Condition) RETURN count(c) AS cnt"),
        ("Sanction Nodes", "MATCH (s:Sanction) RETURN count(s) AS cnt"),
        ("Exception Nodes", "MATCH (e:Exception) RETURN count(e) AS cnt"),
        ("REGULATES Rel", "MATCH ()-[r:REGULATES]->() RETURN count(r) AS cnt"),
        ("HAS_CONDITION Rel", "MATCH ()-[r:HAS_CONDITION]->() RETURN count(r) AS cnt"),
        ("HAS_SANCTION Rel", "MATCH ()-[r:HAS_SANCTION]->() RETURN count(r) AS cnt"),
        ("HAS_EXCEPTION Rel", "MATCH ()-[r:HAS_EXCEPTION]->() RETURN count(r) AS cnt"),
        ("INHERITS_FROM Rel", "MATCH ()-[r:INHERITS_FROM]->() RETURN count(r) AS cnt"),
    ]:
        res = run_cypher_statement(query)
        lines = res.strip().splitlines()
        val = lines[-1].strip() if len(lines) > 1 else lines[0].strip()
        verification_metrics[label] = val

    print("\n" + "=" * 65)
    print("           LIVE NEO4J VERIFICATION RESULTS")
    print("=" * 65)
    for k, v in verification_metrics.items():
        print(f"  {k:<28}: {v}")
    print(f"\n  Elapsed Time                : {time.time() - start_time:.2f} seconds")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
