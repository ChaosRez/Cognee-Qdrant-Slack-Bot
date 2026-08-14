import numpy as np
from qdrant_client import QdrantClient

from seal_bot.catalog import load_catalog
from seal_bot.models import MatchResult
from seal_bot.qdrant_store import QdrantStore


def test_real_qdrant_index_query_and_confirmation(tmp_path):
    products = load_catalog()[:2]
    products_by_sku = {product.sku: product for product in products}
    vectors = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32)
    store = QdrantStore(QdrantClient(path=str(tmp_path / "qdrant")))
    try:
        store.index_catalog(products, vectors, fingerprint="test-fingerprint")
        assert store.catalog_is_current(products, "test-fingerprint")

        matches = store.search_catalog(vectors[0], products_by_sku, limit=2)
        assert [match.product.sku for match in matches] == [products[0].sku, products[1].sku]

        result = MatchResult(
            case_id="seal-qdrant-test",
            query_label="query.jpg",
            query_sha256="abc",
            raw_matches=matches,
            displayed_matches=matches,
            override_applied=False,
            override_reason=None,
            actor="U123",
        )
        store.save_case(result, vectors[0])
        case = store.confirm_case(result.case_id, products[0].sku, "U123")

        assert case["confirmation"]["sku"] == products[0].sku
        assert store.counts() == {"catalog": 2, "cases": 1}
    finally:
        store.close()

