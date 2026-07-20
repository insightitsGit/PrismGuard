from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from prismguard.config.loader import load_triage_config
from prismguard.context.loader import (
    load_lexicon_file,
    load_lexicon_from_sql_table,
    resolve_lexicon_path,
)
from prismguard.context.templates import lexicon_to_parsed_seed
from prismguard.domains.registry import get_domain_pack, list_domains
from prismguard.seed import import_bundled_seed, import_seeds
from prismguard.storage import create_storage, create_storage_from_env


def _storage_for_cli(backend: str | None):
    if backend is not None:
        return create_storage(backend)
    if os.environ.get("PRISMGUARD_STORAGE_BACKEND"):
        return create_storage_from_env()
    if os.environ.get("PRISMGUARD_STORAGE_DSN"):
        return create_storage("pgvector", dsn=os.environ["PRISMGUARD_STORAGE_DSN"])
    return create_storage("memory")


def _import_domain(storage, domain: str, *, dry_run: bool) -> dict:
    pack = get_domain_pack(domain)
    from prismguard.seed.parse import parse_seed_file

    parsed = parse_seed_file(pack.overlay_path)
    report = import_seeds(
        storage,
        parsed,
        mode="update",
        dry_run=dry_run,
        skip_taxonomy=dry_run,
    )
    return {
        "domain": pack.name,
        "label": pack.label,
        "overlay": str(pack.overlay_path),
        "inserted": report.inserted,
        "updated": report.updated,
        "skipped": report.skipped,
        "dry_run": report.dry_run,
    }


def _import_tenant_context(
    storage,
    lexicon_path: Path | None,
    *,
    dry_run: bool,
    apply_templates: bool,
) -> dict:
    if lexicon_path is None:
        return {"skipped": True, "reason": "no tenant lexicon provided"}
    lexicon = load_lexicon_file(lexicon_path)
    result: dict = {
        "source": str(lexicon_path),
        "domain": lexicon.domain,
        "entity_count": len(lexicon.entities),
        "dry_run": dry_run,
    }
    if not apply_templates:
        result["templates_skipped"] = True
        return result
    parsed = lexicon_to_parsed_seed(lexicon)
    report = import_seeds(storage, parsed, mode="update", dry_run=dry_run, skip_taxonomy=dry_run)
    result.update(
        {
            "inserted": report.inserted,
            "updated": report.updated,
            "skipped_entries": report.skipped,
            "template_entries": len(parsed.entries),
        }
    )
    return result


def cmd_init(args: argparse.Namespace) -> int:
    if args.context_file or args.context_table:
        from prismguard.licensing.features import ENTERPRISE_TENANT, require_feature

        require_feature(ENTERPRISE_TENANT)
    storage = _storage_for_cli(args.backend)
    output: dict = {"steps": []}
    try:
        bundled = import_bundled_seed(
            storage,
            profile=args.profile,
            mode="update",
            dry_run=args.dry_run,
            skip_taxonomy=args.dry_run,
        )
        output["steps"].append(
            {
                "step": "bundled_seed",
                "profile": args.profile,
                "inserted": bundled.inserted,
                "updated": bundled.updated,
                "dry_run": bundled.dry_run,
            }
        )

        if args.domain:
            output["steps"].append(
                _import_domain(storage, args.domain, dry_run=args.dry_run)
            )

        lexicon_path: Path | None = None
        if args.context_file:
            lexicon_path = Path(args.context_file)
        elif args.context_table and args.context_dsn:
            lexicon = load_lexicon_from_sql_table(args.context_dsn, args.context_table)
            if args.dry_run:
                output["steps"].append(
                    {
                        "step": "tenant_context",
                        "source": f"sql:{args.context_table}",
                        "entity_count": len(lexicon.entities),
                        "dry_run": True,
                    }
                )
            else:
                tmp = Path.cwd() / ".prismguard_tenant_lexicon.yaml"
                import yaml

                tmp.write_text(
                    yaml.safe_dump(lexicon.model_dump(), sort_keys=False),
                    encoding="utf-8",
                )
                lexicon_path = tmp
        elif args.context_file is None and not args.context_table:
            auto_path = resolve_lexicon_path()
            if auto_path is not None:
                lexicon_path = auto_path

        if lexicon_path is not None or (args.context_table and args.dry_run):
            if lexicon_path is not None:
                output["steps"].append(
                    _import_tenant_context(
                        storage,
                        lexicon_path,
                        dry_run=args.dry_run,
                        apply_templates=not args.context_lexicon_only,
                    )
                )
                if not args.dry_run and not args.context_lexicon_only:
                    os.environ["PRISMGUARD_TENANT_LEXICON_PATH"] = str(lexicon_path)

        if args.write_config and not args.dry_run:
            cfg_path = Path(args.write_config)
            cfg_path.parent.mkdir(parents=True, exist_ok=True)
            cfg = load_triage_config()
            updates = {
                "tenant_context": {
                    "enabled": lexicon_path is not None,
                    "lexicon_path": str(lexicon_path) if lexicon_path else "",
                }
            }
            if args.domain:
                updates["tenant_context"]["domain"] = args.domain  # type: ignore[index]
            import yaml

            raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) if cfg_path.is_file() else {}
            if not isinstance(raw, dict):
                raw = {}
            raw.setdefault("tenant_context", {}).update(updates["tenant_context"])
            cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
            output["config_written"] = str(cfg_path)

        output["success"] = True
    finally:
        storage.close()

    print(json.dumps(output, indent=2))
    return 0


def _safe_print(text: str) -> None:
    """Print without crashing Windows cp1252 consoles on Unicode punctuation."""
    try:
        print(text)
    except UnicodeEncodeError:
        from prismguard.runtime.capabilities import ascii_safe

        print(ascii_safe(text))


def cmd_caps(args: argparse.Namespace) -> int:
    """Print onnx / taxonomy / feedback / storage readiness (DX for half-stack installs)."""
    from prismguard.runtime.capabilities import ascii_safe, format_capabilities, guard_capabilities

    caps = guard_capabilities(profile=args.profile)
    if args.json:
        # Ensure note strings are ASCII-safe even in JSON pretty-print on Windows.
        safe = dict(caps)
        safe["notes"] = [ascii_safe(str(n)) for n in (caps.get("notes") or [])]
        if safe.get("taxonomy_skip_reason"):
            safe["taxonomy_skip_reason"] = ascii_safe(str(safe["taxonomy_skip_reason"]))
        _safe_print(json.dumps(safe, indent=2, ensure_ascii=True))
    else:
        _safe_print(format_capabilities(caps))
    # Non-zero if claiming scorecard-ish profile without ONNX, or learn path without taxonomy.
    prof = str(caps.get("profile") or "")
    if prof in ("security_bench", "law_pilot", "low_latency") and not caps.get("onnx_ready"):
        return 1
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    report: dict = {"checks": [], "ok": True}
    cfg = load_triage_config(Path(args.config) if args.config else None)

    report["checks"].append({"name": "python", "ok": True, "detail": sys.version.split()[0]})

    coherence_ok = True
    if cfg.gray_zone_policy == "escalate" and cfg.guard_model.enabled:
        from prismguard.runtime.guard_model import create_guard_model

        model = create_guard_model(cfg.guard_model)
        ready = model is not None and model.is_ready
        check: dict = {
            "name": "guard_model",
            "ok": ready,
            "artifact_id": cfg.guard_model.artifact_id,
        }
        if not ready:
            coherence_ok = False
            check["detail"] = (
                "guard model not ready - install extras and download artifacts: "
                "pip install prismguard[guard-model] && prismguard-model download"
            )
        report["checks"].append(check)
    else:
        report["checks"].append({"name": "guard_model", "ok": True, "detail": "not required for current policy"})

    lexicon_path = cfg.tenant_context.lexicon_path or os.environ.get("PRISMGUARD_TENANT_LEXICON_PATH", "")
    if cfg.tenant_context.enabled:
        exists = bool(lexicon_path and Path(lexicon_path).is_file())
        report["checks"].append({"name": "tenant_lexicon", "ok": exists, "path": lexicon_path})
        if not exists:
            coherence_ok = False
    else:
        report["checks"].append({"name": "tenant_lexicon", "ok": True, "detail": "optional - not enabled"})

    report["checks"].append({"name": "domains_available", "ok": True, "domains": list_domains()})
    report["checks"].append(
        {
            "name": "classifier_mode",
            "ok": True,
            "mode": cfg.guard_model.classifier_mode,
            "disagreement_escalation": cfg.guard_model.disagreement_escalation,
            "veto_enabled": cfg.guard_model.veto_enabled,
        }
    )

    storage = _storage_for_cli(args.backend)
    try:
        categories = storage.relational.list_categories()
        entries = sum(
            len(storage.vector.list_seed_entries_by_category(c.slug)) for c in categories
        )
        report["checks"].append({"name": "seed_corpus", "ok": entries > 0, "entries": entries, "categories": len(categories)})
        if entries == 0:
            coherence_ok = False
    except Exception as exc:
        report["checks"].append({"name": "seed_corpus", "ok": False, "error": str(exc)})
        coherence_ok = False
    finally:
        storage.close()

    report["ok"] = coherence_ok
    print(json.dumps(report, indent=2))
    return 0 if coherence_ok else 1


def cmd_check(args: argparse.Namespace) -> int:
    from prismguard.cli_check import format_check_result, run_check

    try:
        result = run_check(args.text)
    except SystemExit:
        raise
    except Exception as exc:
        # Last-resort: actionable message, not an unhandled traceback.
        print(f"prismguard check failed: {exc}", file=sys.stderr)
        print(
            'Hint: for full taxonomy extras run: pip install "prismguard[prism]"',
            file=sys.stderr,
        )
        return 2
    if args.json:
        print(
            json.dumps(
                {
                    "decision": result.decision,
                    "resolution_gate": result.resolution_gate,
                    "matched_category": result.matched_category,
                    "details": result.details,
                },
                indent=2,
            )
        )
    else:
        print(format_check_result(result))
    return 0 if result.decision == "allow" else 1


def cmd_context_import(args: argparse.Namespace) -> int:
    if args.apply:
        from prismguard.licensing.features import ENTERPRISE_TENANT, require_feature

        require_feature(ENTERPRISE_TENANT)
    path = Path(args.source)
    lexicon = load_lexicon_file(path)
    print(
        json.dumps(
            {
                "domain": lexicon.domain,
                "entities": len(lexicon.entities),
                "source": lexicon.source or str(path),
            },
            indent=2,
        )
    )
    if args.dry_run:
        parsed = lexicon_to_parsed_seed(lexicon)
        print(json.dumps({"dry_run": True, "template_entries": len(parsed.entries)}, indent=2))
        return 0

    storage = _storage_for_cli(args.backend)
    try:
        if args.apply:
            parsed = lexicon_to_parsed_seed(lexicon)
            report = import_seeds(storage, parsed, mode="update", skip_taxonomy=False)
            print(
                json.dumps(
                    {
                        "applied": True,
                        "inserted": report.inserted,
                        "updated": report.updated,
                        "skipped": report.skipped,
                    },
                    indent=2,
                )
            )
    finally:
        storage.close()
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="prismguard", description="PrismGuard setup and diagnostics")
    sub = parser.add_subparsers(dest="command", required=True)

    init_cmd = sub.add_parser("init", help="Bootstrap bundled seed, optional domain pack, optional tenant context")
    init_cmd.add_argument("--domain", choices=list_domains(), help="Optional domain pack (law, healthcare, finance)")
    init_cmd.add_argument("--profile", default="authored", choices=["authored", "full"])
    init_cmd.add_argument("--context-file", type=Path, help="Optional tenant lexicon (.yaml, .json, .csv)")
    init_cmd.add_argument("--context-table", help="Optional SQL table name with term rows")
    init_cmd.add_argument("--context-dsn", help="Database DSN for --context-table")
    init_cmd.add_argument(
        "--context-lexicon-only",
        action="store_true",
        help="Load lexicon for runtime only; do not import template seed entries",
    )
    init_cmd.add_argument("--dry-run", action="store_true")
    init_cmd.add_argument("--backend", default=None)
    init_cmd.add_argument("--write-config", type=Path, help="Write tenant_context settings to triage yaml")

    doctor_cmd = sub.add_parser("doctor", help="Verify storage, seed, guard model, and optional tenant lexicon")
    doctor_cmd.add_argument("--config", type=Path, default=None)
    doctor_cmd.add_argument("--backend", default=None)

    caps_cmd = sub.add_parser(
        "caps",
        help="Print capability truth table (onnx, prismrag taxonomy, feedback, storage, domain, lexicon)",
    )
    caps_cmd.add_argument(
        "--profile",
        default=None,
        help="App profile to evaluate (default: PRISMGUARD_APP_PROFILE or web_chat)",
    )
    caps_cmd.add_argument("--json", action="store_true", help="Emit JSON")

    check_cmd = sub.add_parser("check", help="Check one prompt and print an auditable decision")
    check_cmd.add_argument("text", help="Prompt text to classify")
    check_cmd.add_argument("--json", action="store_true", help="Emit JSON instead of human-readable output")

    ctx_cmd = sub.add_parser("context", help="Tenant context lexicon tools")
    ctx_sub = ctx_cmd.add_subparsers(dest="context_command", required=True)
    import_cmd = ctx_sub.add_parser("import", help="Validate or import optional tenant lexicon")
    import_cmd.add_argument("source", type=Path)
    import_cmd.add_argument("--dry-run", action="store_true")
    import_cmd.add_argument("--apply", action="store_true", help="Import template-generated seed entries")
    import_cmd.add_argument("--backend", default=None)

    domains_cmd = sub.add_parser("domains", help="List available domain packs")
    domains_cmd.add_argument("--json", action="store_true")

    eval_cmd = sub.add_parser("eval", help="Install verification (not internal holdout benchmark)")
    eval_sub = eval_cmd.add_subparsers(dest="eval_command", required=True)
    self_check_cmd = eval_sub.add_parser(
        "self-check",
        help="Verify classifier + fresh probes after pip install (holdout is eval-only, never imported)",
    )
    self_check_cmd.add_argument(
        "--skip-runtime",
        action="store_true",
        help="Config checks only (no ONNX runtime probes)",
    )

    # Opt-in customer/pilot training loop (default: unused until feedback persist is enabled).
    fb_cmd = sub.add_parser(
        "feedback",
        help="Export reviewed feedback for ONNX training (opt-in; default unused)",
    )
    fb_sub = fb_cmd.add_subparsers(dest="feedback_command", required=True)
    fb_export = fb_sub.add_parser("export", help="Export training JSONL (approved blocks by default)")
    fb_export.add_argument("--output", "-o", required=True)
    fb_export.add_argument(
        "--include-calibration-allows",
        action="store_true",
        help="Also export calibration allows (default: off)",
    )
    fb_export.add_argument("--calibration-only", action="store_true")
    fb_export.add_argument("--store", default="")
    fb_export.add_argument("--backend", default=None)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        raise SystemExit(cmd_init(args))
    if args.command == "doctor":
        raise SystemExit(cmd_doctor(args))
    if args.command == "caps":
        raise SystemExit(cmd_caps(args))
    if args.command == "check":
        raise SystemExit(cmd_check(args))
    if args.command == "context":
        if args.context_command == "import":
            raise SystemExit(cmd_context_import(args))
        parser.error(f"Unknown context command {args.context_command!r}")
    if args.command == "domains":
        packs = [get_domain_pack(name) for name in list_domains()]
        if args.json:
            print(json.dumps([{"name": p.name, "label": p.label} for p in packs], indent=2))
        else:
            for pack in packs:
                print(f"{pack.name}\t{pack.label}\t{pack.overlay_path}")
        return
    if args.command == "eval":
        if args.eval_command == "self-check":
            from prismguard.eval.self_check import format_report, run_user_verify

            report = run_user_verify(skip_runtime=args.skip_runtime)
            print(format_report(report))
            raise SystemExit(0 if report.ok else 1)
        parser.error(f"Unknown eval command {args.eval_command!r}")
    if args.command == "feedback":
        from prismguard.feedback.cli import cmd_export

        raise SystemExit(cmd_export(args))
    parser.error(f"Unknown command {args.command!r}")


if __name__ == "__main__":
    main()
