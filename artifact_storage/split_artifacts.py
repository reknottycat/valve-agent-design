#!/usr/bin/env python3
"""Offline valve-artifact splitter CLI; never edits the originals."""
import sys
from transport import main
if __name__ == '__main__':
    sys.exit(main(['split'] + sys.argv[1:]))
