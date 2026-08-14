from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from qdrant_client import QdrantClient, models

from .models import CatalogProduct, MatchResult, SearchMatch


CATALOG_COLLECTION = "seal_catalog_v1"
CASES_COLLECTION = "seal_cases_v1"


def _point_id(prefix: str, value: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"seal-bot:{prefix}:{value}"))


class QdrantStore:
    def __init__(self, client: QdrantClient):
        self.client = client

    @classmethod
    def from_env(cls, default_path: Path) -> "QdrantStore":
        url = os.environ.get("SEAL_QDRANT_URL", "").strip()
        api_key = os.environ.get("SEAL_QDRANT_API_KEY", "").strip() or None
        if url:
            return cls(QdrantClient(url=url, api_key=api_key))
        path = Path(os.environ.get("SEAL_QDRANT_PATH", str(default_path))).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return cls(QdrantClient(path=str(path)))

    def _ensure_collection(self, name: str, dimension: int) -> None:
        if self.client.collection_exists(name):
            info = self.client.get_collection(name)
            configured = info.config.params.vectors
            configured_size = getattr(configured, "size", None)
            if configured_size is not None and configured_size != dimension:
                raise RuntimeError(
                    f"Qdrant collection {name} has dimension {configured_size}, expected {dimension}. "
                    "Use a new SEAL_QDRANT_PATH or collection version."
                )
            return
        self.client.create_collection(
            collection_name=name,
            vectors_config=models.VectorParams(size=dimension, distance=models.Distance.COSINE),
        )

    def index_catalog(
        self,
        products: Sequence[CatalogProduct],
        vectors: np.ndarray,
        fingerprint: str,
    ) -> None:
        if len(products) != len(vectors):
            raise ValueError("Product and vector counts differ")
        self._ensure_collection(CATALOG_COLLECTION, int(vectors.shape[1]))
        points = []
        for product, vector in zip(products, vectors, strict=True):
            payload = product.to_payload()
            payload.update({"kind": "catalog_product", "catalog_fingerprint": fingerprint})
            points.append(
                models.PointStruct(
                    id=_point_id("catalog", product.sku),
                    vector=vector.tolist(),
                    payload=payload,
                )
            )
        self.client.upsert(collection_name=CATALOG_COLLECTION, points=points, wait=True)

    def catalog_is_current(self, products: Sequence[CatalogProduct], fingerprint: str) -> bool:
        if not self.client.collection_exists(CATALOG_COLLECTION):
            return False
        records = self.client.retrieve(
            collection_name=CATALOG_COLLECTION,
            ids=[_point_id("catalog", product.sku) for product in products],
            with_payload=True,
            with_vectors=False,
        )
        return len(records) == len(products) and all(
            record.payload and record.payload.get("catalog_fingerprint") == fingerprint for record in records
        )

    def search_catalog(
        self,
        vector: np.ndarray,
        products_by_sku: dict[str, CatalogProduct],
        limit: int,
    ) -> tuple[SearchMatch, ...]:
        response = self.client.query_points(
            collection_name=CATALOG_COLLECTION,
            query=vector.tolist(),
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        matches: list[SearchMatch] = []
        for rank, point in enumerate(response.points, start=1):
            sku = str((point.payload or {}).get("sku", ""))
            product = products_by_sku.get(sku)
            if product:
                matches.append(SearchMatch(product=product, score=float(point.score), raw_rank=rank))
        return tuple(matches)

    def save_case(self, result: MatchResult, query_vector: np.ndarray) -> None:
        self._ensure_collection(CASES_COLLECTION, int(query_vector.shape[0]))
        payload = result.to_payload()
        payload.update({"kind": "seal_case", "created_at": datetime.now(timezone.utc).isoformat()})
        self.client.upsert(
            collection_name=CASES_COLLECTION,
            points=[
                models.PointStruct(
                    id=_point_id("case", result.case_id),
                    vector=query_vector.tolist(),
                    payload=payload,
                )
            ],
            wait=True,
        )

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        if not self.client.collection_exists(CASES_COLLECTION):
            return None
        records = self.client.retrieve(
            collection_name=CASES_COLLECTION,
            ids=[_point_id("case", case_id)],
            with_payload=True,
            with_vectors=False,
        )
        return dict(records[0].payload) if records and records[0].payload else None

    def confirm_case(self, case_id: str, sku: str, actor: str) -> dict[str, Any]:
        case = self.get_case(case_id)
        if case is None:
            raise KeyError(f"Unknown case ID: {case_id}")
        confirmation = {
            "sku": sku,
            "actor": actor,
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
        }
        self.client.set_payload(
            collection_name=CASES_COLLECTION,
            payload={"confirmation": confirmation},
            points=[_point_id("case", case_id)],
            wait=True,
        )
        case["confirmation"] = confirmation
        return case

    def counts(self) -> dict[str, int]:
        result = {"catalog": 0, "cases": 0}
        if self.client.collection_exists(CATALOG_COLLECTION):
            result["catalog"] = int(self.client.count(CATALOG_COLLECTION, exact=True).count)
        if self.client.collection_exists(CASES_COLLECTION):
            result["cases"] = int(self.client.count(CASES_COLLECTION, exact=True).count)
        return result

    def close(self) -> None:
        self.client.close()
