"""
Seed Test Data for Integration Tests
=====================================
Seeds Neo4j and ChromaDB with test legal rules and precedents.
"""

import os
import logging
from typing import List

log = logging.getLogger(__name__)


def seed_test_knowledge_graph():
    """
    Seed Neo4j with test legal rules and precedents
    
    This function is called by Docker Compose before running integration tests.
    """
    try:
        from neo4j import GraphDatabase
        
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "testpassword123")
        
        log.info(f"Seeding test data to Neo4j at {neo4j_uri}")
        
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
        with driver.session() as session:
            # Clear existing test data
            session.run("MATCH (n:TestData) DETACH DELETE n")
            
            # Seed legal rules
            rules = [
                {
                    "rule_id": "rule_contract_validity",
                    "condition": "قرارداد امضا شده و پرداخت انجام شده",
                    "conclusion": "قرارداد معتبر است",
                    "confidence": 0.95,
                    "source": "قانون مدنی ماده 10",
                },
                {
                    "rule_id": "rule_contract_invalidity",
                    "condition": "قرارداد بدون امضا",
                    "conclusion": "قرارداد باطل است",
                    "confidence": 0.90,
                    "source": "قانون مدنی ماده 190",
                },
                {
                    "rule_id": "rule_payment_obligation",
                    "condition": "قرارداد معتبر",
                    "conclusion": "پرداخت الزامی است",
                    "confidence": 0.85,
                    "source": "قانون تجارت ماده 5",
                },
            ]
            
            for rule in rules:
                session.run(
                    """
                    CREATE (r:LegalRule:TestData {
                        rule_id: $rule_id,
                        condition: $condition,
                        conclusion: $conclusion,
                        confidence: $confidence,
                        source: $source
                    })
                    """,
                    **rule
                )
            
            # Seed legal precedents
            precedents = [
                {
                    "precedent_id": "prec_contract_case_2023",
                    "case_name": "پرونده 1402/123 - دادگاه تهران",
                    "facts": "قرارداد امضا شده اما پرداخت انجام نشده",
                    "ruling": "قرارداد معتبر اما قابل فسخ",
                    "confidence": 0.88,
                    "jurisdiction": "تهران",
                    "year": 2023,
                },
                {
                    "precedent_id": "prec_payment_case_2022",
                    "case_name": "پرونده 1401/456 - دیوان عالی",
                    "facts": "پرداخت با تاخیر انجام شده",
                    "ruling": "خسارت تاخیر تادیه",
                    "confidence": 0.92,
                    "jurisdiction": "دیوان عالی",
                    "year": 2022,
                },
            ]
            
            for precedent in precedents:
                session.run(
                    """
                    CREATE (p:LegalPrecedent:TestData {
                        precedent_id: $precedent_id,
                        case_name: $case_name,
                        facts: $facts,
                        ruling: $ruling,
                        confidence: $confidence,
                        jurisdiction: $jurisdiction,
                        year: $year
                    })
                    """,
                    **precedent
                )
            
            # Verify seeding
            result = session.run("MATCH (n:TestData) RETURN count(n) as count")
            count = result.single()["count"]
            
            log.info(f"✅ Seeded {count} test nodes to Neo4j")
        
        driver.close()
        
    except ImportError:
        log.warning("Neo4j driver not available - skipping seed")
    except Exception as e:
        log.error(f"Failed to seed test data: {e}")
        raise


def seed_test_embeddings():
    """
    Seed ChromaDB with test embeddings
    
    This function is called by Docker Compose before running integration tests.
    """
    try:
        import chromadb
        
        chroma_host = os.getenv("CHROMA_HOST", "localhost")
        chroma_port = int(os.getenv("CHROMA_PORT", "8000"))
        
        log.info(f"Seeding test embeddings to ChromaDB at {chroma_host}:{chroma_port}")
        
        client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
        
        # Create or get test collection
        collection = client.get_or_create_collection(
            name="test_legal_documents",
            metadata={"description": "Test legal documents for verification tests"}
        )
        
        # Seed test documents
        documents = [
            "قرارداد امضا شده و پرداخت انجام شده",
            "قرارداد بدون امضا",
            "پرداخت با تاخیر انجام شده",
        ]
        
        ids = [f"doc_{i}" for i in range(len(documents))]
        
        collection.add(
            documents=documents,
            ids=ids,
            metadatas=[{"source": "test"} for _ in documents]
        )
        
        log.info(f"✅ Seeded {len(documents)} test documents to ChromaDB")
        
    except ImportError:
        log.warning("ChromaDB not available - skipping seed")
    except Exception as e:
        log.error(f"Failed to seed embeddings: {e}")
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_test_knowledge_graph()
    seed_test_embeddings()
