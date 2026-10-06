#!/usr/bin/env python3
"""Explicit offline valve-artifact verification/restoration CLI."""
import sys
from transport import main
if __name__ == '__main__':
    sys.exit(main(['restore'] + sys.argv[1:]))
