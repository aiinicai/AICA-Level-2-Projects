"""
Checker API
Handles task check execution requests
"""
import logging
import os
import posixpath

from flask import Blueprint, jsonify, request

from supabase_config import supabase_admin
from api.auth import request_context

# Setup logger
logger = logging.getLogger(__name__)
import shutil
import time
from datetime import datetime

from services.onedrive import get_user_onedrive_token, list_onedrive_files, list_onedrive_folders

checker_bp = Blueprint('checker', __name__)

ENABLE_LLM_TRIAGE = os.getenv('AI_ENABLE_LLM_TRIAGE', 'false').lower() == 'true'
ENABLE_CHUNKED_CHECKS = os.getenv('AI_ENABLE_CHUNKED_CHECKS', 'false').lower() == 'true'
FULL_FIDELITY_MODE = os.getenv('AI_FULL_FIDELITY_MODE', 'false').lower() == 'true'
ENABLE_ASYNC_CHECKS = os.getenv('TASKCHECKER_ASYNC_CHECKS', 'false').lower() == 'true'


def normalize_path_list(value):
    if not value:
        return []
    if isinstance(value, str):
        raw_parts = []
        for part in value.replace(',', '\n').splitlines():
            if part is None:
                continue
            raw_parts.append(part)
        value = raw_parts
    if not isinstance(value, list):
        return []
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
    return cleaned


def merge_unique(paths):
    seen = set()
    merged = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        merged.append(path)
    return merged


def normalize_onedrive_path(value):
    """Return one absolute, normalized OneDrive path."""
    raw = str(value or '/').strip().replace('\\', '/')
    return posixpath.normpath('/' + raw.lstrip('/'))


def onedrive_path_within_base(path, base_path):
    """Keep browser requests inside the tenant connection's configured root."""
    path = normalize_onedrive_path(path).casefold()
    base_path = normalize_onedrive_path(base_path).casefold()
    return base_path == '/' or path == base_path or path.startswith(base_path.rstrip('/') + '/')


@checker_bp.route('/onedrive/folders', methods=['GET'])
def list_folders():
    """
    List OneDrive folders for folder picker

    Query params:
        path (optional): Parent folder path to list (default: "/")
        connection_id (optional): Specific connection to use

    Expected Authorization header: Bearer <supabase_access_token>
    """
    try:
        context, error = request_context()
        if error:
            return error
        connection_response = supabase_admin.table('tenant_onedrive_connections') \
            .select('*').eq('tenant_id', context.tenant_id).single().execute()

        if not connection_response.data:
            return jsonify({'error': 'Connection not found'}), 400

        refresh_token = connection_response.data.get('refresh_token')
        base_path = normalize_onedrive_path(connection_response.data.get('base_folder_path', '/'))

        # Get parent path and depth from query params
        # If no path provided, use base path
        parent_path = normalize_onedrive_path(request.args.get('path', base_path))
        if not onedrive_path_within_base(parent_path, base_path):
            return jsonify({'error': 'Folder is outside the configured OneDrive base path'}), 400
        depth = int(request.args.get('depth', '0'))

        # Get fresh OneDrive access token only after the requested path is accepted.
        onedrive_token = get_user_onedrive_token(refresh_token)

        # List folders
        folders = list_onedrive_folders(onedrive_token, parent_path, max_depth=depth)

        return jsonify({
            'folders': folders,
            'parent_path': parent_path,
            'base_path': base_path
        })

    except Exception as e:
        print(f"Error listing OneDrive folders: {str(e)}")
        return jsonify({'error': str(e)}), 500


@checker_bp.route('/onedrive/files', methods=['GET'])
def list_files():
    """
    List OneDrive files for KB file picker

    Query params:
        folder (optional): Folder path to list files from
        connection_id (optional): Specific connection to use

    Expected Authorization header: Bearer <supabase_access_token>
    """
    try:
        context, error = request_context()
        if error:
            return error
        connection_response = supabase_admin.table('tenant_onedrive_connections') \
            .select('*').eq('tenant_id', context.tenant_id).single().execute()

        if not connection_response.data:
            return jsonify({'error': 'Connection not found'}), 400

        refresh_token = connection_response.data.get('refresh_token')
        base_path = normalize_onedrive_path(connection_response.data.get('base_folder_path', '/'))

        # Get folder path from query params (default to base path)
        folder_path = normalize_onedrive_path(request.args.get('folder', base_path))
        if not onedrive_path_within_base(folder_path, base_path):
            return jsonify({'error': 'Folder is outside the configured OneDrive base path'}), 400

        # Get fresh OneDrive access token only after the requested path is accepted.
        onedrive_token = get_user_onedrive_token(refresh_token)

        # Get recursive flag (default to false for file listing in specific folder)
        recursive = request.args.get('recursive', 'false').lower() == 'true'

        # List files
        files = list_onedrive_files(onedrive_token, folder_path, recursive=recursive)

        return jsonify({
            'files': files,
            'folder_path': folder_path,
            'base_path': base_path
        })

    except Exception as e:
        print(f"Error listing OneDrive files: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ==================== ONEDRIVE OAUTH FLOW ====================

@checker_bp.route('/onedrive/auth', methods=['GET'])
def onedrive_auth():
    """
    Initiate OneDrive OAuth flow
    This redirects to Microsoft login WITHOUT creating/signing in a new user
    """
    try:
        context, error = request_context('super_admin')
        if error:
            return error

        # Get Microsoft OAuth credentials from environment
        client_id = os.getenv('CLIENT_ID')
        tenant_id = os.getenv('TENANT_ID')
        redirect_uri = os.getenv('ONEDRIVE_REDIRECT_URI', 'http://localhost:5000/onedrive/callback')

        if not client_id or not tenant_id:
            return jsonify({'error': 'OAuth not configured. Missing CLIENT_ID or TENANT_ID'}), 500

        # Store user_id in session/state for callback
        # We'll encode it in the state parameter
        from itsdangerous import URLSafeTimedSerializer
        state = URLSafeTimedSerializer(os.getenv('FLASK_SECRET_KEY', 'task-checker-secret-key-change-in-production')) \
            .dumps({'user_id': context.user_id, 'tenant_id': context.tenant_id}, salt='onedrive-oauth')

        # Build Microsoft authorization URL
        auth_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
        params = {
            'client_id': client_id,
            'response_type': 'code',
            'redirect_uri': redirect_uri,
            'scope': 'Files.Read User.Read offline_access',
            'state': state,
            'response_mode': 'query',
            'prompt': 'select_account'
        }

        from urllib.parse import urlencode
        authorization_url = f"{auth_url}?{urlencode(params)}"

        return jsonify({'authorization_url': authorization_url}), 200

    except Exception as e:
        print(f"Error initiating OneDrive auth: {str(e)}")
        return jsonify({'error': str(e)}), 500


# NOTE: The OneDrive OAuth callback is handled in app_standalone.py at the
# root route /onedrive/callback (which matches the configured ONEDRIVE_REDIRECT_URI).


# ==================== ONEDRIVE CONNECTIONS MANAGEMENT ====================

@checker_bp.route('/onedrive/connections', methods=['GET'])
def list_onedrive_connections():
    """List the tenant connection available to task and agent file pickers."""
    try:
        context, error = request_context()
        if error:
            return error

        # Get all OneDrive connections for this user
        try:
            connections_response = supabase_admin.table('tenant_onedrive_connections') \
                .select('tenant_id, account_name, account_email, base_folder_path, created_at') \
                .eq('tenant_id', context.tenant_id).execute()
            connections = [{**row, 'id': row['tenant_id'], 'is_active': True} for row in (connections_response.data or [])]
        except Exception as table_error:
            # If table doesn't exist yet (migration not run), return empty list
            print(f"OneDrive connections table not found (migration may not be run): {str(table_error)}")
            connections = []

        return jsonify({'connections': connections}), 200

    except Exception as e:
        print(f"Error listing OneDrive connections: {str(e)}")
        # Return empty list instead of error if it's just a missing table
        if 'relation "onedrive_connections" does not exist' in str(e).lower():
            print("OneDrive connections table doesn't exist - migration not run yet")
            return jsonify({'connections': []}), 200
        return jsonify({'error': str(e)}), 500


@checker_bp.route('/onedrive/connections', methods=['POST'])
def create_onedrive_connection():
    """Create a new OneDrive connection"""
    try:
        context, error = request_context('super_admin')
        if error:
            return error
        payload = request.get_json() or {}

        account_name = (payload.get('account_name') or '').strip()
        account_email = (payload.get('account_email') or '').strip()
        refresh_token = (payload.get('refresh_token') or '').strip()
        base_folder_path = (payload.get('base_folder_path') or '/').strip()

        if not account_name:
            return jsonify({'error': 'Account name is required'}), 400
        if len(account_name) > 100:
            return jsonify({'error': 'Account name must be 100 characters or fewer'}), 400
        if not account_email:
            return jsonify({'error': 'Microsoft account email is required. Please reconnect the account.'}), 400
        if not refresh_token:
            return jsonify({'error': 'Refresh token is required'}), 400

        connection_data = {
            'tenant_id': context.tenant_id,
            'account_name': account_name,
            'account_email': account_email,
            'refresh_token': refresh_token,
            'base_folder_path': base_folder_path,
            'connected_by': context.user_id,
            'updated_at': datetime.utcnow().isoformat()
        }
        response = supabase_admin.table('tenant_onedrive_connections').upsert(connection_data).execute()
        result = response.data[0] if response.data else connection_data
        result = {**result, 'id': context.tenant_id, 'is_active': True}
        result.pop('refresh_token', None)
        return jsonify(result), 201

    except Exception as e:
        print(f"Error creating OneDrive connection: {str(e)}")
        return jsonify({'error': str(e)}), 500


@checker_bp.route('/onedrive/connections/<connection_id>', methods=['PUT'])
def update_onedrive_connection(connection_id):
    """Update an OneDrive connection (name, email, base path)"""
    try:
        context, error = request_context('super_admin')
        if error:
            return error
        payload = request.get_json() or {}
        updates = {}

        if 'account_name' in payload:
            account_name = (payload['account_name'] or '').strip()
            if not account_name:
                return jsonify({'error': 'Account name is required'}), 400
            if len(account_name) > 100:
                return jsonify({'error': 'Account name must be 100 characters or fewer'}), 400
            updates['account_name'] = account_name

        if 'account_email' in payload:
            updates['account_email'] = (payload['account_email'] or '').strip()

        if 'base_folder_path' in payload:
            base_path = (payload['base_folder_path'] or '/').strip()
            if not base_path.startswith('/'):
                return jsonify({'error': 'Base folder path must start with /'}), 400
            updates['base_folder_path'] = base_path

        if not updates:
            return jsonify({'error': 'No valid fields to update'}), 400

        updates['updated_at'] = datetime.utcnow().isoformat()

        response = supabase_admin.table('tenant_onedrive_connections') \
            .update(updates) \
            .eq('tenant_id', context.tenant_id) \
            .execute()

        if not response.data:
            return jsonify({'error': 'Connection not found or access denied'}), 404

        return jsonify(response.data[0]), 200

    except Exception as e:
        print(f"Error updating OneDrive connection: {str(e)}")
        return jsonify({'error': str(e)}), 500


@checker_bp.route('/onedrive/connections/<connection_id>/activate', methods=['PUT'])
def activate_onedrive_connection(connection_id):
    """Set a connection as the active one (deactivates all others)"""
    try:
        context, error = request_context('super_admin')
        if error:
            return error
        connection_check = supabase_admin.table('tenant_onedrive_connections') \
            .select('tenant_id').eq('tenant_id', context.tenant_id).execute()

        if not connection_check.data:
            return jsonify({'error': 'Connection not found or access denied'}), 404

        return jsonify({'id': context.tenant_id, 'tenant_id': context.tenant_id, 'is_active': True}), 200

    except Exception as e:
        print(f"Error activating OneDrive connection: {str(e)}")
        return jsonify({'error': str(e)}), 500


@checker_bp.route('/onedrive/connections/<connection_id>', methods=['DELETE'])
def delete_onedrive_connection(connection_id):
    """Delete an OneDrive connection"""
    try:
        context, error = request_context('super_admin')
        if error:
            return error
        connection_check = supabase_admin.table('tenant_onedrive_connections') \
            .select('tenant_id').eq('tenant_id', context.tenant_id).single().execute()

        if not connection_check.data:
            return jsonify({'error': 'Connection not found or access denied'}), 404

        supabase_admin.table('tenant_onedrive_connections').delete() \
            .eq('tenant_id', context.tenant_id).execute()

        return jsonify({'success': True}), 200

    except Exception as e:
        print(f"Error deleting OneDrive connection: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ==================== END ONEDRIVE CONNECTIONS MANAGEMENT ====================


@checker_bp.route('/agents/<agent_id>/run-check', methods=['POST'])
def run_check(agent_id):
    """
    Execute a task check for an agent

    Expected Authorization header: Bearer <supabase_access_token>
    Expected JSON body: {
        "task_folder": "/Documents/Tasks/Invoice Processing"
    }

    Client folder and KB selections are configured on the agent.

    Returns:
        JSON response with check results
    """
    if os.getenv('TASKCHECKER_VALIDATOR', 'codex').lower() == 'codex':
        from api.codex_runs import enqueue_codex_check
        return enqueue_codex_check(agent_id)

    # Operator-only rollback path. There is deliberately no automatic fallback.
    check_run_id = None
    client_temp_dir = None
    task_temp_dir = None
    kb_temp_dir = None

    try:
        # Verify authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized - Missing or invalid Authorization header'}), 401

        token = auth_header.replace('Bearer ', '')

        # Get folder paths from request body
        data = request.get_json() or {}
        task_folder = (data.get('task_folder') or '').strip()

        # Get user from token
        try:
            user_response = supabase_admin.auth.get_user(token)
            if not user_response or not user_response.user:
                return jsonify({'error': 'Invalid authentication token'}), 401
            user_id = user_response.user.id
        except Exception as e:
            return jsonify({'error': f'Authentication failed: {str(e)}'}), 401

        print(f"✅ Authenticated user: {user_id}")

        # Get agent details
        agent_response = supabase_admin.table('agents').select('*').eq('id', agent_id).eq('user_id', user_id).single().execute()

        if not agent_response.data:
            return jsonify({'error': 'Agent not found or access denied'}), 404

        agent = agent_response.data
        print(f"✅ Found agent: {agent['name']}")

        if not task_folder:
            # Prefer the explicitly SELECTED task subfolder(s) over the parent root,
            # so unchecked sibling folders (e.g. a different task) are never ingested.
            selected = agent.get('task_file_paths') or []
            if isinstance(selected, list) and selected:
                task_folder = str(selected[0] or '').strip()
                if len(selected) > 1:
                    print(f"⚠️ Multiple task folders selected; using the first: {task_folder}")
            if not task_folder:
                task_folder = (agent.get('onedrive_folder_path') or '').strip()

        if not task_folder:
            return jsonify({'error': 'task_folder is required in request body or agent configuration'}), 400

        print(f"📁 Task folder: {task_folder}")

        agent_kb_folders = normalize_path_list(agent.get('kb_folder_paths'))
        agent_kb_files = normalize_path_list(agent.get('kb_file_paths'))
        kb_files = merge_unique(agent_kb_files)
        kb_folders = merge_unique(agent_kb_folders)

        client_folder = (agent.get('client_folder_path') or '').strip()
        if not client_folder:
            print("ℹ️ No client folder configured for this agent; skipping client context.")
        else:
            print(f"📁 Client folder: {client_folder}")

        # Create check run record
        initial_status = 'QUEUED' if ENABLE_ASYNC_CHECKS else 'RUNNING'
        check_run_response = supabase_admin.table('check_runs').insert({
            'agent_id': agent_id,
            'status': initial_status,
            'result_summary': 'Check queued...' if ENABLE_ASYNC_CHECKS else 'Check in progress...'
        }).execute()

        check_run_id = check_run_response.data[0]['id']
        print(f"✅ Created check run: {check_run_id}")

        if ENABLE_ASYNC_CHECKS:
            task_payload = {
                'agent_id': agent_id,
                'user_id': user_id,
                'task_folder': task_folder
            }
            task_response = supabase_admin.table('check_run_tasks').insert({
                'check_run_id': check_run_id,
                'stage': 'execute_check',
                'status': 'PENDING',
                'payload': task_payload
            }).execute()

            task_id = task_response.data[0]['id'] if task_response.data else None
            return jsonify({
                'success': True,
                'check_run_id': check_run_id,
                'task_id': task_id,
                'status': 'QUEUED',
                'summary': 'Check queued for processing.'
            }), 202

        start_time = time.time()

        # Get user's OneDrive refresh token (prefer active connection, fallback to legacy profile token)
        refresh_token = None
        try:
            connection_response = supabase_admin.table('onedrive_connections') \
                .select('refresh_token') \
                .eq('user_id', user_id) \
                .eq('is_active', True) \
                .limit(1) \
                .execute()
            if connection_response.data:
                refresh_token = connection_response.data[0].get('refresh_token')
            if not refresh_token:
                fallback_response = supabase_admin.table('onedrive_connections') \
                    .select('refresh_token') \
                    .eq('user_id', user_id) \
                    .order('created_at', desc=True) \
                    .limit(1) \
                    .execute()
                if fallback_response.data:
                    refresh_token = fallback_response.data[0].get('refresh_token')
        except Exception:
            refresh_token = None

        if not refresh_token:
            profile_response = supabase_admin.table('profiles') \
                .select('onedrive_refresh_token') \
                .eq('id', user_id) \
                .single() \
                .execute()
            if not profile_response.data:
                raise Exception('User profile not found')
            refresh_token = profile_response.data.get('onedrive_refresh_token')

        if not refresh_token:
            raise Exception('OneDrive not connected. Please connect your OneDrive account first.')

        print("✅ Got OneDrive refresh token")

        # Get fresh access token
        access_token = get_user_onedrive_token(refresh_token)
        print("✅ Got fresh OneDrive access token")

        # ========== SECTIONS 2-7 PIPELINE ==========
        # NEW ARCHITECTURE: Run ingestion, normalization, workflow reconstruction, client context, and rule engine
        import sys
        logger.info("="*80)
        logger.info("🚀🚀🚀 ABOUT TO START SECTIONS 2-7 PIPELINE 🚀🚀🚀")
        logger.info(f"Task Folder: {task_folder}")
        logger.info(f"Client Folder: {client_folder}")
        logger.info(f"KB Folders: {kb_folders}")
        logger.info(f"KB Files: {kb_files}")
        logger.info("="*80)

        print("\n" + "🚀" * 30, flush=True)
        print("EXECUTING SECTIONS 2-7 PIPELINE (NEW ARCHITECTURE)", flush=True)
        print("🚀" * 30 + "\n", flush=True)
        sys.stdout.flush()

        from services.section_pipeline import run_section_pipeline

        # The agent's name/description/specialization prompt drive the generic
        # criteria engine ("what should be checked"). No task type is selected by
        # the user; the pipeline auto-detects any specialization.
        task_description = "\n".join(
            part for part in [
                (agent.get('name') or '').strip(),
                (agent.get('description') or '').strip(),
                (agent.get('system_prompt') or '').strip(),
            ] if part
        )

        # Example input/output reference files are a strong "what good looks like"
        # signal for criteria derivation. Download + extract their text (best effort).
        reference_texts = []
        try:
            from services.reference_files import gather_reference_texts
            reference_texts = gather_reference_texts(access_token, agent.get('reference_file_paths'))
            if reference_texts:
                print(f"📎 Loaded {len(reference_texts)} reference example file(s)")
        except Exception as e:
            logger.warning(f"Failed to gather reference files: {e}")

        try:
            logger.info("Calling run_section_pipeline()...")
            pipeline_result = run_section_pipeline(
                user_id=user_id,
                agent_id=agent_id,
                access_token=access_token,
                task_folder=task_folder,
                client_folder=client_folder if client_folder else None,
                kb_folders=kb_folders if kb_folders else None,
                kb_files=kb_files if kb_files else None,
                task_description=task_description,
                reference_texts=reference_texts if reference_texts else None
            )

            # Extract results from pipeline
            section2_manifest = pipeline_result['section2_manifest']
            section3_normalized = pipeline_result['section3_normalized']
            section4_workflow = pipeline_result['section4_workflow']
            section5_context = pipeline_result['section5_context']

            # Set work directory for later use
            task_temp_dir = pipeline_result['work_dir']
            kb_temp_dir = pipeline_result.get('kb_work_dir')
            client_temp_dir = os.path.join(task_temp_dir, 'client_context') if client_folder else None

            print(f"\n✅ Sections 2-7 pipeline complete in {pipeline_result['execution_time_seconds']:.1f}s")

        except Exception as e:
            print(f"\n❌ SECTIONS 2-7 PIPELINE FAILED: {e}")
            print("=" * 60)
            print("NO FALLBACK ENABLED - Check cannot proceed without Sections 2-7")
            print("=" * 60)
            import traceback
            traceback.print_exc()
            raise Exception(f"Sections 2-7 pipeline failed: {str(e)}") from e

        # ========== END SECTIONS 2-7 PIPELINE ==========

        # ========== BUILD RESPONSE WITH SECTIONS 2-7 DATA ==========
        print("\n" + "=" * 60)
        print("📦 BUILDING RESPONSE FROM SECTIONS 2-7")
        print("=" * 60)

        execution_time = time.time() - start_time

        mode = pipeline_result.get('mode', 'specialization')
        specialization = pipeline_result.get('specialization')

        # Extract Section 6/7 (specialization) and generic results from pipeline
        section6_rules = pipeline_result.get('section6_rules')
        section7_validation = pipeline_result.get('section7_validation')
        generic_validation = pipeline_result.get('generic_validation')
        check_spec = pipeline_result.get('check_spec')

        # Determine overall status + summary based on the path that ran
        overall_status = 'PASS'
        summary = 'Check completed'

        if mode == 'generic':
            gv_summary = (generic_validation or {}).get('summary', {})
            overall_status = gv_summary.get('overall_status', 'INDETERMINATE')
            summary = (
                f"{gv_summary.get('passed', 0)} passed / {gv_summary.get('failed', 0)} failed / "
                f"{gv_summary.get('unclear', 0)} unclear of {gv_summary.get('total', 0)} criteria"
            )
        else:
            if section7_validation:
                overall_status = section7_validation.get('summary', {}).get('overall_status', 'UNKNOWN')
                s = section7_validation.get('summary', {})
                summary = f"AI Validation: {s.get('passed_steps', 0)}/{s.get('total_steps', 0)} steps passed"
            elif section6_rules:
                if section6_rules.failed_count > 0:
                    overall_status = 'FAIL'
                elif section6_rules.indeterminate_count > 0 and section6_rules.passed_count == 0:
                    overall_status = 'INDETERMINATE'
                summary = f"Validation: {section6_rules.passed_count}/{section6_rules.total_rules_evaluated} rules passed"

        # Build sections metadata
        section2_manifest = pipeline_result.get('section2_manifest')
        section3_normalized = pipeline_result.get('section3_normalized')
        section4_workflow = pipeline_result.get('section4_workflow')
        section5_context = pipeline_result.get('section5_context')

        sections_metadata = {
            'section2': {
                'total_files': len(section2_manifest.get('file_inventory', [])),
                'workflow_files': len(section2_manifest.get('workflow_files', [])),
                'inputs_count': len(section2_manifest.get('role_index', {}).get('INPUTS', [])),
                'outputs_count': len(section2_manifest.get('role_index', {}).get('OUTPUTS', [])),
                'client_context_count': len(section2_manifest.get('client_context_files', [])),
                'kb_count': len(section2_manifest.get('knowledge_base_files', []))
            } if section2_manifest else {},
            'section3': {
                'normalized_inputs': len(section3_normalized.get('normalized_inputs', [])),
                'normalized_outputs': len(section3_normalized.get('normalized_outputs', [])),
                'ambiguities_count': len(section3_normalized.get('ambiguities', []))
            } if section3_normalized else {},
            'section4': {
                'declared_workflows': len(section4_workflow.get('declared_workflows', [])),
                'execution_events': len(section4_workflow.get('execution_timeline', [])),
                'workflow_comparisons': len(section4_workflow.get('workflow_comparison', [])),
                'unmatched_steps': len(section4_workflow.get('unmatched_steps', []))
            } if section4_workflow else {},
            'section5': {
                'context_domains': list(section5_context.get('client_context_model', {}).keys()),
                'conflicts_count': len(section5_context.get('conflicts', [])),
                'context_warnings': section5_context.get('context_warnings', []),
                'context_confidence': section5_context.get('context_confidence', {})
            } if section5_context else {},
            'section6': {
                'total_rules_evaluated': section6_rules.total_rules_evaluated if section6_rules else 0,
                'passed_count': section6_rules.passed_count if section6_rules else 0,
                'failed_count': section6_rules.failed_count if section6_rules else 0,
                'indeterminate_count': section6_rules.indeterminate_count if section6_rules else 0,
                'unresolved_items': len(section6_rules.unresolved_items) if section6_rules else 0,
                'execution_time_ms': section6_rules.execution_time_ms if section6_rules else 0,
                'rule_results': [
                    {
                        'rule_id': r.rule_id,
                        'rule_name': r.rule_name,
                        'status': r.status.value,
                        'severity': r.severity.value,
                        'deviation': r.deviation
                    }
                    for r in section6_rules.rule_results
                ] if section6_rules else []
            } if section6_rules else {},
            'section7': {
                'total_steps': section7_validation.get('summary', {}).get('total_steps', 0) if section7_validation else 0,
                'passed_steps': section7_validation.get('summary', {}).get('passed_steps', 0) if section7_validation else 0,
                'failed_steps': section7_validation.get('summary', {}).get('failed_steps', 0) if section7_validation else 0,
                'overall_status': section7_validation.get('summary', {}).get('overall_status', 'UNKNOWN') if section7_validation else 'UNKNOWN',
                'ai_cost': section7_validation.get('metadata', {}).get('cost', 0) if section7_validation else 0,
                'input_tokens': section7_validation.get('metadata', {}).get('input_tokens', 0) if section7_validation else 0,
                'output_tokens': section7_validation.get('metadata', {}).get('output_tokens', 0) if section7_validation else 0,
                'validations': section7_validation.get('validations', []) if section7_validation else [],
                'failed_validations': [
                    {
                        'step': v.get('step', 'Unknown'),
                        'status': v.get('status', 'UNKNOWN'),
                        'issues_count': len(v.get('issues', [])),
                        'issues': v.get('issues', [])[:3]  # First 3 issues only
                    }
                    for v in section7_validation.get('validations', []) if v.get('status') == 'FAIL'
                ] if section7_validation else []
            } if section7_validation else {},
            'mode': mode,
            'specialization': specialization,
            'generic': {
                'task_summary': (generic_validation or {}).get('task_summary', '') if generic_validation else (check_spec or {}).get('task_summary', ''),
                'check_spec': check_spec or {},
                'criteria_results': (generic_validation or {}).get('criteria_results', []) if generic_validation else [],
                'summary': (generic_validation or {}).get('summary', {}) if generic_validation else {},
                'metadata': (generic_validation or {}).get('metadata', {}) if generic_validation else {},
                'cost': pipeline_result.get('cost', {}),
                'error': pipeline_result.get('generic_error'),
            } if mode == 'generic' else {}
        }

        print("✅ Response built successfully")
        print(f"   - Status: {overall_status}")
        print(f"   - Execution time: {execution_time:.1f}s")
        print(f"   - Sections included: {list(sections_metadata.keys())}")

        # Update check run in database
        # Map INDETERMINATE to ERROR for database (constraint only allows PASS/FAIL/ERROR)
        db_status = 'ERROR' if overall_status == 'INDETERMINATE' else overall_status
        try:
            supabase_admin.table('check_runs').update({
                'status': db_status,
                'execution_time_seconds': execution_time
            }).eq('id', check_run_id).execute()
        except Exception as e:
            logger.warning(f"Failed to update check_run: {e}")

        # Cleanup temp files
        for temp_directory in [task_temp_dir, kb_temp_dir, client_temp_dir]:
            if temp_directory and os.path.exists(temp_directory):
                shutil.rmtree(temp_directory, ignore_errors=True)
        print("✅ Cleaned up temp files")

        # Return response with ONLY Sections 2-7 data
        return jsonify({
            'success': True,
            'check_run_id': check_run_id,
            'status': overall_status,
            'summary': summary,
            'execution_time': execution_time,

            # SECTIONS 2-7: New Architecture Pipeline Data (ONLY data source)
            'sections_2_7': sections_metadata
        }), 200

    except Exception as e:
        error_message = str(e)
        print(f"\n{'='*60}")
        print("❌ FATAL ERROR in run_check:")
        print(f"   Error: {error_message}")
        print(f"   Type: {type(e).__name__}")
        print("   Traceback:")
        print(traceback.format_exc())
        print(f"{'='*60}\n")

        # Update check run with error if it was created
        if 'check_run_id' in locals():
            try:
                supabase_admin.table('check_runs').update({
                    'status': 'ERROR',
                    'error_message': error_message,
                    'execution_time_seconds': time.time() - start_time if 'start_time' in locals() else 0
                }).eq('id', check_run_id).execute()
            except Exception:
                pass

        # Cleanup temp files
        for temp_var in ['client_temp_dir', 'task_temp_dir', 'kb_temp_dir']:
            if temp_var in locals():
                temp_directory = locals()[temp_var]
                if temp_directory and os.path.exists(temp_directory):
                    shutil.rmtree(temp_directory, ignore_errors=True)

        return jsonify({
            'success': False,
            'error': error_message
        }), 500

