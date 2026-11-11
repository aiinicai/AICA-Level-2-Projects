SmartHire AI Python 3.15 compatibility patch

Changes:
- Removed scikit-learn==1.6.1 and replaced TF-IDF cosine similarity with a standard-library implementation.
- Removed exact version pins to allow pip to resolve packages available for your Python version.
- Corrected FastAPI command to python -m uvicorn main:app --port 8000.
- Added 127.0.0.1:5173 to default CORS origins.

To run: open backend folder and double-click START_BACKEND_WINDOWS.cmd.
Or use: python -m pip install --prefer-binary -r requirements.txt
Then: python -m uvicorn main:app --port 8000

Important: Python 3.15 compatibility of ALL third-party libraries is not guaranteed. If another dependency fails, send the first error; don't install a compiler or downgrade Python without checking.

IMPORTANT DATABASE NOTE: The previously provisioned Supabase schema may differ from the columns this backend expects (e.g. applications.filename, match_score, reviews table). This patch fixes the scikit-learn installation issue but does not automatically reconcile that database schema. The API may still need a schema migration before all dashboard, upload and review features work.

Your backend also needs backend/.env with SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY and FRONTEND_ORIGIN. Keep service role key private and never put it in frontend/.env.
