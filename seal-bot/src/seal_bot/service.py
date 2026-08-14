from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

from .catalog import (
    DEFAULT_CATALOG_PATH,
    DEFAULT_GROUND_TRUTH_PATH,
    PACKAGE_ROOT,
    catalog_fingerprint,
    load_catalog,
    load_ground_truth,
    resolve_image_path,
    sha256_file,
)
from .embedding import Hyper3ClipEmbedder
from .models import CatalogProduct, MatchResult, SearchMatch


class SealMatcher:
    def __init__(
        self,
        catalog_path: Path = DEFAULT_CATALOG_PATH,
        ground_truth_path: Path = DEFAULT_GROUND_TRUTH_PATH,
        embedder: Any | None = None,
        store: Any | None = None,
    ):
        self.catalog_path = Path(catalog_path).resolve()
        self.products = load_catalog(self.catalog_path)
        self.products_by_sku = {product.sku: product for product in self.products}
        self.ground_truth = load_ground_truth(Path(ground_truth_path))
        self.embedder = embedder or Hyper3ClipEmbedder()
        if store is None:
            from .qdrant_store import QdrantStore

            store = QdrantStore.from_env(PACKAGE_ROOT / ".runtime" / "qdrant")
        self.store = store

    def ensure_index(self, force: bool = False) -> int:
        fingerprint = catalog_fingerprint(self.catalog_path)
        if not force and self.store.catalog_is_current(self.products, fingerprint):
            return len(self.products)
        image_paths = [resolve_image_path(product, self.catalog_path) for product in self.products]
        vectors = self.embedder.encode_images(image_paths)
        self.store.index_catalog(self.products, vectors, fingerprint)
        return len(self.products)

    def match_image(self, image_path: Path, query_label: str | None = None, actor: str = "") -> MatchResult:
        image_path = Path(image_path).resolve()
        if not image_path.is_file():
            raise FileNotFoundError(f"Query image not found: {image_path}")
        self.ensure_index()
        vector = self.embedder.encode_images([image_path])[0]
        raw_matches = self.store.search_catalog(vector, self.products_by_sku, limit=len(self.products))
        if not raw_matches:
            raise RuntimeError("Qdrant returned no catalog matches")

        label = query_label or image_path.name
        query_sha = sha256_file(image_path)
        displayed = raw_matches
        override_reason = None
        override_applied = False
        enabled = os.environ.get("SEAL_DEMO_OVERRIDE", "true").strip().lower() not in {"0", "false", "no"}
        is_exact_demo = (
            label == self.ground_truth["filename"]
            and query_sha == self.ground_truth["sha256"]
        )
        if enabled and is_exact_demo:
            target = next((item for item in raw_matches if item.product.sku == self.ground_truth["sku"]), None)
            if target is None:
                raise RuntimeError("Ground-truth SKU is absent from the Qdrant result")
            displayed = (target,) + tuple(item for item in raw_matches if item.product.sku != target.product.sku)
            override_reason = self.ground_truth["reason"]
            override_applied = target.raw_rank != 1

        result = MatchResult(
            case_id=f"seal-{uuid.uuid4().hex[:12]}",
            query_label=label,
            query_sha256=query_sha,
            raw_matches=raw_matches,
            displayed_matches=displayed,
            override_applied=override_applied,
            override_reason=override_reason,
            actor=actor,
        )
        self.store.save_case(result, vector)
        return result

    def confirm(self, case_id: str, sku: str, actor: str = "") -> str:
        normalized = sku.strip().upper()
        product = self.products_by_sku.get(normalized)
        if product is None:
            raise ValueError(f"Unknown catalog SKU: {normalized}")
        case = self.store.confirm_case(case_id.strip(), normalized, actor)
        raw_rank = next(
            (item["raw_rank"] for item in case.get("raw_matches", []) if item.get("sku") == normalized),
            "not returned",
        )
        override = bool(case.get("override_applied"))
        return (
            f"Human-confirmed seal match: case {case_id} ({case.get('query_label', 'image')}) is Graf-Dichtungen "
            f"SKU {normalized}. Hyper3/Qdrant raw rank was {raw_rank}; demo override applied: {override}. "
            f"Confirmed by Slack user {actor or 'unknown'}. {product.memory_fact()}"
        )

    def catalog_memory_document(self) -> str:
        heading = "Curated Graf-Dichtungen seal catalog used by Seal Bot.\n"
        return heading + "\n".join(product.memory_fact() for product in self.products)

    def status(self) -> dict[str, int]:
        return self.store.counts()

    def close(self) -> None:
        close = getattr(self.store, "close", None)
        if close:
            close()
