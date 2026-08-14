"""Seal product matching backed by Hyper3-CLIP and Qdrant."""

from .models import CatalogProduct, MatchResult, SearchMatch
from .service import SealMatcher

__all__ = ["CatalogProduct", "MatchResult", "SearchMatch", "SealMatcher"]

