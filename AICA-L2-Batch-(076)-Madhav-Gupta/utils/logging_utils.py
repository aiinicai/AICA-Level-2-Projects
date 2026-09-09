import logging
import os
from utils.paths import get_log_directory

_LOGGER = None


def get_logger(name="AssetDepPro"):
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    log_path = os.path.join(get_log_directory(), "assetdeppro.log")
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))
    logger.addHandler(fh)
    _LOGGER = logger
    return logger