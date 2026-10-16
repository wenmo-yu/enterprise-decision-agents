"""问数子图的本地基础设施配置。"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AnalyticsSettings:
    """所有数据基础设施均在当前应用内连接，不经过 HTTP 问数服务。"""

    metadata_database_url: str
    warehouse_database_url: str
    qdrant_url: str
    elasticsearch_url: str
    value_index: str
    column_collection: str
    metric_collection: str
    embedding_model: str
    max_rows: int
    timeout_seconds: float

    @classmethod
    def from_env(cls) -> "AnalyticsSettings":
        return cls(
            metadata_database_url=os.getenv("ANALYTICS_METADATA_DATABASE_URL", ""),
            warehouse_database_url=os.getenv("ANALYTICS_WAREHOUSE_DATABASE_URL", ""),
            qdrant_url=os.getenv("ANALYTICS_QDRANT_URL", "http://localhost:6333"),
            elasticsearch_url=os.getenv("ANALYTICS_ELASTICSEARCH_URL", "http://localhost:9200"),
            value_index=os.getenv("ANALYTICS_VALUE_INDEX", "analytics_values"),
            column_collection=os.getenv("ANALYTICS_COLUMN_COLLECTION", "analytics_columns"),
            metric_collection=os.getenv("ANALYTICS_METRIC_COLLECTION", "analytics_metrics"),
            embedding_model=os.getenv("ANALYTICS_EMBEDDING_MODEL", os.getenv("RAG_EMBEDDING_MODEL", "text-embedding-v4")),
            max_rows=max(1, int(os.getenv("ANALYTICS_MAX_ROWS", "1000"))),
            timeout_seconds=max(1.0, float(os.getenv("ANALYTICS_TIMEOUT_SECONDS", "15"))),
        )

    def validate(self) -> None:
        missing = [
            name
            for name, value in (
                ("ANALYTICS_METADATA_DATABASE_URL", self.metadata_database_url),
                ("ANALYTICS_WAREHOUSE_DATABASE_URL", self.warehouse_database_url),
            )
            if not value
        ]
        if missing:
            raise ValueError(f"嵌入式问数未配置：{', '.join(missing)}")
