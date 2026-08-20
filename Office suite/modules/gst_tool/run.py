from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="GST Management Tool Standalone")

try:
    from .api import router
except ImportError:
    from api import router

app.include_router(router, prefix="/api/gst_tool")

app.mount("/modules/gst_tool", StaticFiles(directory=MODULE_DIR, html=True), name="gst_tool_static")

@app.get("/")
def read_root():
    return FileResponse(MODULE_DIR / "index.html")

if __name__ == "__main__":
    print("Starting GST Management Tool Standalone Server on http://localhost:8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001)
