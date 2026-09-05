"""
Specialization router.

The product is fully automatic: the user never picks a task type. After
normalization, this router asks each registered specialization task pack whether
the materials look like its task (via the pack's optional `matches()` signal). If
one matches with enough confidence, the pipeline uses that pack's exact,
hand-coded checks; otherwise it falls back to the generic criteria engine.

Specializations are the task packs under task_packs/ (currently just tds_26q).
The generic engine is NOT a pack — it is the default path.
"""

import logging
from typing import Any, Dict, Optional

from services.task_loader import list_available_tasks, load_task

logger = logging.getLogger(__name__)

# Minimum confidence for a specialization to take over from the generic engine.
DETECTION_THRESHOLD = 0.6


def detect_specialization(normalized_data: Dict[str, Any]) -> Optional[str]:
    """
    Return the task_id of the best-matching specialization, or None for generic.
    """
    best_id: Optional[str] = None
    best_conf = 0.0

    for task_id in list_available_tasks():
        try:
            task = load_task(task_id)
        except Exception as e:  # noqa: BLE001 - a broken pack must not block the run
            logger.warning("Specialization '%s' failed to load: %s", task_id, e)
            continue

        matcher = getattr(task, "matches", None)
        if not callable(matcher):
            continue
        try:
            conf = float(matcher(normalized_data))
        except Exception as e:  # noqa: BLE001
            logger.warning("Specialization '%s' matches() raised: %s", task_id, e)
            continue

        if conf > best_conf:
            best_conf = conf
            best_id = task_id

    if best_id and best_conf >= DETECTION_THRESHOLD:
        logger.info("Specialization detected: %s (confidence %.2f)", best_id, best_conf)
        return best_id

    logger.info("No specialization matched (best %.2f); using generic engine.", best_conf)
    return None
