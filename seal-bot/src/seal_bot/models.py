from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CatalogProduct:
    sku: str
    name: str
    family: str
    color: str
    material: str
    height_mm: float | None
    width_mm: float | None
    groove_width_mm: float | None
    lip: bool
    foot_shape: str
    hollow_chambers: int
    image_path: str
    image_url: str
    product_url: str
    source_note: str
    selection_reason: str
    traits: tuple[str, ...]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CatalogProduct":
        data = dict(value)
        data["traits"] = tuple(data.get("traits", ()))
        return cls(**data)

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["traits"] = list(self.traits)
        return payload

    def memory_fact(self) -> str:
        lip = "with a sealing lip" if self.lip else "without a sealing lip"
        traits = ", ".join(self.traits)
        height = format_mm(self.height_mm)
        width = format_mm(self.width_mm)
        groove = format_mm(self.groove_width_mm)
        return (
            f"Graf-Dichtungen product {self.sku} is {self.name}. It is a {self.color} "
            f"{self.material} {self.family} {lip}. Dimensions: height {height}, width {width}, "
            f"recommended groove {groove}. It has a {self.foot_shape} foot and "
            f"{self.hollow_chambers} hollow chamber(s). "
            f"Visual traits: {traits}. Product page: {self.product_url}"
        )


def format_mm(value: float | None) -> str:
    return f"{value:g} mm" if value is not None else "not listed"


@dataclass(frozen=True)
class SearchMatch:
    product: CatalogProduct
    score: float
    raw_rank: int

    def to_payload(self) -> dict[str, Any]:
        return {
            "sku": self.product.sku,
            "score": self.score,
            "raw_rank": self.raw_rank,
        }


@dataclass(frozen=True)
class MatchResult:
    case_id: str
    query_label: str
    query_sha256: str
    raw_matches: tuple[SearchMatch, ...]
    displayed_matches: tuple[SearchMatch, ...]
    override_applied: bool
    override_reason: str | None
    actor: str

    @property
    def best(self) -> SearchMatch:
        return self.displayed_matches[0]

    def to_payload(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "query_label": self.query_label,
            "query_sha256": self.query_sha256,
            "raw_matches": [match.to_payload() for match in self.raw_matches],
            "displayed_matches": [match.to_payload() for match in self.displayed_matches],
            "override_applied": self.override_applied,
            "override_reason": self.override_reason,
            "actor": self.actor,
        }
