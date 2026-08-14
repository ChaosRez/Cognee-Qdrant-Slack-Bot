from pathlib import Path

import numpy as np

from seal_bot.catalog import DEFAULT_CATALOG_PATH, DEFAULT_DEMO_IMAGE, catalog_fingerprint
from seal_bot.models import SearchMatch
from seal_bot.service import SealMatcher


class FakeEmbedder:
    def __init__(self):
        self.calls = []

    def encode_images(self, paths):
        self.calls.append(tuple(paths))
        return np.tile(np.array([[1.0, 0.0, 0.0]], dtype=np.float32), (len(paths), 1))


class FakeStore:
    def __init__(self):
        self.indexed = False
        self.cases = {}

    def catalog_is_current(self, products, fingerprint):
        return self.indexed

    def index_catalog(self, products, vectors, fingerprint):
        assert fingerprint == catalog_fingerprint(DEFAULT_CATALOG_PATH)
        assert len(products) == len(vectors) == 10
        self.indexed = True

    def search_catalog(self, vector, products_by_sku, limit):
        order = ["F2037", "F3267"] + [sku for sku in products_by_sku if sku not in {"F2037", "F3267"}]
        return tuple(
            SearchMatch(products_by_sku[sku], score=1.0 - rank / 100, raw_rank=rank)
            for rank, sku in enumerate(order, start=1)
        )

    def save_case(self, result, vector):
        self.cases[result.case_id] = result.to_payload()

    def confirm_case(self, case_id, sku, actor):
        if case_id not in self.cases:
            raise KeyError(case_id)
        return self.cases[case_id]

    def counts(self):
        return {"catalog": 10 if self.indexed else 0, "cases": len(self.cases)}


def test_exact_demo_override_preserves_raw_rank():
    matcher = SealMatcher(embedder=FakeEmbedder(), store=FakeStore())
    result = matcher.match_image(DEFAULT_DEMO_IMAGE, query_label=DEFAULT_DEMO_IMAGE.name, actor="U123")

    assert result.raw_matches[0].product.sku == "F2037"
    assert result.best.product.sku == "F3267"
    assert result.best.raw_rank == 2
    assert result.override_applied is True
    assert result.override_reason


def test_filename_must_also_match_for_override(tmp_path: Path):
    renamed = tmp_path / "different-name.jpg"
    renamed.write_bytes(DEFAULT_DEMO_IMAGE.read_bytes())
    matcher = SealMatcher(embedder=FakeEmbedder(), store=FakeStore())

    result = matcher.match_image(renamed)

    assert result.best.product.sku == "F2037"
    assert result.override_reason is None
    assert result.override_applied is False


def test_confirmation_produces_cognee_fact():
    store = FakeStore()
    matcher = SealMatcher(embedder=FakeEmbedder(), store=store)
    result = matcher.match_image(DEFAULT_DEMO_IMAGE, query_label=DEFAULT_DEMO_IMAGE.name)

    fact = matcher.confirm(result.case_id, "f3267", actor="U123")

    assert "Human-confirmed seal match" in fact
    assert "SKU F3267" in fact
    assert "raw rank was 2" in fact


def test_catalog_memory_handles_unknown_dimensions():
    matcher = SealMatcher(embedder=FakeEmbedder(), store=FakeStore())

    document = matcher.catalog_memory_document()

    assert "product F0737" in document
    assert "width not listed" in document
    assert "recommended groove not listed" in document
