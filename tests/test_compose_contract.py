import re
import pytest
from pathlib import Path


@pytest.fixture
def docker_compose_content():
    compose_file = Path(__file__).parent.parent / "docker-compose.yml"
    if not compose_file.exists():
        pytest.skip("docker-compose.yml not found")
    return compose_file.read_text()


def test_neo4j_healthcheck_uses_correct_env_vars(docker_compose_content):
    neo4j_match = re.search(
        r"^\s{2}neo4j:\s*$.*?(?=^\s{2}\w+:|^volumes:|^networks:|\Z)",
        docker_compose_content,
        re.MULTILINE | re.DOTALL
    )
    assert neo4j_match, "Neo4j service not found in docker-compose.yml"
    
    neo4j_text = neo4j_match.group()
    
    assert "healthcheck:" in neo4j_text, "Neo4j healthcheck section not found"
    assert "cypher-shell" in neo4j_text, "Neo4j healthcheck doesn't use cypher-shell"
    
    assert "DB_NEO4J_PASSWORD" in neo4j_text or "NEO4J_PASSWORD" in neo4j_text, \
        "Neo4j health check must reference password env var"
    
    assert "DB_NEO4J_PASSWORD" in neo4j_text, \
        "Neo4j health check should use DB_NEO4J_PASSWORD (canonical name), not NEO4J_PASSWORD"


def test_redis_port_mapping_avoids_conflict(docker_compose_content):
    redis_section = re.search(
        r"redis:.*?(?=\n\w+:|\Z)",
        docker_compose_content,
        re.DOTALL
    )
    assert redis_section, "Redis service not found in docker-compose.yml"
    
    ports_match = re.search(
        r"ports:.*?-\s+[\"']?\$\{REDIS_PORT:-(\d+)\}:6379[\"']?",
        redis_section.group(),
        re.DOTALL
    )
    
    assert ports_match, "Redis port mapping not found or malformed"
    
    default_external_port = int(ports_match.group(1))
    
    assert default_external_port != 6379, \
        f"Redis default external port should NOT be 6379 (conflict risk). Found: {default_external_port}"
    
    assert default_external_port == 6380, \
        f"Redis default external port should be 6380. Found: {default_external_port}"


def test_redis_command_handles_empty_password(docker_compose_content):
    redis_section = re.search(
        r"redis:.*?(?=\n\w+:|\Z)",
        docker_compose_content,
        re.DOTALL
    )
    assert redis_section, "Redis service not found in docker-compose.yml"
    
    redis_text = redis_section.group()
    
    has_requirepass = "requirepass" in redis_text.lower()
    
    if has_requirepass:
        has_conditional = "if" in redis_text and "REDIS_PASSWORD" in redis_text
        
        assert has_conditional, \
            "Redis command uses --requirepass but lacks conditional logic for empty password. " \
            "This breaks when REDIS_PASSWORD is empty (empty value consumed next arg)."


def test_chromadb_service_exists(docker_compose_content):
    chromadb_section = re.search(
        r"chromadb:.*?(?=\n\w+:|\Z)",
        docker_compose_content,
        re.DOTALL
    )
    assert chromadb_section, "ChromaDB service not found in docker-compose.yml"
    
    chromadb_text = chromadb_section.group()
    
    image_match = re.search(r"image:\s+(\S+)", chromadb_text)
    assert image_match, "ChromaDB image not specified"
    
    image = image_match.group(1)
    assert "chroma" in image.lower(), f"ChromaDB image should contain 'chroma', found: {image}"


def test_all_services_use_mahoun_volume_prefix(docker_compose_content):
    volumes_section = re.search(
        r"^volumes:.*",
        docker_compose_content,
        re.MULTILINE | re.DOTALL
    )
    
    if not volumes_section:
        pytest.skip("No volumes section found")
    
    volumes_text = volumes_section.group()
    
    volume_names = re.findall(r"name:\s+(\S+)", volumes_text)
    
    for volume_name in volume_names:
        assert volume_name.startswith("mahoun_"), \
            f"Volume '{volume_name}' should use 'mahoun_' prefix (found legacy prefix?)"


def test_no_legacy_platform33_references(docker_compose_content):
    legacy_prefix = "platform33"
    
    assert legacy_prefix not in docker_compose_content.lower(), \
        f"Found legacy '{legacy_prefix}' reference in docker-compose.yml. " \
        "All references should use 'mahoun' prefix."
