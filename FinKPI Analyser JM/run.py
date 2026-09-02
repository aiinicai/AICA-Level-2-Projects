import uvicorn
from backend.app.main import app

if __name__ == "__main__":
    print("==================================================================")
    print(" STARTING FINKPI ANALYZER WEB APPLICATION & RESTFUL API")
    print("==================================================================")
    print(" Web Application Dashboard : http://localhost:8000")
    print(" Swagger / OpenAPI 3.0 Docs: http://localhost:8000/docs")
    print(" Demo Login                : admin / admin123")
    print("==================================================================")
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
