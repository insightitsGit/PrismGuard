from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

import yaml

from prismguard.context.models import EntityTerm, TenantLexicon


def _entity_from_row(row: dict[str, Any]) -> EntityTerm:
    aliases_raw = row.get("aliases") or row.get("alias") or ""
    if isinstance(aliases_raw, str):
        aliases = [a.strip() for a in aliases_raw.split(";") if a.strip()]
    elif isinstance(aliases_raw, list):
        aliases = [str(a).strip() for a in aliases_raw if str(a).strip()]
    else:
        aliases = []
    return EntityTerm(
        term=str(row.get("term") or row.get("keyword") or row.get("name") or "").strip(),
        type=row.get("type") or row.get("entity_type") or "generic",  # type: ignore[arg-type]
        sensitivity=row.get("sensitivity") or "internal",  # type: ignore[arg-type]
        aliases=aliases,
    )


def load_lexicon_from_mapping(data: dict[str, Any], *, source: str = "") -> TenantLexicon:
    entities_raw = data.get("entities") or data.get("terms") or data.get("keywords") or []
    entities: list[EntityTerm] = []
    for row in entities_raw:
        if isinstance(row, str):
            entities.append(EntityTerm(term=row.strip()))
        elif isinstance(row, dict):
            entity = _entity_from_row(row)
            if entity.term:
                entities.append(entity)
    override = data.get("override_tokens") or []
    return TenantLexicon(
        domain=str(data.get("domain") or "general"),
        source=source or str(data.get("source") or ""),
        entities=entities,
        override_tokens=[str(t) for t in override],
    )


def load_lexicon_file(path: str | Path) -> TenantLexicon:
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Tenant lexicon not found: {file_path}")
    suffix = file_path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        with file_path.open(encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
        if not isinstance(raw, dict):
            raise ValueError(f"Expected mapping in {file_path}, got {type(raw)!r}")
        return load_lexicon_from_mapping(raw, source=str(file_path))
    if suffix == ".json":
        with file_path.open(encoding="utf-8") as handle:
            raw = json.load(handle)
        if not isinstance(raw, dict):
            raise ValueError(f"Expected mapping in {file_path}, got {type(raw)!r}")
        return load_lexicon_from_mapping(raw, source=str(file_path))
    if suffix == ".csv":
        entities: list[EntityTerm] = []
        with file_path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                entity = _entity_from_row(row)
                if entity.term:
                    entities.append(entity)
        return TenantLexicon(domain="general", source=str(file_path), entities=entities)
    raise ValueError(f"Unsupported tenant lexicon format: {suffix} (use .yaml, .json, or .csv)")


def load_lexicon_from_sql_table(
    dsn: str,
    table: str,
    *,
    limit: int = 5000,
) -> TenantLexicon:
    import re

    try:
        import psycopg2
        from psycopg2 import sql as psql
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "SQL tenant lexicon requires psycopg2 (install prismguard[pgvector])"
        ) from exc

    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table):
        raise ValueError(f"Invalid SQL table name: {table!r}")

    entities: list[EntityTerm] = []
    with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(psql.SQL("SELECT * FROM {} LIMIT %s").format(psql.Identifier(table)), (limit,))
        columns = [desc[0].lower() for desc in cur.description]
        for row in cur.fetchall():
            row_dict = {columns[i]: row[i] for i in range(len(columns))}
            entity = _entity_from_row(row_dict)
            if entity.term:
                entities.append(entity)
    return TenantLexicon(domain="general", source=f"sql:{table}", entities=entities)


def re_table_name(name: str) -> bool:
    import re

    return bool(re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name))


def resolve_lexicon_path(path: str | Path | None = None) -> Path | None:
    if path is not None:
        return Path(path)
    env = os.environ.get("PRISMGUARD_TENANT_LEXICON_PATH", "").strip()
    if env:
        return Path(env)
    default = Path.cwd() / "tenant_lexicon.yaml"
    if default.is_file():
        return default
    return None


def load_tenant_lexicon(path: str | Path | None = None) -> TenantLexicon | None:
    resolved = resolve_lexicon_path(path)
    if resolved is None:
        return None
    return load_lexicon_file(resolved)
