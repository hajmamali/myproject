# Mahoun Platform Documentation

This directory contains comprehensive documentation for the Mahoun zero-hallucination AI reasoning platform.

## Quick Start

**Required reading for new developers:**

- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide for production and development environments
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture overview and design principles
- [API.md](API.md) - REST API reference and usage examples

## Documentation Index

### Architecture & Design

- [ARCHITECTURE.md](ARCHITECTURE.md) - Core architecture, modules, and design patterns
- [EXPLANATION_PROVENANCE_LAYER_SPEC.md](EXPLANATION_PROVENANCE_LAYER_SPEC.md) - Provenance layer specification for evidence tracking

### API Reference

- [API.md](API.md) - FastAPI endpoints, request/response schemas, authentication

### Deployment & Operations

- [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment, configuration, monitoring
- [DOCKER.md](DOCKER.md) - Docker Compose setup and container orchestration

### CI/CD

- [ci/](ci/) - Continuous integration gates and pipeline documentation

### Archive

- [archive/](archive/) - Historical documentation and deprecated specs

## Testing

For test structure and running tests, see [../tests/README.md](../tests/README.md).

## Development Workflow

1. Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand system design
2. Review [API.md](API.md) for endpoint specifications
3. Check [DEPLOYMENT.md](DEPLOYMENT.md) for environment setup
4. Run tests following [../tests/README.md](../tests/README.md)
5. Use [DOCKER.md](DOCKER.md) for local development with containers

## Contributing

- Follow architecture patterns documented in [ARCHITECTURE.md](ARCHITECTURE.md)
- Ensure all API changes are reflected in [API.md](API.md)
- Update relevant documentation when making changes
- Run full test suite before submitting changes

## Last Updated

This index was last updated: 2026-02-14
