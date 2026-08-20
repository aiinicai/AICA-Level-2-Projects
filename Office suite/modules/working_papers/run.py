from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Working Paper Tools Standalone")

try:
    from .api import router
except ImportError:
    from api import router

app.include_router(router, prefix="/api/working_papers")

app.mount("/modules/working_papers", StaticFiles(directory=MODULE_DIR, html=True), name="wp_static")

@app.get("/")
def read_root():
    return FileResponse(MODULE_DIR / "index.html")

if __name__ == "__main__":
    print("Starting Working Paper Tools Standalone Server on http://localhost:8002...")
    uvicorn.run(app, host="0.0.0.0", port=8002)
