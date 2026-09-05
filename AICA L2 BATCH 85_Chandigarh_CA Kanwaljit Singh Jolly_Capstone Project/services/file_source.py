"""
FileSource — storage abstraction for Section 2 ingestion.

Section 2 should not care *where* files come from. This module defines a small
interface with two implementations:

- OneDriveSource: enumerates/downloads via the Microsoft Graph API (production).
- LocalDirSource: enumerates/downloads from a local directory tree (tests, offline runs).

Both produce the same enumeration shape so the rest of the pipeline is unchanged:

    {
        "folders": [{"path": "/Inputs", "name": "Inputs", "onedrive_id": "..."}],
        "files":   [{"onedrive_file_id": "...", "path": "/Inputs/a.pdf", "name": "a.pdf",
                     "size_bytes": 123, "mime_type": "application/pdf", "last_modified": "..."}]
    }

Paths are POSIX-style and rooted at the source root with a leading "/", mirroring
OneDrive paths, so the existing folder-name role assignment keeps working.
"""

import mimetypes
import os
import shutil
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests


class FileSource(ABC):
    """Abstract source of files for ingestion."""

    @abstractmethod
    def enumerate_tree(self, root_path: str) -> Dict[str, List[Dict[str, Any]]]:
        """Recursively enumerate folders and files under root_path."""
        raise NotImplementedError

    @abstractmethod
    def download(self, remote_path: str, local_dest: str) -> None:
        """Download/copy a single file identified by remote_path to local_dest."""
        raise NotImplementedError


# ==================== OneDrive (Microsoft Graph) ====================

class OneDriveSource(FileSource):
    """Microsoft Graph API source (Files.Read.All scope)."""

    GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }

    def _list_folder_contents(self, folder_path: str) -> List[Dict[str, Any]]:
        encoded_path = requests.utils.quote(folder_path)
        url = f"{self.GRAPH_API_ENDPOINT}/me/drive/root:{encoded_path}:/children"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json().get('value', [])

    def enumerate_tree(self, root_path: str) -> Dict[str, List[Dict[str, Any]]]:
        folders: List[Dict[str, Any]] = []
        files: List[Dict[str, Any]] = []

        def recurse(current_path: str):
            try:
                items = self._list_folder_contents(current_path)
            except Exception as e:  # noqa: BLE001 - surface as warning, keep enumerating siblings
                print(f"[WARNING] Failed to list {current_path}: {e}")
                return

            for item in items:
                item_name = item.get('name', '')
                item_path = f"{current_path}/{item_name}" if current_path != "/" else f"/{item_name}"

                if 'folder' in item:
                    folders.append({
                        'path': item_path,
                        'name': item_name,
                        'onedrive_id': item.get('id'),
                    })
                    recurse(item_path)
                elif 'file' in item:
                    files.append({
                        'onedrive_file_id': item.get('id'),
                        'path': item_path,
                        'name': item_name,
                        'size_bytes': item.get('size', 0),
                        'mime_type': item.get('file', {}).get('mimeType', 'application/octet-stream'),
                        'last_modified': item.get('lastModifiedDateTime', ''),
                    })

        recurse(root_path)
        return {'folders': folders, 'files': files}

    def download(self, remote_path: str, local_dest: str) -> None:
        encoded_path = requests.utils.quote(remote_path)
        url = f"{self.GRAPH_API_ENDPOINT}/me/drive/root:{encoded_path}:/content"
        response = requests.get(url, headers=self.headers, stream=True)
        response.raise_for_status()

        os.makedirs(os.path.dirname(local_dest), exist_ok=True)
        with open(local_dest, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)


# ==================== Local directory (offline / tests) ====================

class LocalDirSource(FileSource):
    """Read files from a local directory tree (no network, no credentials)."""

    def __init__(self, base_dir: str):
        if not os.path.isdir(base_dir):
            raise ValueError(f"LocalDirSource base_dir does not exist: {base_dir}")
        self.base_dir = os.path.abspath(base_dir)

    def _to_local(self, remote_path: str) -> str:
        rel = remote_path.lstrip('/').replace('\\', '/')
        parts = [p for p in rel.split('/') if p and p != '..']
        return os.path.join(self.base_dir, *parts)

    def enumerate_tree(self, root_path: str) -> Dict[str, List[Dict[str, Any]]]:
        folders: List[Dict[str, Any]] = []
        files: List[Dict[str, Any]] = []

        start = self._to_local(root_path) if root_path not in ('', '/') else self.base_dir

        for dirpath, dirnames, filenames in os.walk(start):
            for dirname in sorted(dirnames):
                abs_dir = os.path.join(dirpath, dirname)
                rel = os.path.relpath(abs_dir, self.base_dir).replace('\\', '/')
                folders.append({
                    'path': '/' + rel,
                    'name': dirname,
                    'onedrive_id': '/' + rel,
                })
            for filename in sorted(filenames):
                abs_file = os.path.join(dirpath, filename)
                rel = os.path.relpath(abs_file, self.base_dir).replace('\\', '/')
                try:
                    stat = os.stat(abs_file)
                    size = stat.st_size
                    last_modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                except OSError:
                    size = 0
                    last_modified = ''
                mime, _ = mimetypes.guess_type(filename)
                files.append({
                    'onedrive_file_id': '/' + rel,
                    'path': '/' + rel,
                    'name': filename,
                    'size_bytes': size,
                    'mime_type': mime or 'application/octet-stream',
                    'last_modified': last_modified,
                })

        return {'folders': folders, 'files': files}

    def download(self, remote_path: str, local_dest: str) -> None:
        src = self._to_local(remote_path)
        os.makedirs(os.path.dirname(local_dest), exist_ok=True)
        shutil.copy2(src, local_dest)
