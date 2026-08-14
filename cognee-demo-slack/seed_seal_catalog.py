"""Seed the curated seal catalog into Cognee memory.

Run from ``cognee-demo-slack`` after installing the repository requirements:

    python seed_seal_catalog.py
"""

import asyncio
import sys
from pathlib import Path

import cognee


REPO_ROOT = Path(__file__).resolve().parents[1]
SEAL_BOT_ROOT = REPO_ROOT / "seal-bot"
sys.path.insert(0, str(SEAL_BOT_ROOT / "src"))

from seal_bot.service import SealMatcher  # noqa: E402


async def main() -> None:
    matcher = SealMatcher()
    try:
        document = matcher.catalog_memory_document()
        await cognee.remember(document, dataset_name="slack")
        print(f"Seeded {len(matcher.products)} seal products into Cognee dataset 'slack'.")
    finally:
        matcher.close()


if __name__ == "__main__":
    asyncio.run(main())
