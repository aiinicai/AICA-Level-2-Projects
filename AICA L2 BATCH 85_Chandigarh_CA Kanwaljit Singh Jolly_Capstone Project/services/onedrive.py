"""
OneDrive Service
Handles OneDrive authentication and file operations
"""
import os
from urllib.parse import quote

import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")


def _children_url(folder_path):
    if folder_path == "/":
        return "https://graph.microsoft.com/v1.0/me/drive/root/children"
    encoded_path = quote(folder_path, safe='/')
    return f"https://graph.microsoft.com/v1.0/me/drive/root:{encoded_path}:/children"


def _list_children(access_token, folder_path):
    """List every immediate child, following Microsoft Graph pagination."""
    headers = {'Authorization': f'Bearer {access_token}'}
    url = _children_url(folder_path)
    children = []

    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        result = response.json()
        children.extend(result.get('value', []))
        url = result.get('@odata.nextLink')

    return children


def get_user_onedrive_token(refresh_token):
    """
    Get fresh access token from refresh token

    Args:
        refresh_token: User's OneDrive refresh token

    Returns:
        str: Fresh access token

    Raises:
        Exception: If token refresh fails
    """
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        'client_id': CLIENT_ID,
        'scope': 'Files.Read offline_access',
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
        'client_secret': CLIENT_SECRET
    }

    response = requests.post(url, data=data)
    result = response.json()

    if 'access_token' not in result:
        raise Exception(f"Failed to refresh OneDrive token: {result.get('error_description', result)}")

    return result['access_token']


def download_onedrive_file(access_token, file_path, local_file_path):
    """
    Download a single OneDrive file

    Args:
        access_token: Valid OneDrive access token
        file_path: Path to OneDrive file (e.g., "/KB/document.pdf")
        local_file_path: Local path to save the file

    Raises:
        Exception: If file download fails
    """
    headers = {'Authorization': f'Bearer {access_token}'}

    # Ensure file path starts with /
    if not file_path.startswith('/'):
        file_path = '/' + file_path

    # Get file metadata first to get the item ID
    url = f"https://graph.microsoft.com/v1.0/me/drive/root:{quote(file_path, safe='/')}"
    response = requests.get(url, headers=headers)
    result = response.json()

    if 'id' not in result:
        error_msg = result.get('error', {}).get('message', str(result))
        raise Exception(f"Error accessing OneDrive file '{file_path}': {error_msg}")

    item_id = result['id']

    # Download file content
    file_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/content"
    file_response = requests.get(file_url, headers=headers)

    if file_response.status_code != 200:
        raise Exception(f"Failed to download file '{file_path}': HTTP {file_response.status_code}")

    # Write file to local path
    os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
    with open(local_file_path, 'wb') as f:
        f.write(file_response.content)

    print(f"✅ Downloaded: {os.path.basename(file_path)}")


def download_onedrive_folder(access_token, folder_path, local_dir):
    """
    Recursively download OneDrive folder to local directory

    Args:
        access_token: Valid OneDrive access token
        folder_path: Path to OneDrive folder (e.g., "/TaskChecker")
        local_dir: Local directory to download files to

    Returns:
        str: Path to local directory with downloaded files

    Raises:
        Exception: If folder download fails
    """
    headers = {'Authorization': f'Bearer {access_token}'}

    # Ensure folder path starts with /
    if not folder_path.startswith('/'):
        folder_path = '/' + folder_path

    os.makedirs(local_dir, exist_ok=True)

    for item in _list_children(access_token, folder_path):
        item_name = item['name']
        item_id = item['id']

        if item.get('folder'):
            # Recursively download subfolder
            subfolder_path = f"{folder_path}/{item_name}"
            local_subfolder = os.path.join(local_dir, item_name)
            download_onedrive_folder(access_token, subfolder_path, local_subfolder)
        else:
            # Download file
            file_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/content"
            file_response = requests.get(file_url, headers=headers)

            if file_response.status_code == 200:
                local_file_path = os.path.join(local_dir, item_name)
                with open(local_file_path, 'wb') as f:
                    f.write(file_response.content)
                print(f"✅ Downloaded: {item_name}")
            else:
                print(f"⚠️ Failed to download: {item_name}")

    return local_dir


def list_onedrive_folders(access_token, parent_path="/", max_depth=0):
    """
    List folders in OneDrive (for folder picker UI)

    Args:
        access_token: Valid OneDrive access token
        parent_path: Parent folder path to list
        max_depth: Maximum recursion depth (default: 0 = only immediate children)

    Returns:
        list: List of folder dictionaries with 'name' and 'path'
    """
    folders = []
    current_depth = parent_path.count('/')

    for item in _list_children(access_token, parent_path):
        if item.get('folder'):
            folder_name = item['name']
            folder_path = f"{parent_path}/{folder_name}" if parent_path != "/" else f"/{folder_name}"

            folders.append({
                'name': folder_name,
                'path': folder_path
            })

            # Recursively list subfolders if max_depth > 0
            if max_depth > 0 and current_depth < max_depth:
                try:
                    subfolders = list_onedrive_folders(access_token, folder_path, max_depth)
                    folders.extend(subfolders)
                except Exception as e:
                    print(f"Warning: Could not list subfolders in {folder_path}: {e}")

    return folders


def list_onedrive_files(access_token, folder_path="/KB", recursive=True):
    """
    List files in a OneDrive folder (for KB file picker UI)

    Args:
        access_token: Valid OneDrive access token
        folder_path: Folder path to list files from (default: /KB)
        recursive: Whether to include files from subfolders (default: True)

    Returns:
        list: List of file dictionaries with 'name', 'path', and 'size'
    """
    # Ensure folder path starts with /
    if not folder_path.startswith('/'):
        folder_path = '/' + folder_path

    files = []

    for item in _list_children(access_token, folder_path):
        item_name = item['name']
        item_path = f"{folder_path.rstrip('/')}/{item_name}"

        if item.get('file'):
            # It's a file
            files.append({
                'name': item_name,
                'path': item_path,
                'size': item.get('size', 0),
                'isFolder': False,
                'lastModified': item.get('lastModifiedDateTime')
            })
        elif item.get('folder'):
            # It's a folder - add it to the list
            files.append({
                'name': item_name,
                'path': item_path,
                'size': 0,
                'isFolder': True,
                'childCount': item.get('folder', {}).get('childCount', 0),
                'lastModified': item.get('lastModifiedDateTime')
            })

            # If recursive, also get files inside this folder
            if recursive:
                try:
                    subfiles = list_onedrive_files(access_token, item_path, recursive=True)
                    files.extend(subfiles)
                except Exception as e:
                    print(f"Warning: Could not list files in {item_path}: {e}")

    return files
