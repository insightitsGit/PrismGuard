from __future__ import annotations

import argparse
import json
import os
import sys

from prismguard.seed import import_bundled_seed, load_bundled_seed
from prismguard.seed.importer import import_seeds
from prismguard.seed.parse import parse_seed_sources
from prismguard.storage import create_storage, create_storage_from_env
from prismguard.taxonomy.pipeline import PostSeedReport


def _storage_for_cli(backend: str | None):
    if backend is not None:
        return create_storage(backend)
    if os.environ.get("PRISMGUARD_STORAGE_BACKEND"):
        return create_storage_from_env()
    if os.environ.get("PRISMGUARD_STORAGE_DSN"):
        return create_storage("pgvector", dsn=os.environ["PRISMGUARD_STORAGE_DSN"])
    return create_storage("memory")


def _taxonomy_output(taxonomy_report: PostSeedReport) -> dict:
    return {
        "embedder": taxonomy_report.embedder_name,
        "ingest": {
            "total_entries": taxonomy_report.ingest.total_entries,
            "embedded": taxonomy_report.ingest.embedded,
            "skipped_already_embedded": taxonomy_report.ingest.skipped_already_embedded,
            "duration_seconds": round(taxonomy_report.ingest.duration_seconds, 3),
        },
        "coverage": taxonomy_report.coverage.to_dict(),
        "llm_reduction_estimate": taxonomy_report.llm_reduction,
    }


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
        help="Import the packaged seed corpus from prismguard/seed/corpus/",
    )
    import_cmd.add_argument(
        "--profile",
        default="authored",
        choices=["authored", "full"],
        help="Bundled corpus profile: authored (default, fast) or full (includes external datasets)",
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
    import_cmd.add_argument(
        "--skip-taxonomy",
        action="store_true",
        help="Skip post-import prismRAG taxonomy mapping + dual-vector embed",
    )
    import_cmd.add_argument(
        "--domain",
        default=None,
        help="Optional domain slug overlay after import (bundled or custom)",
    )
    import_cmd.add_argument(
        "--force-embed",
        action="store_true",
        help="Re-embed all seed entries even if vectors already exist",
    )
    return parser


def _import_domain_overlay(storage, domain: str, *, dry_run: bool, skip_taxonomy: bool) -> dict:
    from prismguard.domains.registry import get_domain_pack
    from prismguard.seed.parse import parse_seed_file

    pack = get_domain_pack(domain)
    parsed = parse_seed_file(pack.overlay_path)
    report = import_seeds(
        storage,
        parsed,
        mode="update",
        dry_run=dry_run,
        skip_taxonomy=skip_taxonomy,
    )
    return {
        "domain": pack.name,
        "overlay": str(pack.overlay_path),
        "inserted": report.inserted,
        "updated": report.updated,
    }


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command != "import":
        parser.error(f"Unknown command {args.command!r}")

    if not args.bundled and not args.sources:
        parser.error("Provide at least one source path or use --bundled")

    storage = _storage_for_cli(args.backend)

    try:
        domain_report = None
        if args.bundled:
            report = import_bundled_seed(
                storage,
                mode=args.mode,
                scope=args.scope,
                dry_run=args.dry_run,
                confirm_replace_all=args.confirm_replace_all,
                profile=args.profile,
                skip_taxonomy=args.skip_taxonomy,
                force_embed=args.force_embed,
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
                skip_taxonomy=args.skip_taxonomy,
                force_embed=args.force_embed,
            )
        if args.domain and not args.dry_run:
            domain_report = _import_domain_overlay(
                storage,
                args.domain,
                dry_run=False,
                skip_taxonomy=args.skip_taxonomy,
            )
        elif args.domain and args.dry_run:
            domain_report = _import_domain_overlay(
                storage,
                args.domain,
                dry_run=True,
                skip_taxonomy=True,
            )
        else:
            domain_report = None
    finally:
        storage.close()

    output: dict = {
        "mode": report.mode,
        "scope": report.scope,
        "source_files": report.source_files,
        "inserted": report.inserted,
        "updated": report.updated,
        "skipped": report.skipped,
        "errored": report.errored,
        "dry_run": report.dry_run,
        "warnings": report.warnings,
    }
    if report.taxonomy is not None:
        output["taxonomy"] = _taxonomy_output(report.taxonomy)
    if domain_report is not None:
        output["domain_pack"] = domain_report

    print(json.dumps(output, indent=2))

    if report.errored:
        sys.exit(1)


if __name__ == "__main__":
    main()
