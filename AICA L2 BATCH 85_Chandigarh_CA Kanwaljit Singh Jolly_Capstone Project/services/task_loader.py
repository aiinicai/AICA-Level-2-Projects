"""
Task Loader - Generic core component

Loads task packs dynamically based on task_id.
This is the bridge between core (generic) and task packs (specific).
"""

import importlib


def load_task(task_id: str):
    """
    Loads a task pack by id, e.g. 'tds_26q' -> task_packs.tds_26q.task_api

    Args:
        task_id: Task identifier (e.g., 'tds_26q', 'invoice_validation')

    Returns:
        TaskPack object with methods:
        - classify(file_path) -> str
        - extract(doc_type, file_path) -> list
        - get_rules() -> List[RuleDefinition]
        - get_ai_checks() -> List[dict]

    Raises:
        ImportError: Task pack not found
        RuntimeError: Task pack missing get_task()
    """
    mod_path = f"task_packs.{task_id}.task_api"
    mod = importlib.import_module(mod_path)

    if not hasattr(mod, "get_task"):
        raise RuntimeError(f"{mod_path} missing get_task()")

    return mod.get_task()


def list_available_tasks():
    """
    List all available task packs.

    Returns:
        List of task_id strings
    """
    # For now, hardcoded. Could auto-discover from task_packs/ directory
    return ["tds_26q"]
