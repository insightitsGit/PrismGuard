from __future__ import annotations

import sys

from prismguard.models.eval import main as eval_main


def main() -> None:
    raise SystemExit(eval_main(["--domain", "law", *sys.argv[1:]]))


if __name__ == "__main__":
    main()
