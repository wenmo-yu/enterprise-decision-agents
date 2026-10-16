# Dependency Audit

The repository contains an embedded analytics subgraph. It is not only a planning or prompt-based integration: the subgraph retrieves schema candidates, generates SQL, performs programmatic read-only checks, optionally runs `EXPLAIN`, and executes through a read-only MySQL account. Therefore the following database and retrieval packages are deliberate runtime dependencies.

| Dependency | Runtime owner | Why it remains |
| --- | --- | --- |
| `asyncmy` | `app/analytics/agent.py` via `mysql+asyncmy://` | Async MySQL dialect used by SQLAlchemy for metadata, `EXPLAIN`, and bounded read-only queries. |
| `sqlalchemy` | `app/analytics/agent.py` | Creates async engines and binds parameters for metadata and warehouse access. |
| `sqlglot` | `app/analytics/agent.py` | Parses SQL and rejects multi-statement, write, DDL, locking reads, and other non-query forms before any database call. |
| `qdrant-client` | `app/analytics/agent.py` | Dense retrieval of schema fields and metrics. |
| `elasticsearch[async]` | `app/analytics/agent.py` | Retrieves candidate field values and business entities. |
| `httpx` | `app/analytics/agent.py` | Optional Cross-Encoder reranker request. |

`asyncmy` is intentionally not imported as a Python symbol: SQLAlchemy resolves it from the configured `mysql+asyncmy://` URL. Removing it would make the local analytics path fail at connection time.

## Removed direct dependencies

The following packages had no application import or runtime entry point after the embedded analytics migration and were removed from `pyproject.toml`:

- `aiofiles`
- `langchain-community`
- `markdown`
- `requests`

They may still appear in `uv.lock` as transitive dependencies of retained packages. A lockfile entry is not a direct application dependency.

`requirements.txt` was removed because it had diverged from the `pyproject.toml` + `uv.lock` source of truth. Installing with a second, stale manifest would make the repository less reproducible.

## Audit commands

Run these before release after changing application imports:

```powershell
uv lock
uv lock --check
uv run python -m compileall -q app tests
uv run python -m unittest tests/test_platform_safety.py tests/test_context_engineering.py
```

The listed tests validate analytics-graph compilation, SQL safety guards, context budgets and evidence contracts. A real integration run additionally requires the MySQL metadata/warehouse, Qdrant and Elasticsearch services described in [analytics_setup.md](analytics_setup.md).
