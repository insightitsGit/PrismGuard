from __future__ import annotations

import argparse
import json
import os
import sys

from prismguard.data import import_bundled_seed, load_bundled_seed
from prismguard.seed.importer import import_seeds
from prismguard.seed.parse import parse_seed_sources
from prismguard.storage import create_storage, create_storage_from_env


def _storage_for_cli(backend: str | None):
    if backend is not None:
        return create_storage(backend)
    if os.environ.get("PRISMGUARD_STORAGE_BACKEND"):
        return create_storage_from_env()
    if os.environ.get("PRISMGUARD_STORAGE_DSN"):
        return create_storage("pgvector", dsn=os.environ["PRISMGUARD_STORAGE_DSN"])
    return create_storage("memory")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="prismguard-seed", description="PrismGuard seed corpus importer")
    sub = parser.add_subparsers(dest="command", required=True)

    import_cmd = sub.add_parser("import", help="Import seed from one or more sources")
    import_cmd.add_argument(
        "sources",
        nargs="*",
        help="Seed files, directories, or @manifest.txt (optional with --bundled)",
    )
    import_cmd.add_argument(
        "--bundled",
        action="store_true",
        help="Import the packaged v0 seed corpus from prismguard/data/seeds/v0/",
    )
    import_cmd.add_argument(
        "--format",
        default="auto",
        choices=["auto", "yaml", "json", "jsonl", "csv", "markdown"],
        help="Format for all sources (auto detects per file by default)",
    )
    import_cmd.add_argument(
        "--mode",
        default="update",
        choices=["update", "replace"],
        help="update=upsert/merge (default); replace=delete then load",
    )
    import_cmd.add_argument(
        "--scope",
        default="all",
        help="all (default) or category:<slug> — only meaningful with --mode replace",
    )
    import_cmd.add_argument("--recursive", action="store_true", help="When a source is a directory, include subfolders")
    import_cmd.add_argument("--dry-run", action="store_true", help="Validate and report without writing")
    import_cmd.add_argument(
        "--confirm-replace-all",
        action="store_true",
        help="Required with --mode replace --scope all",
    )
    import_cmd.add_argument("--force", action="store_true", help="Import despite validation warnings/errors")
    import_cmd.add_argument(
        "--backend",
        default=None,
        help="Storage backend override (default from PRISMGUARD_STORAGE_BACKEND or memory)",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command != "import":
        parser.error(f"Unknown command {args.command!r}")

    if not args.bundled and not args.sources:
        parser.error("Provide at least one source path or use --bundled")

    storage = _storage_for_cli(args.backend)

    try:
        if args.bundled:
            report = import_bundled_seed(
                storage,
                mode=args.mode,
                scope=args.scope,
                dry_run=args.dry_run,
                confirm_replace_all=args.confirm_replace_all,
            )
        else:
            parsed = parse_seed_sources(args.sources, format_name=args.format, recursive=args.recursive)
            report = import_seeds(
                storage,
                parsed,
                mode=args.mode,
                scope=args.scope,
                dry_run=args.dry_run,
                confirm_replace_all=args.confirm_replace_all,
                force=args.force,
            )
    finally:
        storage.close()

    print(json.dumps({
        "mode": report.mode,
        "scope": report.scope,
        "source_files": report.source_files,
        "inserted": report.inserted,
        "updated": report.updated,
        "skipped": report.skipped,
        "errored": report.errored,
        "dry_run": report.dry_run,
        "warnings": report.warnings,
    }, indent=2))

    if report.errored:
        sys.exit(1)


if __name__ == "__main__":
    main()
