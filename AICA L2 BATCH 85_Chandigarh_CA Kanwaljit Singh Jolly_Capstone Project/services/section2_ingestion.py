"""
SECTION 2 - STORAGE, FILE SYSTEM & ONEDRIVE CONTRACT

Pure ingestion layer - NO interpretation, NO inference, NO AI.
Implements SECTION_2.md specification exactly.

Purpose:
- Recursively enumerate OneDrive files
- Assign logical roles based on folder names
- Download files and compute hashes
- Extract raw text from workflow files
- Generate ingestion manifest

This is the ONLY input to Section 3.
"""

import hashlib
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from services.file_processor import extract_docx_text, extract_pdf_text
from services.file_source import FileSource, OneDriveSource

# Configure logging for Section 2
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ==================== 2.1 STORAGE AUTHORITY MODEL ====================

"""
OneDrive is the single source of truth.
Files are:
- Intentionally placed
- Correctly named (but not semantically perfect)
- Stable for the duration of a run
No tampering detection.
"""


# ==================== 2.2 / 2.3 STORAGE ACCESS + ENUMERATION ====================
# File access and recursive enumeration are provided by services.file_source
# (OneDriveSource for production, LocalDirSource for offline/tests). Section 2 is
# storage-agnostic and only depends on the FileSource interface.


# ==================== 2.4 LOGICAL ROLE ASSIGNMENT ====================

"""
Roles are labels, not enforcement rules.

Role Assignment Strategy (SIMPLIFIED):
- Primary signal: Folder name (high confidence)
- Secondary signal: File content keywords (only if ambiguous)

Folder name contains:
- "input", "source", "raw" -> INPUTS
- "output", "result", "final" -> OUTPUTS
- "workflow", "process", "sop" -> WORKFLOW
- "client", "customer", "profile" -> CLIENT_CONTEXT
- "law", "kb", "reference", "knowledge" -> KNOWLEDGE_BASE
- No match -> OTHER
"""

ROLE_KEYWORDS = {
    'INPUTS': ['input', 'source', 'raw', 'original'],
    'OUTPUTS': ['output', 'result', 'final', 'deliverable'],
    'WORKFLOW': ['workflow', 'process', 'sop', 'procedure', 'steps'],
    'CLIENT_CONTEXT': ['client', 'customer', 'profile', 'context'],
    'KNOWLEDGE_BASE': ['law', 'kb', 'reference', 'knowledge', 'legal', 'regulation']
}


def assign_role(path: str) -> str:
    """
    Assign logical role based on path keywords.

    Args:
        path: File or folder path

    Returns:
        Role string (INPUTS, OUTPUTS, WORKFLOW, CLIENT_CONTEXT, KNOWLEDGE_BASE, OTHER)
    """
    path_lower = path.lower()

    # Check each role's keywords
    for role, keywords in ROLE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in path_lower:
                return role

    # No match
    return 'OTHER'


def build_role_index(files: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Build index of files by role.

    Args:
        files: List of file metadata dicts

    Returns:
        {
            "INPUTS": [...],
            "OUTPUTS": [...],
            "WORKFLOW": [...],
            "CLIENT_CONTEXT": [...],
            "KNOWLEDGE_BASE": [...],
            "OTHER": [...]
        }
    """
    role_index = {
        'INPUTS': [],
        'OUTPUTS': [],
        'WORKFLOW': [],
        'CLIENT_CONTEXT': [],
        'KNOWLEDGE_BASE': [],
        'OTHER': []
    }

    for file in files:
        role = assign_role(file['path'])
        role_index[role].append(file)

    return role_index


# ==================== 2.5 FILE DOWNLOAD & CONTENT ACCESS ====================

def download_file_with_hash(source: FileSource, file_path: str, local_dest: str) -> str:
    """
    Download a file via the given FileSource and compute its SHA-256 hash.

    Args:
        source: FileSource instance (OneDrive or local)
        file_path: Source-relative file path
        local_dest: Local destination path

    Returns:
        SHA-256 hash (hex string)
    """
    source.download(file_path, local_dest)

    sha256 = hashlib.sha256()
    with open(local_dest, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)

    return sha256.hexdigest()


# ==================== 2.7 WORKFLOW FILE HANDLING ====================

"""
Workflow files may be:
- .txt
- .docx
- .pdf
- .md

Multiple workflow files are allowed.
"""

WORKFLOW_EXTENSIONS = ['.txt', '.docx', '.pdf', '.md']


def is_workflow_file(filename: str) -> bool:
    """Check if file is a workflow file based on extension"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in WORKFLOW_EXTENSIONS


def extract_workflow_text(file_path: str) -> Dict[str, Any]:
    """
    Extract raw text from workflow file.

    Args:
        file_path: Local file path

    Returns:
        {
            "workflow_file": "Process.docx",
            "raw_text": "...",
            "sections": [...]  # If headings detected
        }
    """
    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()

    result = {
        'workflow_file': filename,
        'raw_text': '',
        'sections': []
    }

    try:
        if ext == '.txt' or ext == '.md':
            with open(file_path, 'r', encoding='utf-8') as f:
                result['raw_text'] = f.read()

        elif ext == '.docx':
            result['raw_text'] = extract_docx_text(file_path)

        elif ext == '.pdf':
            result['raw_text'] = extract_pdf_text(file_path)

        else:
            result['raw_text'] = f"[Unsupported workflow format: {ext}]"

    except Exception as e:
        result['raw_text'] = f"[Error extracting text: {str(e)}]"

    return result


# ==================== 2.8 CLIENT INFO HANDLING ====================

"""
2.8.1 Core Rule
Client info has NO PREDEFINED SCHEMA at ingestion time.
Anything inside CLIENT_CONTEXT is accepted.
"""

def extract_client_context_text(file_path: str) -> Dict[str, Any]:
    """
    Extract text from client context file (free-form).

    Args:
        file_path: Local file path

    Returns:
        {
            "file": "special_instructions.pdf",
            "text": "...",
            "binary_present": true
        }
    """
    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()

    result = {
        'file': filename,
        'text': '',
        'binary_present': True
    }

    try:
        if ext == '.txt' or ext == '.md':
            with open(file_path, 'r', encoding='utf-8') as f:
                result['text'] = f.read()

        elif ext == '.docx':
            result['text'] = extract_docx_text(file_path)

        elif ext == '.pdf':
            result['text'] = extract_pdf_text(file_path)

        else:
            # Binary file - text extraction not possible
            result['text'] = f"[Binary file: {ext}]"

    except Exception as e:
        result['text'] = f"[Error: {str(e)}]"

    return result


# ==================== 2.9 KNOWLEDGE BASE HANDLING ====================

"""
2.9.1 Accepted Content
- Laws, PDFs, DOCX, notes, link lists, screenshots, emails
- No assumptions
"""

def extract_kb_text(file_path: str) -> Dict[str, Any]:
    """
    Extract text from knowledge base file (free-form).

    Similar to client context extraction.
    """
    return extract_client_context_text(file_path)


# ==================== 2.11 INGESTION MANIFEST ====================

class Section2Ingestion:
    """
    Main Section 2 ingestion orchestrator.
    Follows implementation order from 2.12.
    """

    def __init__(self, task_id: str, onedrive_root_path: str, local_work_dir: str,
                 file_source: Optional[FileSource] = None, access_token: Optional[str] = None):
        """
        Args:
            task_id: Unique task identifier
            onedrive_root_path: Source-relative root path (e.g., "/Documents/Tasks/Invoice")
            local_work_dir: Local directory for downloads
            file_source: FileSource to read from (preferred). If omitted, an
                OneDriveSource is built from access_token (backward compatible).
            access_token: OneDrive access token (used only if file_source is None).
        """
        self.task_id = task_id
        self.onedrive_root_path = onedrive_root_path
        if file_source is None:
            if not access_token:
                raise ValueError("Section2Ingestion requires either file_source or access_token")
            file_source = OneDriveSource(access_token)
        self.file_source = file_source
        self.local_work_dir = local_work_dir

        # Create work directory
        os.makedirs(local_work_dir, exist_ok=True)

    def ingest(self) -> Dict[str, Any]:
        """
        Execute full Section 2 ingestion pipeline.

        Returns:
            Ingestion manifest (as specified in 2.11)
        """
        logger.info("=" * 80)
        logger.info("SECTION 2: INGESTION START")
        logger.info("=" * 80)
        print("=" * 80, flush=True)
        print("SECTION 2: INGESTION START", flush=True)
        print("=" * 80, flush=True)
        sys.stdout.flush()

        # Step 1: Recursive listing via FileSource
        logger.info("[1/6] Recursive file listing...")
        print("\n[1/6] Recursive file listing...", flush=True)
        sys.stdout.flush()
        enumeration = self.file_source.enumerate_tree(self.onedrive_root_path)
        logger.info("[OK] Enumeration complete!")
        folders = enumeration['folders']
        files = enumeration['files']
        logger.info(f"   Found {len(folders)} folders, {len(files)} files")
        print(f"   [OK] Found {len(folders)} folders", flush=True)
        print(f"   [OK] Found {len(files)} files", flush=True)
        sys.stdout.flush()

        # Step 2: Path preservation + metadata capture
        # (Already done in enumeration)
        print("\n[2/6] Path preservation + metadata capture")
        print("   [OK] Metadata preserved for all files")

        # Step 3: Role assignment via folder name
        print("\n[3/6] Role assignment...")
        role_index = build_role_index(files)
        for role, role_files in role_index.items():
            if role_files:
                print(f"   [OK] {role}: {len(role_files)} file(s)")

        # Step 4: File downloading + hashing
        print("\n[4/6] File downloading + hashing...")
        file_hashes = {}
        for file in files:
            local_path = os.path.join(self.local_work_dir, file['path'].lstrip('/'))
            try:
                file_hash = download_file_with_hash(self.file_source, file['path'], local_path)
                file_hashes[file['path']] = file_hash
                file['local_path'] = local_path
                file['sha256'] = file_hash
            except Exception as e:
                print(f"   [WARNING] Failed to download {file['path']}: {e}")
                file['local_path'] = None
                file['sha256'] = None

        print(f"   [OK] Downloaded {len(file_hashes)} files")

        # Step 5: Workflow text extraction
        print("\n[5/6] Workflow text extraction...")
        workflow_files = []
        for file in role_index['WORKFLOW']:
            if file.get('local_path') and is_workflow_file(file['name']):
                workflow_data = extract_workflow_text(file['local_path'])
                workflow_files.append(workflow_data)
                print(f"   [OK] Extracted: {workflow_data['workflow_file']}")

        if not workflow_files:
            print("   [WARNING] No workflow files found")

        # Extract client context files
        client_context_files = []
        for file in role_index['CLIENT_CONTEXT']:
            if file.get('local_path'):
                client_data = extract_client_context_text(file['local_path'])
                client_context_files.append(client_data)

        # Extract knowledge base files
        knowledge_base_files = []
        for file in role_index['KNOWLEDGE_BASE']:
            if file.get('local_path'):
                kb_data = extract_kb_text(file['local_path'])
                knowledge_base_files.append(kb_data)

        # Step 6: Manifest generation
        print("\n[6/6] Manifest generation...")
        manifest = {
            'task_id': self.task_id,
            'onedrive_root_path': self.onedrive_root_path,
            'ingestion_timestamp': datetime.utcnow().isoformat(),
            'folders': folders,
            'files': files,
            'role_index': role_index,
            'workflow_files': workflow_files,
            'client_context_files': client_context_files,
            'knowledge_base_files': knowledge_base_files
        }

        print("   [OK] Manifest generated")
        print("\n" + "=" * 80)
        print("SECTION 2: INGESTION COMPLETE")
        print("=" * 80)

        return manifest


# ==================== CONVENIENCE FUNCTION ====================

def ingest_from_onedrive(task_id: str, onedrive_root_path: str, access_token: str,
                         local_work_dir: str = None) -> Dict[str, Any]:
    """
    Convenience function for Section 2 ingestion.

    Args:
        task_id: Unique task identifier
        onedrive_root_path: OneDrive folder path
        access_token: OneDrive access token
        local_work_dir: Optional local work directory (default: /tmp/section2_{task_id})

    Returns:
        Ingestion manifest
    """
    if local_work_dir is None:
        local_work_dir = f"/tmp/section2_{task_id}"

    ingestion = Section2Ingestion(task_id, onedrive_root_path, local_work_dir, access_token=access_token)
    return ingestion.ingest()
