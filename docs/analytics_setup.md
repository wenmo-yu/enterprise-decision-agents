# Embedded Analytics Setup

`app/analytics` is the local LangGraph subgraph used by the 经营问数专家. It is not an HTTP client and does not need the former standalone question-answering service.

## Required services

| Service | Responsibility | Environment variable |
| --- | --- | --- |
| MySQL metadata database | table, column, metric definitions and schema dependencies | `ANALYTICS_METADATA_DATABASE_URL` |
| MySQL warehouse | read-only `EXPLAIN` and query execution | `ANALYTICS_WAREHOUSE_DATABASE_URL` |
| Qdrant | dense retrieval for columns and metrics | `ANALYTICS_QDRANT_URL` |
| Elasticsearch | field-value retrieval | `ANALYTICS_ELASTICSEARCH_URL` |
| Embedding endpoint | converts analysis queries to vectors | `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `ANALYTICS_EMBEDDING_MODEL` |
| Cross-Encoder endpoint, optional | reranks dense candidates | `ANALYTICS_RERANKER_URL` |

The warehouse account must receive only the minimum `SELECT` privileges. Application-level `sqlglot` validation is a second line of defence; it is not a substitute for database permissions.

## Metadata contract

The metadata database contains `column_info` records used during schema dependency expansion. Required columns are `id`, `table_id`, `name`, `type`, `role`, `description` and `alias`. `role` uses `primary_key` or `foreign_key` for join keys. Temporal columns named `date`, `date_id`, `year`, `quarter`, `month` or `day` are included automatically when a table is retrieved.

Qdrant collections contain the same field/metric metadata in the point payload. Elasticsearch documents use at least `value` and `column_id`. Keeping the payload IDs equal to the metadata IDs gives the final SQL prompt a stable audit trail.

## Runtime contract

1. Persisted conversation state produces an expanded analysis query for follow-ups.
2. Qdrant retrieves candidate columns and metrics while Elasticsearch retrieves real field values.
3. The optional Cross-Encoder reranks candidates; absent endpoint falls back to dense ranking without failure.
4. Dependency expansion adds temporal fields and join keys.
5. The model generates one SQL statement; `sqlglot` rejects multi-statements and non-read-only operations.
6. MySQL `EXPLAIN` validates the query. At most one correction is attempted, then execution has a timeout and row cap.
