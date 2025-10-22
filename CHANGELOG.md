# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-10-22

### Added
- Modern async-first architecture with `AsyncDHIS2Client` and `SyncDHIS2Client`
- Comprehensive analytics endpoint with DataFrame conversion (`.to_pandas()`)
- DataValueSets endpoint with read/write capabilities
- Tracker events endpoint with pagination and streaming
- Metadata endpoint with import/export functionality
- Built-in rate limiting with adaptive strategies
- Robust retry mechanism with exponential backoff
- HTTP caching with ETag and Last-Modified support
- Data Quality Review (DQR) metrics based on WHO standards
- Command-line interface (CLI) with typer
- Project template system using Cookiecutter
- OpenTelemetry instrumentation for observability
- Comprehensive test suite (348 tests)
- Multi-platform CI/CD (Ubuntu, Windows, macOS)
- Support for Python 3.9, 3.10, 3.11

### Features
- **Analytics**: Query, pagination, streaming, export to multiple formats
- **DataValueSets**: Pull, push, chunking, conflict resolution
- **Tracker**: Events and tracked entities with full CRUD operations
- **Metadata**: Export, import, validation, schema inspection
- **DQR**: Completeness, consistency, and timeliness metrics
- **I/O**: Native Pandas, Arrow, and Parquet support
- **Resilience**: Rate limiting, retries, caching, compression
- **Developer Experience**: Type hints, clear error messages, extensive examples

### Documentation
- Comprehensive README with quick start guide
- Example scripts for common use cases
- Contributing guidelines
- Code of Conduct
- API documentation in docstrings

### Infrastructure
- GitHub Actions CI pipeline
- Ruff for linting and formatting
- pytest with asyncio support
- Modern packaging with pyproject.toml

---

## Unreleased

### Planned
- Enhanced CLI functionality for data operations
- ReadTheDocs documentation site
- Additional DQR metrics and visualizations
- Performance benchmarking tools
- More example notebooks and tutorials
- Integration with additional data formats (Polars, DuckDB)

---

[0.2.0]: https://github.com/HzaCode/pyDHIS2/releases/tag/v0.2.0

