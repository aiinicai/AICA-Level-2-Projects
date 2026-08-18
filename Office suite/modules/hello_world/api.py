from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/")
def get_hello():
    return {
        "status": "success",
        "module": "hello_world",
        "message": "Hello World module loaded dynamically!",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/status")
def get_status():
    return {
        "module": "hello_world",
        "healthy": True,
        "features": ["Dynamic Routing", "FastAPI APIRouter", "Iframe Sandbox UI"]
    }
