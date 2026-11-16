"""CLI wrapper around aica_fsm.testdata.
  python tools/make_test_data.py bulk <folder> <count> [seed]
  python tools/make_test_data.py docs <folder>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aica_fsm.testdata import make_bulk, make_docs  # noqa: E402,F401

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "bulk":
        p = make_bulk(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else 1)
        print(f"{len(p)} files in {sys.argv[2]}")
    elif cmd == "docs":
        print(make_docs(sys.argv[2]))
