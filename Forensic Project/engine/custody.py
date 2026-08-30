"""
Chain of Custody and Audit Trail module for Red Flag Engine.
Maintains append-only run logs, file SHA-256 hashes, rule version hashes,
predication notes, and human verification confirmations (ICAI Ch. 6.4.1.1).
"""
import os
import json
import uuid
import datetime
from typing import Dict, List, Any, Optional
from engine.ingest import compute_sha256

def hash_rule_files(rules_dir: str = "rules") -> Dict[str, str]:
    """Compute SHA-256 hash for every YAML file in the rules directory."""
    hashes = {}
    if os.path.exists(rules_dir):
        for f in sorted(os.listdir(rules_dir)):
            if f.endswith(".yaml"):
                full_path = os.path.join(rules_dir, f)
                hashes[f] = compute_sha256(full_path)
    return hashes

def record_custody_entry(
    run_id: Optional[str] = None,
    operator: str = "Forensic Auditor",
    predication_note: str = "",
    files: Optional[List[Dict[str, Any]]] = None,
    parameters: Optional[Dict[str, Any]] = None,
    confirmations: Optional[List[Dict[str, Any]]] = None,
    rules_dir: str = "rules",
    runs_dir: str = "runs"
) -> Dict[str, Any]:
    """
    Record an append-only chain of custody entry into runs/<run_id>/custody.json.
    """
    if not run_id:
        run_id = str(uuid.uuid4())
        
    entry = {
        "run_id": run_id,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "operator": operator,
        "predication_note": predication_note,
        "files": files or [],
        "rule_versions": hash_rule_files(rules_dir),
        "parameters": parameters or {},
        "confirmations": confirmations or []
    }
    
    run_folder = os.path.join(runs_dir, run_id)
    os.makedirs(run_folder, exist_ok=True)
    custody_file = os.path.join(run_folder, "custody.json")
    
    # Read existing entries if present (append-only)
    entries = []
    if os.path.exists(custody_file):
        try:
            with open(custody_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    entries = data
                elif isinstance(data, dict):
                    entries = [data]
        except Exception:
            entries = []
            
    entries.append(entry)
    with open(custody_file, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
        
    return entry
