"""
Agents API
Handles agent CRUD for authenticated users.
"""
import json
import os
import random
import secrets
import string
import tempfile
from datetime import datetime

import requests
from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename

from supabase_config import supabase_admin
from api.auth import can_access_agent, request_context

agents_bp = Blueprint('agents', __name__)

# Allowed file types for reference files
ALLOWED_EXTENSIONS = {'.txt', '.md', '.csv', '.xlsx', '.xls', '.pdf', '.docx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

def allowed_file(filename):
    """Check if file extension is allowed"""
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


def normalize_kb_folder_paths(value):
    if value is None:
        return None
    if isinstance(value, str):
        raw_parts = []
        for part in value.replace(',', '\n').splitlines():
            if part is None:
                continue
            raw_parts.append(part)
        value = raw_parts
    if not isinstance(value, list):
        return None
    cleaned = []
    for item in value:
        if not isinstance(item, str):
            continue
        path = item.strip()
        if not path:
            continue
        if not path.startswith('/'):
            path = '/' + path
        cleaned.append(path)
    if not cleaned:
        return []
    seen = set()
    unique = []
    for path in cleaned:
        if path in seen:
            continue
        seen.add(path)
        unique.append(path)
    return unique


def generate_temp_password(length=12):
    """Generate a temporary password with mixed characters."""
    min_length = max(length, 8)
    password_chars = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits)
    ]
    alphabet = string.ascii_letters + string.digits
    password_chars.extend(secrets.choice(alphabet) for _ in range(min_length - len(password_chars)))
    random.SystemRandom().shuffle(password_chars)
    return ''.join(password_chars)


def send_temporary_password_email(to_email, temp_password, display_name=None):
    resend_api_key = os.getenv("RESEND_API_KEY")
    resend_from = os.getenv("RESEND_FROM")
    app_url = (os.getenv("APP_URL") or "").strip()

    if not resend_api_key or not resend_from:
        raise ValueError("Resend configuration is missing (RESEND_API_KEY/RESEND_FROM).")

    greeting_name = display_name or to_email.split('@')[0]
    lines = [
        f"Hi {greeting_name},",
        "",
        "An account has been created for you in Task Checker.",
        "Use the temporary password below to sign in:",
        "",
        f"Temporary password: {temp_password}",
        "",
        "For security, you will be prompted to change this password immediately after logging in."
    ]
    if app_url:
        lines.extend(["", f"Login: {app_url}"])

    payload = {
        "from": resend_from,
        "to": [to_email],
        "subject": "Your Task Checker temporary password",
        "text": "\n".join(lines)
    }

    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {resend_api_key}",
            "Content-Type": "application/json"
        },
        data=json.dumps(payload),
        timeout=15
    )

    if response.status_code >= 300:
        raise RuntimeError(f"Resend API error: {response.status_code} {response.text}")


def get_user_id_from_request():
    context, error = request_context()
    if error:
        return None, None, error
    return context.user_id, context.role, None


@agents_bp.route('/agents', methods=['GET'])
def list_agents():
    context, error_response = request_context()
    if error_response:
        return error_response

    query = supabase_admin.table('agents').select('*').eq('tenant_id', context.tenant_id).eq('is_active', True)
    if not context.is_superadmin:
        assignment_rows = supabase_admin.table('agent_assignments').select('agent_id') \
            .eq('tenant_id', context.tenant_id).eq('admin_user_id', context.user_id).execute().data or []
        agent_ids = [row['agent_id'] for row in assignment_rows]
        if not agent_ids:
            return jsonify([]), 200
        query = query.in_('id', agent_ids)
    response = query.order('created_at', desc=True).execute()

    return jsonify(response.data or []), 200


@agents_bp.route('/agents', methods=['POST'])
def create_agent():
    context, error_response = request_context()
    if error_response:
        return error_response
    user_id = context.user_id

    payload = request.get_json(force=True, silent=True) or {}
    name = (payload.get('name') or '').strip()
    system_prompt = (payload.get('system_prompt') or '').strip()
    kb_folder_paths = None
    kb_file_paths = None
    if 'kb_folder_paths' in payload:
        kb_folder_paths = normalize_kb_folder_paths(payload.get('kb_folder_paths'))
        if kb_folder_paths is None:
            return jsonify({'error': 'kb_folder_paths must be a list of folder paths'}), 400
    if 'kb_file_paths' in payload:
        kb_file_paths = normalize_kb_folder_paths(payload.get('kb_file_paths'))
        if kb_file_paths is None:
            return jsonify({'error': 'kb_file_paths must be a list of file paths'}), 400
    reference_file_paths = None
    if 'reference_file_paths' in payload:
        reference_file_paths = payload.get('reference_file_paths')
        # reference_file_paths should be a dict with arrays
        if reference_file_paths and not isinstance(reference_file_paths, dict):
            return jsonify({'error': 'reference_file_paths must be a dictionary'}), 400

    if not name:
        return jsonify({'error': 'Agent name is required'}), 400

    assigned_admin_ids = payload.get('assigned_admin_ids') or []
    if not isinstance(assigned_admin_ids, list):
        return jsonify({'error': 'assigned_admin_ids must be a list'}), 400
    if not context.is_superadmin and context.user_id not in {str(item) for item in assigned_admin_ids}:
        assigned_admin_ids.append(context.user_id)

    codex_model = (payload.get('codex_model') or 'gpt-5.6-sol').strip()
    codex_effort = (payload.get('codex_reasoning_effort') or 'xhigh').strip()
    if codex_model not in {'gpt-5.6-sol', 'gpt-5.6-terra', 'gpt-5.6-luna'}:
        return jsonify({'error': 'Invalid Codex model'}), 400
    if codex_effort not in {'low', 'medium', 'high', 'xhigh'}:
        return jsonify({'error': 'Invalid Codex reasoning effort'}), 400

    agent_data = {
        'name': name,
        'description': (payload.get('description') or '').strip() or None,
        'system_prompt': system_prompt,
        # Retained for compatibility with the legacy NOT NULL column. File
        # assignments now belong to tasks, not agents.
        'onedrive_folder_path': '',
        'user_id': user_id,
        'tenant_id': context.tenant_id,
        'created_by': user_id,
        'workflow_text': system_prompt,
        'codex_model': codex_model,
        'codex_reasoning_effort': codex_effort
    }
    if kb_folder_paths is not None:
        agent_data['kb_folder_paths'] = kb_folder_paths
    if kb_file_paths is not None:
        agent_data['kb_file_paths'] = kb_file_paths
    if reference_file_paths is not None:
        agent_data['reference_file_paths'] = reference_file_paths

    response = supabase_admin.table('agents').insert(agent_data).execute()
    data = response.data[0] if response.data else agent_data

    if assigned_admin_ids and data.get('id'):
        valid = supabase_admin.table('tenant_memberships').select('user_id') \
            .eq('tenant_id', context.tenant_id).eq('role', 'admin').eq('status', 'active') \
            .in_('user_id', assigned_admin_ids).execute().data or []
        valid_ids = {str(row['user_id']) for row in valid}
        if valid_ids != {str(item) for item in assigned_admin_ids}:
            supabase_admin.table('agents').delete().eq('id', data['id']).eq('tenant_id', context.tenant_id).execute()
            return jsonify({'error': 'Assignments must target active admins in this tenant'}), 400
        supabase_admin.table('agent_assignments').insert([{
            'tenant_id': context.tenant_id, 'agent_id': data['id'],
            'admin_user_id': admin_id, 'assigned_by': user_id
        } for admin_id in valid_ids]).execute()

    return jsonify(data), 201


@agents_bp.route('/agents/<agent_id>', methods=['PUT'])
def update_agent(agent_id):
    context, error_response = request_context()
    if error_response:
        return error_response
    if not can_access_agent(context, agent_id):
        return jsonify({'error': 'Agent not found or access denied'}), 404
    user_id = context.user_id

    payload = request.get_json(force=True, silent=True) or {}
    updates = {}

    if 'name' in payload:
        updates['name'] = (payload.get('name') or '').strip()
    if 'description' in payload:
        updates['description'] = (payload.get('description') or '').strip() or None
    if 'system_prompt' in payload:
        updates['system_prompt'] = (payload.get('system_prompt') or '').strip()
        updates['workflow_text'] = updates['system_prompt']
    if 'workflow_text' in payload:
        updates['workflow_text'] = (payload.get('workflow_text') or '').strip()
        updates['system_prompt'] = updates['workflow_text']
    if 'codex_model' in payload:
        model = (payload.get('codex_model') or '').strip()
        if model not in {'gpt-5.6-sol', 'gpt-5.6-terra', 'gpt-5.6-luna'}:
            return jsonify({'error': 'Invalid Codex model'}), 400
        updates['codex_model'] = model
    if 'codex_reasoning_effort' in payload:
        effort = (payload.get('codex_reasoning_effort') or '').strip()
        if effort not in {'low', 'medium', 'high', 'xhigh'}:
            return jsonify({'error': 'Invalid Codex reasoning effort'}), 400
        updates['codex_reasoning_effort'] = effort
    if 'kb_folder_paths' in payload:
        kb_folder_paths = normalize_kb_folder_paths(payload.get('kb_folder_paths'))
        if kb_folder_paths is None:
            return jsonify({'error': 'kb_folder_paths must be a list of folder paths'}), 400
        updates['kb_folder_paths'] = kb_folder_paths
    if 'kb_file_paths' in payload:
        kb_file_paths = normalize_kb_folder_paths(payload.get('kb_file_paths'))
        if kb_file_paths is None:
            return jsonify({'error': 'kb_file_paths must be a list of file paths'}), 400
        updates['kb_file_paths'] = kb_file_paths
    if 'reference_file_paths' in payload:
        reference_file_paths = payload.get('reference_file_paths')
        if reference_file_paths and not isinstance(reference_file_paths, dict):
            return jsonify({'error': 'reference_file_paths must be a dictionary'}), 400
        updates['reference_file_paths'] = reference_file_paths

    if not updates:
        return jsonify({'error': 'No valid fields to update'}), 400

    current = supabase_admin.table('agents').select('config_version').eq('id', agent_id) \
        .eq('tenant_id', context.tenant_id).limit(1).execute().data or []
    if not current:
        return jsonify({'error': 'Agent not found or access denied'}), 404
    updates['config_version'] = int(current[0].get('config_version') or 1) + 1
    response = supabase_admin.table('agents') \
        .update(updates) \
        .eq('id', agent_id) \
        .eq('tenant_id', context.tenant_id) \
        .execute()

    if not response.data:
        return jsonify({'error': 'Agent not found or access denied'}), 404

    return jsonify(response.data[0]), 200


@agents_bp.route('/agents/<agent_id>', methods=['DELETE'])
def delete_agent(agent_id):
    context, error_response = request_context()
    if error_response:
        return error_response
    if not can_access_agent(context, agent_id):
        return jsonify({'error': 'Agent not found or access denied'}), 404

    archived_at = datetime.utcnow().isoformat()
    response = supabase_admin.table('agents') \
        .update({'is_active': False, 'archived_at': archived_at}) \
        .eq('id', agent_id) \
        .eq('tenant_id', context.tenant_id) \
        .execute()

    if not response.data:
        return jsonify({'error': 'Agent not found or access denied'}), 404

    supabase_admin.table('tasks') \
        .update({'is_active': False, 'archived_at': archived_at}) \
        .eq('agent_id', agent_id) \
        .eq('tenant_id', context.tenant_id) \
        .execute()

    return jsonify({'success': True}), 200


# ==================== REFERENCE FILES ENDPOINTS ====================

@agents_bp.route('/agents/<agent_id>/reference-files', methods=['POST'])
def upload_reference_file(agent_id):
    """
    Upload a reference file for an agent

    Form data:
        file: File upload
        file_type: 'example_input' | 'example_output' | 'quality_standard' | 'reference_doc'
    """
    user_id, user_role, error_response = get_user_id_from_request()
    if error_response:
        return error_response

    context, _ = request_context()
    if not can_access_agent(context, agent_id):
        return jsonify({'error': 'Agent not found'}), 404

    # Verify agent exists
    agent_response = supabase_admin.table('agents') \
        .select('id') \
        .eq('id', agent_id) \
        .single() \
        .execute()

    if not agent_response.data:
        return jsonify({'error': 'Agent not found'}), 404

    # Check if file is in request
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Get file_type from form data
    file_type = request.form.get('file_type', '').strip()
    if file_type not in ['example_input', 'example_output', 'quality_standard', 'reference_doc']:
        return jsonify({'error': 'Invalid file_type'}), 400

    # Validate file extension
    if not allowed_file(file.filename):
        return jsonify({'error': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

    # Check file size (read in chunks to avoid loading large files into memory)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_FILE_SIZE:
        return jsonify({'error': f'File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)} MB'}), 400

    try:
        # Secure filename
        filename = secure_filename(file.filename)

        # Storage path: {user_id}/{agent_id}/{filename}
        storage_path = f"{user_id}/{agent_id}/{filename}"

        # Upload to Supabase Storage
        file_data = file.read()
        supabase_admin.storage.from_('agent-reference-files').upload(
            storage_path,
            file_data,
            file_options={"content-type": file.content_type or "application/octet-stream"}
        )

        # Insert metadata into database
        file_metadata = {
            'agent_id': agent_id,
            'user_id': user_id,
            'file_name': filename,
            'file_type': file_type,
            'storage_path': storage_path,
            'file_size': file_size
        }

        db_response = supabase_admin.table('agent_reference_files') \
            .insert(file_metadata) \
            .execute()

        if not db_response.data:
            # If DB insert fails, try to clean up storage
            try:
                supabase_admin.storage.from_('agent-reference-files').remove([storage_path])
            except Exception:
                pass
            return jsonify({'error': 'Failed to save file metadata'}), 500

        return jsonify(db_response.data[0]), 201

    except Exception as e:
        print(f"❌ Error uploading reference file: {e}")
        return jsonify({'error': f'Failed to upload file: {str(e)}'}), 500


@agents_bp.route('/agents/<agent_id>/reference-files', methods=['GET'])
def list_reference_files(agent_id):
    """List all reference files for an agent"""
    user_id, user_role, error_response = get_user_id_from_request()
    if error_response:
        return error_response
    context, _ = request_context()
    if not can_access_agent(context, agent_id):
        return jsonify({'error': 'Agent not found'}), 404

    # Verify agent exists
    agent_response = supabase_admin.table('agents') \
        .select('id') \
        .eq('id', agent_id) \
        .single() \
        .execute()

    if not agent_response.data:
        return jsonify({'error': 'Agent not found'}), 404

    # Get all reference files for this agent
    files_response = supabase_admin.table('agent_reference_files') \
        .select('*') \
        .eq('agent_id', agent_id) \
        .order('uploaded_at', desc=True) \
        .execute()

    return jsonify(files_response.data or []), 200


@agents_bp.route('/agents/<agent_id>/reference-files/<file_id>', methods=['GET'])
def download_reference_file(agent_id, file_id):
    """Download a specific reference file"""
    user_id, user_role, error_response = get_user_id_from_request()
    if error_response:
        return error_response
    context, _ = request_context()
    if not can_access_agent(context, agent_id):
        return jsonify({'error': 'Agent not found'}), 404

    # Verify agent exists
    agent_response = supabase_admin.table('agents') \
        .select('id') \
        .eq('id', agent_id) \
        .single() \
        .execute()

    if not agent_response.data:
        return jsonify({'error': 'Agent not found'}), 404

    # Get file metadata
    file_response = supabase_admin.table('agent_reference_files') \
        .select('*') \
        .eq('id', file_id) \
        .eq('agent_id', agent_id) \
        .single() \
        .execute()

    if not file_response.data:
        return jsonify({'error': 'File not found'}), 404

    file_data = file_response.data
    storage_path = file_data['storage_path']
    file_name = file_data['file_name']

    try:
        # Download file from storage
        file_bytes = supabase_admin.storage.from_('agent-reference-files').download(storage_path)

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_name)[1]) as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name

        # Send file
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=file_name,
            mimetype='application/octet-stream'
        )

    except Exception as e:
        print(f"❌ Error downloading file: {e}")
        return jsonify({'error': f'Failed to download file: {str(e)}'}), 500


@agents_bp.route('/agents/<agent_id>/reference-files/<file_id>', methods=['DELETE'])
def delete_reference_file(agent_id, file_id):
    """Delete a reference file"""
    user_id, user_role, error_response = get_user_id_from_request()
    if error_response:
        return error_response

    context, _ = request_context()
    if not can_access_agent(context, agent_id):
        return jsonify({'error': 'Agent not found'}), 404

    # Verify agent exists
    agent_response = supabase_admin.table('agents') \
        .select('id') \
        .eq('id', agent_id) \
        .single() \
        .execute()

    if not agent_response.data:
        return jsonify({'error': 'Agent not found'}), 404

    # Get file metadata
    file_response = supabase_admin.table('agent_reference_files') \
        .select('*') \
        .eq('id', file_id) \
        .eq('agent_id', agent_id) \
        .single() \
        .execute()

    if not file_response.data:
        return jsonify({'error': 'File not found'}), 404

    storage_path = file_response.data['storage_path']

    try:
        # Delete from storage
        supabase_admin.storage.from_('agent-reference-files').remove([storage_path])

        # Delete from database
        supabase_admin.table('agent_reference_files') \
            .delete() \
            .eq('id', file_id) \
            .execute()

        return jsonify({'success': True}), 200

    except Exception as e:
        print(f"❌ Error deleting file: {e}")
        return jsonify({'error': f'Failed to delete file: {str(e)}'}), 500


# ==================== USER MANAGEMENT ENDPOINTS ====================

@agents_bp.route('/auth/profile', methods=['GET'])
def get_profile():
    """Get current user's profile including role"""
    user_id, user_role, error_response = get_user_id_from_request()
    if error_response:
        return error_response

    # Fetch user profile
    response = supabase_admin.table('profiles') \
        .select('id, email, display_name, role, created_at') \
        .eq('id', user_id) \
        .single() \
        .execute()

    if not response.data:
        return jsonify({'error': 'Profile not found'}), 404

    profile = dict(response.data)
    context, _ = request_context()
    profile['role'] = context.role
    profile['tenant_id'] = context.tenant_id
    return jsonify(profile), 200


@agents_bp.route('/users', methods=['GET'])
def list_users():
    """List tenant users so agents can be assigned to active admins."""
    context, error_response = request_context()
    if error_response:
        return error_response
    memberships = supabase_admin.table('tenant_memberships').select('user_id,role,status,created_at') \
        .eq('tenant_id', context.tenant_id)
    if not context.is_superadmin:
        memberships = memberships.eq('role', 'admin').eq('status', 'active')
    memberships = memberships.order('created_at', desc=True).execute().data or []
    ids = [row['user_id'] for row in memberships]
    profiles = supabase_admin.table('profiles').select('id,email,display_name,created_at').in_('id', ids).execute().data if ids else []
    profile_map = {str(row['id']): row for row in (profiles or [])}
    return jsonify([{**profile_map.get(str(row['user_id']), {'id': row['user_id']}), 'role': row['role'], 'status': row['status']} for row in memberships]), 200


@agents_bp.route('/users', methods=['POST'])
def create_user():
    """Create a new admin user (super_admin only)"""
    context, error_response = request_context('super_admin')
    if error_response:
        return error_response

    payload = request.get_json(force=True, silent=True) or {}
    email = (payload.get('email') or '').strip().lower()
    provided_password = (payload.get('password') or '').strip()
    display_name = (payload.get('display_name') or '').strip()
    new_user_role = 'admin'

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    temp_password = provided_password or generate_temp_password()
    new_user_id = None

    try:
        # Create user in Supabase Auth
        auth_response = supabase_admin.auth.admin.create_user({
            "email": email,
            "password": temp_password,
            "email_confirm": True,
            "user_metadata": {
                "display_name": display_name or email,
                "must_change_password": True
            }
        })

        new_user_id = auth_response.user.id

        # Create profile with role
        profile_data = {
            'id': new_user_id,
            'email': email,
            'display_name': display_name or email,
            'role': new_user_role
        }

        profile_response = (
            supabase_admin.table('profiles')
            .insert(profile_data)
            .execute()
        )

        if not profile_response.data:
            raise RuntimeError("Failed to create profile for new user")

        supabase_admin.table('tenant_memberships').insert({
            'tenant_id': context.tenant_id,
            'user_id': new_user_id,
            'role': 'admin',
            'status': 'active'
        }).execute()

        send_temporary_password_email(email, temp_password, display_name or email)

        response_payload = dict(profile_response.data[0])
        response_payload["temp_password_emailed"] = True
        return jsonify(response_payload), 201

    except Exception as e:
        if new_user_id:
            try:
                supabase_admin.auth.admin.delete_user(new_user_id)
            except Exception:
                pass
        print(f"??O Error creating user: {e}")
        return jsonify({'error': f'Failed to create user: {str(e)}'}), 500


@agents_bp.route('/users/<target_user_id>', methods=['DELETE'])
def delete_user(target_user_id):
    """Delete a user (super_admin only, cannot delete self)"""
    context, error_response = request_context('super_admin')
    if error_response:
        return error_response
    user_id = context.user_id

    # Cannot delete self
    if user_id == target_user_id:
        return jsonify({'error': 'Cannot delete your own account'}), 400

    try:
        membership = supabase_admin.table('tenant_memberships').select('role').eq('tenant_id', context.tenant_id) \
            .eq('user_id', target_user_id).limit(1).execute().data or []
        if not membership or membership[0]['role'] != 'admin':
            return jsonify({'error': 'Admin not found in this tenant'}), 404
        # Delete user from Supabase Auth
        supabase_admin.auth.admin.delete_user(target_user_id)

        # Profile will be automatically deleted due to CASCADE foreign key
        # (profiles.id references auth.users.id with ON DELETE CASCADE)

        return jsonify({'success': True}), 200

    except Exception as e:
        print(f"❌ Error deleting user: {e}")
        return jsonify({'error': f'Failed to delete user: {str(e)}'}), 500
