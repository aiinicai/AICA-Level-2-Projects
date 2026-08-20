import os
import sys
import importlib.util
import logging
from pathlib import Path
from typing import Dict, List, Any
import json

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OfficeSuiteCore")

# Define root paths
BASE_DIR = Path(__file__).resolve().parent.parent
CORE_DIR = BASE_DIR / "core"
MODULES_DIR = BASE_DIR / "modules"

app = FastAPI(
    title="Modular Office Suite Core Shell",
    description="Locally-hosted, dynamic modular office suite core",
    version="1.0.0"
)

# Enable CORS for local network access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registry to hold metadata of discovered modules
registered_modules: List[Dict[str, Any]] = []

def discover_and_mount_modules():
    """
    Scans the /modules directory.
    If a folder contains an api.py with an APIRouter named `router`,
    dynamically imports and mounts it under /api/{module_name}.
    """
    global registered_modules
    registered_modules.clear()

    if not MODULES_DIR.exists():
        logger.warning(f"Modules directory not found at {MODULES_DIR}")
        return

    # Add project root to sys.path so modules can be imported smoothly
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))

    for item in os.listdir(MODULES_DIR):
        module_path = MODULES_DIR / item
        if not module_path.is_dir():
            continue

        api_file = module_path / "api.py"
        if not api_file.exists():
            logger.info(f"Skipping module '{item}': No api.py found")
            continue

        module_name = item
        # Import api.py dynamically
        module_import_path = f"modules.{module_name}.api"
        try:
            mod = importlib.import_module(module_import_path)
            
            # Check if router exists in the imported module
            if hasattr(mod, "router"):
                router = getattr(mod, "router")
                prefix = f"/api/{module_name}"
                app.include_router(router, prefix=prefix)
                logger.info(f"Successfully mounted router for module '{module_name}' at '{prefix}'")

                # Read manifest if present
                manifest_file = module_path / "manifest.json"
                manifest_data = {}
                if manifest_file.exists():
                    try:
                        with open(manifest_file, "r", encoding="utf-8") as f:
                            manifest_data = json.load(f)
                    except Exception as e:
                        logger.error(f"Error reading manifest for '{module_name}': {e}")

                entry_ui = manifest_data.get("entry_ui", f"/modules/{module_name}/index.html")
                if not manifest_data.get("entry_ui") and not (module_path / "index.html").exists():
                    entry_ui = None

                module_info = {
                    "id": module_name,
                    "name": manifest_data.get("name", module_name.replace("_", " ").title()),
                    "icon": manifest_data.get("icon", "sparkles"),
                    "description": manifest_data.get("description", "Office Suite Tool Module"),
                    "version": manifest_data.get("version", "1.0.0"),
                    "api_base": prefix,
                    "entry_ui": entry_ui
                }
                registered_modules.append(module_info)
            else:
                logger.warning(f"Module '{module_name}/api.py' does not contain an APIRouter named 'router'")
        except Exception as e:
            logger.error(f"Failed to import module '{module_name}': {e}", exc_info=True)

# Run dynamic discovery on startup
discover_and_mount_modules()

@app.get("/api/modules", tags=["Core Shell"])
def get_available_modules():
    """Return list of dynamically registered modules."""
    return {
        "status": "success",
        "count": len(registered_modules),
        "modules": registered_modules
    }

# Mount static asset routes
if MODULES_DIR.exists():
    app.mount("/modules", StaticFiles(directory=str(MODULES_DIR)), name="modules_static")

if CORE_DIR.exists():
    app.mount("/core", StaticFiles(directory=str(CORE_DIR)), name="core_static")

@app.get("/", tags=["Core Shell"])
def read_root():
    """Serve the core dashboard UI at root."""
    return FileResponse(str(CORE_DIR / "dashboard.html"))

if __name__ == "__main__":
    logger.info("Starting Office Suite Core Shell on host 0.0.0.0:8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
