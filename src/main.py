#!/usr/bin/env python3
"""CLI entry: subcommands ``build`` and ``search`` (top-k similarity).

- ``build``: required ``--n``, optional ``--seed`` → writes ``profiles.json`` and
  ``metadata.txt`` under ``./.rmit/dataset/YYYYMMDD_HHMMSS/``; prints those absolute paths
  (no dataset JSON on stdout).
- ``search``: ``--dataset``, ``--query-profile``, optional ``--strategy``, ``--benchmark``.

Imports assume ``PYTHONPATH`` includes the ``src`` directory (no runtime ``sys.path`` mutation).
"""

from __future__ import annotations

import logging

from services.args import build_parser
from services.runner import run_generate_corpus, run_search

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run(argv: list[str] | None = None) -> int:
    """Parse argv, dispatch subcommand; ``search`` prints JSON; ``build`` writes files and paths."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "build":
        return run_generate_corpus(args)
    if args.command == "search":
        return run_search(args)
    raise ValueError(f"unknown command: {args.command!r}")


if __name__ == "__main__":
    raise SystemExit(run())
