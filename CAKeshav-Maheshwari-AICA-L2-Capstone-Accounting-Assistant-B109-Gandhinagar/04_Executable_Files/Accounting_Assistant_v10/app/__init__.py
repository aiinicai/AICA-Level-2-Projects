"""Smart App Control blocks unsigned compiled modules (.pyd). SQLAlchemy ships a pure-Python
twin for each of its *_cy extensions, so when running from source we load those instead.
(The frozen .exe gets all its binaries code-signed at build time instead.)"""
import importlib.abc
import importlib.util
import sys
from pathlib import Path


class _PurePythonSQLAlchemy(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if not (fullname.startswith("sqlalchemy.") and fullname.rsplit(".", 1)[-1].endswith("_cy")):
            return None
        for base in path or []:
            src = Path(base) / (fullname.rsplit(".", 1)[-1] + ".py")
            if src.exists():
                return importlib.util.spec_from_file_location(fullname, src)
        return None


if not getattr(sys, "frozen", False) and not any(isinstance(f, _PurePythonSQLAlchemy) for f in sys.meta_path):
    sys.meta_path.insert(0, _PurePythonSQLAlchemy())
