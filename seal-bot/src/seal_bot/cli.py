from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from .service import SealMatcher


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Index and test the Seal Bot matcher")
    commands = parser.add_subparsers(dest="command", required=True)
    index = commands.add_parser("index", help="Embed the curated catalog and upsert it to Qdrant")
    index.add_argument("--force", action="store_true", help="Re-embed even when the catalog fingerprint matches")
    match = commands.add_parser("match", help="Match a local image through Hyper3 and Qdrant")
    match.add_argument("image", type=Path)
    match.add_argument("--label", help="Original filename used for the auditable demo override")
    confirm = commands.add_parser("confirm", help="Confirm a saved case in Qdrant")
    confirm.add_argument("case_id")
    confirm.add_argument("sku")
    confirm.add_argument("--actor", default="cli")
    commands.add_parser("status", help="Show Qdrant catalog and case counts")
    return parser


def main() -> None:
    load_dotenv()
    args = build_parser().parse_args()
    matcher = None
    try:
        matcher = SealMatcher()
        if args.command == "index":
            count = matcher.ensure_index(force=args.force)
            print(f"Indexed {count} seal products in Qdrant")
        elif args.command == "match":
            result = matcher.match_image(args.image, query_label=args.label)
            print(json.dumps(result.to_payload(), ensure_ascii=False, indent=2))
        elif args.command == "confirm":
            print(matcher.confirm(args.case_id, args.sku, actor=args.actor))
        elif args.command == "status":
            print(json.dumps(matcher.status(), indent=2))
    except Exception as exc:
        raise SystemExit(f"seal-bot: error: {exc}") from exc
    finally:
        if matcher is not None:
            matcher.close()


if __name__ == "__main__":
    main()
