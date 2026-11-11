# SmartHire AI — Full-stack capstone foundation

This is a **working-code foundation**, not a hosted deployment or a production-certified hiring system. It includes React, FastAPI, Supabase Auth, tenant-scoped CRUD, private resume uploads, explainable baseline screening, review statuses, admin invitations and CSV export.

## 1. Create a dedicated Supabase project

Do **not** run the schema in an existing unrelated project. In Supabase SQL Editor run `supabase/schema.sql`. In Dashboard > Authentication > Providers, disable public email signups ("Allow new users to sign up" off). In Authentication > Users create the first administrator manually; copy their Auth UUID. Edit `supabase/bootstrap_admin.sql`, replacing the placeholder with the real UUID, then run it once. This creates an organization and admin profile. Do not expose or commit any secret keys.

## 2. Backend (Python 3.11+)

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
# Copy .env.example to .env and fill SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
uvicorn main:app --reload --port 8000
```

Check `http://localhost:8000/api/health` and `http://localhost:8000/docs`.

## 3. Frontend (Node.js 20+)

```bash
cd frontend
npm install
# Copy .env.example to .env and fill VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY
npm run dev
```

Open `http://localhost:5173` and sign in with the admin credentials. **Only the publishable/anon key belongs in frontend/.env**. The service-role key must stay exclusively in `backend/.env`.

## 4. Try the app

1. Create a job with a detailed description including recognizable skills such as Python, SQL and React.
2. Upload one or more text-based PDF/DOCX resumes.
3. Open Candidates, compare skills and match indicators, and change human review status.
4. Export CSV. Use Admin to invite recruiters.

## Scope and limitations

- Screening uses a **baseline TF-IDF + detected skill coverage** heuristic. It is not an LLM, validated AI hiring model, or a measure of candidate quality. It must never automatically reject or hire anyone.
- OCR for scanned resumes, full audit trails, structured evidence citations, background job queues, LLM-generated interview questions, PDF reports, calibrated scoring and fairness evaluation are future enhancements.
- Admin invitations require configured Supabase Auth email delivery and redirect settings. Invited users may need to set a password through the invite flow.
- For production, implement anti-virus scanning, rate limiting, strong logging, data retention/deletion workflows, legal privacy review, and rigorous security tests. Keep sensitive resumes out of logs and LLM services without consent.
- Supabase table RLS is enabled with no direct browser policies. The FastAPI server verifies access tokens and scopes queries to organization IDs. Server-side service key bypasses RLS, so server authorization is critical. Keep this architecture and thoroughly test tenant isolation before deployment.
- The existing Streamlit MVP is separate; this package does not alter it.

## Key files

- `frontend/src/main.jsx` — responsive UI and Supabase Auth
- `backend/main.py` — FastAPI endpoints, parsing and screening
- `supabase/schema.sql` — tables, RLS and private storage
- `supabase/bootstrap_admin.sql` — initial admin provisioning

## Quick validation

```bash
python -m py_compile backend/main.py
cd frontend && npm run build
```

A deployed Supabase project and real credentials are required for end-to-end authentication and storage testing.
