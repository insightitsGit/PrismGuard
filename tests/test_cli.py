"""CLI wiring tests for handoffBug1 T11."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from prismguard.cli import main


def test_cli_passes_skip_taxonomy_to_bundled_import() -> None:
    with patch("prismguard.cli.import_bundled_seed") as import_mock:
        import_mock.return_value = MagicMock(
            mode="update",
            scope="all",
            source_files=[],
            inserted=0,
            updated=0,
            skipped=0,
            errored=0,
            dry_run=False,
            warnings=[],
            taxonomy=None,
        )
        with patch("prismguard.cli._storage_for_cli") as storage_mock:
            storage_mock.return_value.close = MagicMock()
            main(["import", "--bundled", "--skip-taxonomy"])
    import_mock.assert_called_once()
    assert import_mock.call_args.kwargs["skip_taxonomy"] is True


def test_cli_passes_force_embed_to_import_seeds() -> None:
    with patch("prismguard.cli.parse_seed_sources") as parse_mock:
        parse_mock.return_value = MagicMock()
        with patch("prismguard.cli.import_seeds") as import_mock:
            import_mock.return_value = MagicMock(
                mode="update",
                scope="all",
                source_files=[],
                inserted=0,
                updated=0,
                skipped=0,
                errored=0,
                dry_run=False,
                warnings=[],
                taxonomy=None,
            )
            with patch("prismguard.cli._storage_for_cli") as storage_mock:
                storage_mock.return_value.close = MagicMock()
                main(["import", "seed.yaml", "--force-embed"])
    import_mock.assert_called_once()
    assert import_mock.call_args.kwargs["force_embed"] is True
