from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Literal
from uuid import uuid4

from prismguard.seed.models import ParsedSeed
from prismguard.seed.normalize import normalize_seed_text, seed_content_hash
from prismguard.seed.validate import ValidationReport, validate_parsed_seed
from prismguard.storage.protocols import StorageBackend
from prismguard.storage.types import CategoryRecord, ImportLogRecord, RuleRecord, SeedEntryRecord

ImportMode = Literal["update", "replace"]
ImportScope = Literal["all"] | str


class ReplaceScope(str, Enum):
    ALL = "all"

    @classmethod
    def category(cls, slug: str) -> str:
        return f"category:{slug}"

    @staticmethod
    def parse(value: str) -> tuple[str, str | None]:
        if value == "all":
            return "all", None
        if value.startswith("category:"):
            return "category", value.split(":", 1)[1]
        raise ValueError(f"Invalid scope {value!r}; use all or category:<slug>")


@dataclass
class ImportReport:
    mode: ImportMode
    scope: str
    source_files: list[str]
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errored: int = 0
    warnings: list[str] = field(default_factory=list)
    dry_run: bool = False

    @property
    def net_changes(self) -> int:
        return self.inserted + self.updated


@dataclass
class ImportOptions:
    mode: ImportMode = "update"
    scope: str = "all"
    dry_run: bool = False
    confirm_replace_all: bool = False
    force: bool = False


class SeedImporter:
    def __init__(self, storage: StorageBackend) -> None:
        self._storage = storage

    def import_parsed(self, parsed: ParsedSeed, options: ImportOptions) -> ImportReport:
        scope_kind, category_slug = ReplaceScope.parse(options.scope)
        if options.mode == "replace" and scope_kind == "all" and not options.confirm_replace_all:
            raise ValueError("replace --scope all requires confirm_replace_all=True")
        if options.mode == "replace" and scope_kind == "category" and category_slug:
            parsed = ParsedSeed(
                categories=[c for c in parsed.categories if c.slug == category_slug],
                rules=[r for r in parsed.rules if r.category_slug == category_slug],
                entries=[e for e in parsed.entries if e.category_slug == category_slug],
                source_files=parsed.source_files,
            )

        validation = validate_parsed_seed(parsed, mode=options.mode, scope=options.scope)
        report = ImportReport(
            mode=options.mode,
            scope=options.scope,
            source_files=list(parsed.source_files),
            dry_run=options.dry_run,
            warnings=[issue.message for issue in validation.issues if issue.level == "warning"],
        )
        if validation.has_errors and not options.force:
            report.errored = len([i for i in validation.issues if i.level == "error"])
            raise ValueError(
                "Import validation failed:\n"
                + "\n".join(i.message for i in validation.issues if i.level == "error")
            )

        if options.dry_run:
            report.inserted = len(parsed.entries)
            return report

        if options.mode == "replace":
            if scope_kind == "all":
                report.skipped = self._storage.vector.truncate_seed_entries()
            elif category_slug:
                report.skipped = self._storage.vector.delete_seed_entries_by_category(category_slug)

        for category in parsed.categories:
            self._storage.relational.upsert_category(
                CategoryRecord(
                    slug=category.slug,
                    label=category.label,
                    description=category.description,
                    is_attack_category=category.is_attack_category,
                )
            )

        for rule in parsed.rules:
            self._storage.relational.upsert_rule(
                RuleRecord(
                    rule_id=rule.rule_id,
                    pattern=rule.pattern,
                    pattern_type=rule.pattern_type,
                    category_slug=rule.category_slug,
                    severity=rule.severity,
                    rationale=rule.rationale,
                    created_by=rule.created_by,
                )
            )

        existing_index = self._build_entry_index()

        for entry in parsed.entries:
            content_hash = seed_content_hash(entry.category_slug, entry.text)
            normalized = normalize_seed_text(entry.text)
            existing = existing_index.get(content_hash)
            record = SeedEntryRecord(
                id=existing.id if existing else str(uuid4()),
                raw_text=entry.text,
                chunk_text=normalized,
                embedding_semantic=existing.embedding_semantic if existing else [],
                embedding_category=existing.embedding_category if existing else [],
                category_slug=entry.category_slug,
                severity=entry.severity,
                source=entry.source,
                reviewed_by=existing.reviewed_by if existing else None,
                created_at=existing.created_at if existing else datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            if existing is None:
                self._storage.vector.upsert_seed_entry(record)
                existing_index[content_hash] = record
                report.inserted += 1
            elif self._entry_changed(existing, record):
                self._storage.vector.upsert_seed_entry(record)
                existing_index[content_hash] = record
                report.updated += 1
            else:
                report.skipped += 1

        self._storage.relational.append_import_log(
            ImportLogRecord(
                id=str(uuid4()),
                source_filename="; ".join(parsed.source_files) or "merged",
                mode=options.mode,
                scope=options.scope,
                inserted=report.inserted,
                updated=report.updated,
                skipped=report.skipped,
                errored=report.errored,
                created_at=datetime.now(UTC),
            )
        )
        return report

    def _build_entry_index(self) -> dict[str, SeedEntryRecord]:
        index: dict[str, SeedEntryRecord] = {}
        for category in self._storage.relational.list_categories():
            for entry in self._storage.vector.list_seed_entries_by_category(category.slug):
                key = seed_content_hash(entry.category_slug, entry.raw_text)
                index[key] = entry
        return index

    @staticmethod
    def _entry_changed(before: SeedEntryRecord, after: SeedEntryRecord) -> bool:
        return (
            before.severity != after.severity
            or before.source != after.source
            or before.chunk_text != after.chunk_text
        )


def import_seeds(
    storage: StorageBackend,
    parsed: ParsedSeed,
    *,
    mode: ImportMode = "update",
    scope: str = "all",
    dry_run: bool = False,
    confirm_replace_all: bool = False,
    force: bool = False,
) -> ImportReport:
    importer = SeedImporter(storage)
    return importer.import_parsed(
        parsed,
        ImportOptions(
            mode=mode,
            scope=scope,
            dry_run=dry_run,
            confirm_replace_all=confirm_replace_all,
            force=force,
        ),
    )
