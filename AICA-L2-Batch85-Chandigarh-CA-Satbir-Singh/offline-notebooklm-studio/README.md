# 📚 Offline NotebookLM Studio (FastAPI + LM Studio + Tailwind)

A private, offline, 3-panel **NotebookLM-style** desktop workspace running locally with **FastAPI**, **Tailwind CSS**, and **LM Studio** (`http://localhost:1234/v1`).

---

## 🌟 Key Features

1. **Left Panel: Source Manager**
   - Upload multiple formats: `PDF`, `DOCX`, `XLSX`, `CSV`, `PNG`, `JPG`, `TXT`, `MD`.
   - Automatic local text extraction & storage in `./sources/`.
   - Dynamic context selection (select/deselect specific files to ground AI answers).
   - View extracted text in full modal, inline rename, and delete sources.

2. **Center Panel: Grounded Chat & Analysis**
   - Grounded context injection from selected sources directly into LM Studio prompt stream.
   - Quick research prompts (Executive Summary, Key Insights, Outline Presentation, Compare Sources).
   - One-click response action buttons:
     - **Send to Report**: appends response to Right Panel Output Studio.
     - **Create Word Doc**: instant `.docx` download.
     - **Create Presentation**: instant `.pptx` slide deck download.
     - **Copy Markdown**.

3. **Right Panel: Output Studio & Document Generator**
   - Live Markdown / Rich-text staging and live preview renderer.
   - One-click file generation endpoints:
     - **Export to Word (`.docx`)** via `python-docx`.
     - **Export to PowerPoint (`.pptx`)** via `python-pptx` (title slide + structured bulleted slides).
   - Editable document/presentation title and filename.
   - **"Use Output as Source" (NotebookLM recursion loop):** Saves generated output back into `./sources` as a new markdown source for recursive questioning!

---

## 🚀 Step-by-Step Setup & Running Guide

### Step 1: Start LM Studio Local Server
1. Download and open [LM Studio](https://lmstudio.ai/).
2. Download any model (e.g., `Meta-Llama-3-8B-Instruct`, `Mistral-7B-Instruct`, `Qwen2.5-7B-Instruct`, `Gemma-2-9B-It`, or `DeepSeek-R1-Distill-Qwen`).
3. Navigate to the **Local Server** tab (the `↔` icon on the left sidebar).
4. Select your loaded model from the top dropdown.
5. Ensure the server port is set to **`1234`** and click **Start Server**.
   - Your local endpoint is now active at: `http://localhost:1234/v1`

---

### Step 2: Install Python Dependencies
In your project directory, create a virtual environment and install the requirements:

```bash
# Optional: Create virtual environment
python -m venv venv

# Activate virtual environment:
# On Windows:
venv\Scripts\activate
# On macOS / Linux:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

---

### Step 3: Start the FastAPI Server
Run the FastAPI application with Uvicorn:

```bash
python app.py
```
*Or using uvicorn directly:*
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

---

### Step 4: Open the Application
Open your browser and navigate to:
```
http://localhost:8000/app
```
*(Or open `standalone_index.html` directly in your browser).*

---

## 🛠️ API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Server health check & sources count |
| `GET` | `/api/lm-status` | Tests connection to LM Studio and lists active models |
| `GET` | `/api/sources` | Lists all uploaded sources with character counts |
| `POST` | `/api/upload` | Uploads and extracts text from PDF, DOCX, XLSX, CSV, images |
| `GET` | `/api/sources/{id}/text` | Returns full extracted text of a source |
| `PUT` | `/api/sources/{id}/rename` | Renames source |
| `DELETE` | `/api/sources/{id}` | Deletes source and associated files |
| `POST` | `/api/sources/from-output` | Saves output studio markdown into `./sources` |
| `POST` | `/api/chat` | Server-Sent Events (SSE) grounded streaming chat proxy |
| `POST` | `/api/export/docx` | Generates and downloads styled Word document |
| `POST` | `/api/export/pptx` | Generates and downloads 16:9 widescreen PowerPoint deck |

---

## 📁 Directory Structure
```text
├── app.py                 # FastAPI backend with extractors, proxy, & docx/pptx builders
├── standalone_index.html  # Responsive 3-Panel Vanilla JS + Tailwind UI
├── requirements.txt       # Python dependencies
├── sources/               # Local directory for stored files & metadata
│   ├── files/             # Uploaded source binaries and extracted .txt files
│   └── sources.json       # Metadata registry
└── exports/               # Generated documents cache
```
