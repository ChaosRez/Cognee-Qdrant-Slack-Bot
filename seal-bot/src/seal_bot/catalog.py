from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .models import CatalogProduct


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG_PATH = PACKAGE_ROOT / "catalog.json"
DEFAULT_GROUND_TRUTH_PATH = PACKAGE_ROOT / "demo-ground-truth.json"
DEFAULT_DEMO_IMAGE = PACKAGE_ROOT / "assets" / "IMG_20260808_000446_905.jpg"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_catalog(path: Path = DEFAULT_CATALOG_PATH) -> tuple[CatalogProduct, ...]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    products = tuple(CatalogProduct.from_dict(item) for item in raw)
    skus = [product.sku for product in products]
    if not products:
        raise ValueError("Seal catalog is empty")
    if len(skus) != len(set(skus)):
        raise ValueError("Seal catalog contains duplicate SKUs")
    for product in products:
        image = resolve_image_path(product, path)
        if not image.is_file():
            raise FileNotFoundError(f"Missing catalog image for {product.sku}: {image}")
    return products


def resolve_image_path(product: CatalogProduct, catalog_path: Path = DEFAULT_CATALOG_PATH) -> Path:
    return (catalog_path.parent / product.image_path).resolve()


def catalog_fingerprint(path: Path = DEFAULT_CATALOG_PATH) -> str:
    digest = hashlib.sha256(path.read_bytes())
    for product in load_catalog(path):
        digest.update(product.sku.encode())
        digest.update(sha256_file(resolve_image_path(product, path)).encode())
    return digest.hexdigest()


def load_ground_truth(path: Path = DEFAULT_GROUND_TRUTH_PATH) -> dict[str, str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    required = {"filename", "sha256", "sku", "reason"}
    missing = required.difference(value)
    if missing:
        raise ValueError(f"Demo ground truth is missing: {', '.join(sorted(missing))}")
    return value

