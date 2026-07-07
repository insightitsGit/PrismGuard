from __future__ import annotations

import re
from dataclasses import dataclass, field

from prismguard.seed.models import ParsedSeed, RuleSeed


@dataclass
class ValidationIssue:
    level: str
    message: str


@dataclass
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(issue.level == "error" for issue in self.issues)

    def add_error(self, message: str) -> None:
        self.issues.append(ValidationIssue("error", message))

    def add_warning(self, message: str) -> None:
        self.issues.append(ValidationIssue("warning", message))


def validate_parsed_seed(parsed: ParsedSeed, *, mode: str, scope: str) -> ValidationReport:
    report = ValidationReport()
    known_categories = {c.slug for c in parsed.categories}
    for entry in parsed.entries:
        if entry.category_slug not in known_categories:
            if mode == "replace" and scope == "all":
                report.add_warning(
                    f"Entry references unknown category {entry.category_slug!r} — "
                    "category will be created on import"
                )
            else:
                report.add_warning(
                    f"Entry references category {entry.category_slug!r} not defined in merged sources"
                )
    seen_rule_ids: dict[str, RuleSeed] = {}
    for rule in parsed.rules:
        if rule.rule_id in seen_rule_ids:
            report.add_error(f"Duplicate rule_id {rule.rule_id!r} within merged import batch")
        seen_rule_ids[rule.rule_id] = rule
        if rule.pattern_type == "regex":
            try:
                re.compile(rule.pattern)
            except re.error as exc:
                report.add_error(f"Malformed regex for rule {rule.rule_id!r}: {exc}")
    return report
