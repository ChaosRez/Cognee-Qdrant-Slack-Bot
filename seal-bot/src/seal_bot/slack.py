from __future__ import annotations

import os
import re
import ssl
import tempfile
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

import aiohttp

from .catalog import DEFAULT_DEMO_IMAGE
from .models import MatchResult, format_mm


FILE_ID_PATTERN = re.compile(r"(?<![A-Z0-9])(F[A-Z0-9]{7,})(?![A-Z0-9])", re.IGNORECASE)
MAX_IMAGE_BYTES = 12 * 1024 * 1024


@dataclass(frozen=True)
class ResolvedSlackImage:
    path: Path
    original_name: str
    source: str


def parse_slack_file_id(value: str) -> str | None:
    match = FILE_ID_PATTERN.search(value.strip())
    return match.group(1).upper() if match else None


class SlackImageResolver:
    def __init__(self, bot_token: str | None = None, ssl_context: ssl.SSLContext | None = None):
        self.bot_token = bot_token or os.environ.get("SLACK_BOT_TOKEN", "")
        self.ssl_context = ssl_context

    @asynccontextmanager
    async def resolve(self, reference: str) -> AsyncIterator[ResolvedSlackImage]:
        reference = reference.strip()
        if reference.lower() == "demo":
            yield ResolvedSlackImage(
                path=DEFAULT_DEMO_IMAGE,
                original_name=DEFAULT_DEMO_IMAGE.name,
                source="bundled-demo",
            )
            return

        file_id = parse_slack_file_id(reference)
        if not file_id:
            raise ValueError("Use `demo`, a Slack file ID, or a Slack file permalink")
        if not self.bot_token:
            raise RuntimeError("SLACK_BOT_TOKEN is required to read uploaded Slack images")

        headers = {"Authorization": f"Bearer {self.bot_token}"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(
                "https://slack.com/api/files.info",
                params={"file": file_id},
                ssl=self.ssl_context,
            ) as response:
                response.raise_for_status()
                body = await response.json()
            if not body.get("ok"):
                raise RuntimeError(f"Slack files.info failed: {body.get('error', 'unknown_error')}")
            file = body.get("file", {})
            mimetype = str(file.get("mimetype", ""))
            if not mimetype.startswith("image/"):
                raise ValueError(f"Slack file {file_id} is not an image")
            size = int(file.get("size") or 0)
            if size > MAX_IMAGE_BYTES:
                raise ValueError("Image is larger than the 12 MB demo limit")
            download_url = file.get("url_private_download") or file.get("url_private")
            if not download_url:
                raise RuntimeError("Slack did not return a downloadable private URL")
            original_name = Path(str(file.get("name") or f"{file_id}.img")).name

            with tempfile.TemporaryDirectory(prefix="seal-bot-") as directory:
                destination = Path(directory) / original_name
                downloaded = 0
                async with session.get(download_url, ssl=self.ssl_context) as response:
                    response.raise_for_status()
                    with destination.open("wb") as target:
                        async for chunk in response.content.iter_chunked(64 * 1024):
                            downloaded += len(chunk)
                            if downloaded > MAX_IMAGE_BYTES:
                                raise ValueError("Downloaded image exceeded the 12 MB demo limit")
                            target.write(chunk)
                yield ResolvedSlackImage(destination, original_name, f"slack:{file_id}")


def match_response(result: MatchResult) -> dict:
    best = result.best
    product = best.product
    score = f"{best.score:.3f}"
    override_line = ""
    if result.override_reason:
        override_line = (
            f"\n*Demo ground truth:* exact file + checksum recognized. "
            f"Raw Hyper3/Qdrant rank: *#{best.raw_rank}*."
        )
    alternatives = result.displayed_matches[1:4]
    alternative_lines = "\n".join(
        f"• <{item.product.product_url}|{item.product.sku}> — height "
        f"{format_mm(item.product.height_mm)}, width {format_mm(item.product.width_mm)}, "
        f"score {item.score:.3f} (raw #{item.raw_rank})"
        for item in alternatives
    ) or "No alternatives returned."
    return {
        "response_type": "ephemeral",
        "text": f"Best seal match: {product.sku} — verify dimensions before ordering.",
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": f"Best match: {product.sku}"}},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*<{product.product_url}|{product.name}>*\n"
                        f"Visual similarity: *{score}*{override_line}\n"
                        f"{product.material}, {product.color} · height {format_mm(product.height_mm)} · "
                        f"width {format_mm(product.width_mm)} · groove {format_mm(product.groove_width_mm)}"
                    ),
                },
                "accessory": {
                    "type": "image",
                    "image_url": product.image_url,
                    "alt_text": f"Product profile for {product.sku}",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "⚠️ *Always measure the profile and groove before ordering; an image match alone is not conclusive.*",
                    }
                ],
            },
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Alternatives*\n{alternative_lines}"}},
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Case `{result.case_id}` · Confirm with `/seal-confirm {result.case_id} {product.sku}`",
                    }
                ],
            },
        ],
    }
