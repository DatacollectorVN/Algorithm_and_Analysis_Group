#!/usr/bin/env python3
"""CLI entry: subcommands ``generate-corpus`` and ``search`` (top-k similarity).

- ``generate-corpus``: required ``--N``, optional ``--seed`` → writes ``corpus.json`` and
  ``metadata.txt`` under ``./.rmit/corpus/YYYYMMDD_HHMMSS/``; prints those absolute paths
  (no corpus JSON on stdout).
- ``search``: ``--corpus``, ``--query``, optional ``--strategy``, ``--benchmark``.

Imports assume ``PYTHONPATH`` includes the ``src`` directory (no runtime ``sys.path`` mutation).
"""

from __future__ import annotations

import logging

from services.args import build_parser
from services.runner import run_generate_corpus, run_search

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run(argv: list[str] | None = None) -> int:
    """Parse argv, dispatch subcommand; ``search`` prints JSON; ``generate-corpus`` writes files and paths."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "generate-corpus":
        return run_generate_corpus(args)
    return run_search(args)


if __name__ == "__main__":
    raise SystemExit(run())
