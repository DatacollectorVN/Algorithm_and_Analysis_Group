#!/usr/bin/env python3
"""Entry point — launches the interactive demo menu (see :mod:`menu`)."""

from __future__ import annotations

import logging

from services import interactive_menu

logging.basicConfig(level=logging.INFO, format="%(message)s")
_log = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        interactive_menu()
    except KeyboardInterrupt:
        _log.info("\nGoodbye!")
