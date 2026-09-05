"""
Human Review API (Week 4)

Endpoints for human review queue and conflict resolution.

Routes:
- GET  /api/human-review/queue - List pending reviews
- GET  /api/human-review/<review_id> - Get review details
- POST /api/human-review/<review_id>/resolve - Submit resolution
- GET  /api/human-review/history - Past resolutions
- POST /api/human-review/<review_id>/assign - Assign review to user
"""

import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request

from supabase_config import supabase_admin
from api.auth import request_context

human_review_bp = Blueprint('human_review', __name__)


@human_review_bp.route('/human-review/queue', methods=['GET'])
def get_review_queue():
    """
    Get list of pending human reviews.

    Query params:
    - status: Filter by status (pending, in_progress, resolved)
    - assigned_to: Filter by assignee user_id
    - limit: Max results (default: 50)
    """
    context, error_response = request_context('super_admin')
    if error_response:
        return error_response

    # Parse query params
    status = request.args.get('status', 'pending')
    assigned_to = request.args.get('assigned_to')
    limit = int(request.args.get('limit', 50))

    try:
        # Build query
        query = supabase_admin.table('human_reviews') \
            .select('*') \
            .eq('tenant_id', context.tenant_id) \
            .eq('status', status) \
            .order('created_at', desc=True) \
            .limit(limit)

        if assigned_to:
            query = query.eq('assigned_to', assigned_to)

        result = query.execute()

        reviews = result.data if result.data else []

        return jsonify({
            'reviews': reviews,
            'total': len(reviews),
            'status': status
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch review queue: {str(e)}'}), 500


@human_review_bp.route('/human-review/<review_id>', methods=['GET'])
def get_review_details(review_id):
    """Get detailed information about a specific review"""
    context, error_response = request_context('super_admin')
    if error_response:
        return error_response

    try:
        # Fetch review
        result = supabase_admin.table('human_reviews') \
            .select('*') \
            .eq('id', review_id) \
            .eq('tenant_id', context.tenant_id) \
            .single() \
            .execute()

        if not result.data:
            return jsonify({'error': 'Review not found'}), 404

        review = result.data

        # Fetch associated check run
        check_result = supabase_admin.table('check_runs') \
            .select('*') \
            .eq('id', review['check_run_id']) \
            .eq('tenant_id', context.tenant_id) \
            .single() \
            .execute()

        check_run = check_result.data if check_result.data else None

        # Fetch model consensus results
        consensus_result = supabase_admin.table('model_consensus_results') \
            .select('*') \
            .eq('check_run_id', review['check_run_id']) \
            .single() \
            .execute()

        consensus = consensus_result.data if consensus_result.data else None

        return jsonify({
            'review': review,
            'check_run': check_run,
            'consensus': consensus
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch review details: {str(e)}'}), 500


@human_review_bp.route('/human-review/<review_id>/resolve', methods=['POST'])
def resolve_review(review_id):
    """
    Submit resolution for a review.

    Body:
    {
        "verdict": "PASS" | "FAIL",
        "reasoning": "Explanation of decision",
        "correct_model": "gpt-4" | "claude" | "gemini" (optional),
        "feedback": "Feedback to improve AI models" (optional)
    }
    """
    context, error_response = request_context('super_admin')
    if error_response:
        return error_response
    user_id = context.user_id

    data = request.get_json()
    verdict = data.get('verdict')
    reasoning = data.get('reasoning')
    correct_model = data.get('correct_model')
    feedback = data.get('feedback')

    if not verdict or verdict not in ['PASS', 'FAIL']:
        return jsonify({'error': 'Invalid verdict (must be PASS or FAIL)'}), 400

    if not reasoning:
        return jsonify({'error': 'Reasoning is required'}), 400

    try:
        # Fetch review to verify it exists and is pending
        result = supabase_admin.table('human_reviews') \
            .select('*') \
            .eq('id', review_id) \
            .eq('tenant_id', context.tenant_id) \
            .single() \
            .execute()

        if not result.data:
            return jsonify({'error': 'Review not found'}), 404

        review = result.data

        if review['status'] == 'resolved':
            return jsonify({'error': 'Review already resolved'}), 400

        # Update review with resolution
        resolution = {
            'verdict': verdict,
            'reasoning': reasoning,
            'correct_model': correct_model,
            'resolved_by_user_id': user_id,
            'resolved_at': datetime.now().isoformat()
        }

        supabase_admin.table('human_reviews') \
            .update({
                'status': 'resolved',
                'resolved_by': user_id,
                'resolution': resolution,
                'resolution_reasoning': reasoning,
                'feedback_to_ai': feedback,
                'final_verdict': verdict,
                'resolved_at': datetime.now().isoformat()
            }) \
            .eq('id', review_id) \
            .eq('tenant_id', context.tenant_id) \
            .execute()

        # Store feedback for learning (if provided)
        if feedback and correct_model:
            supabase_admin.table('human_resolution_feedback').insert({
                'id': str(uuid.uuid4()),
                'review_id': review_id,
                'correct_model': correct_model,
                'correction_type': 'verdict_correction',
                'learning_notes': feedback,
                'applied_to_future_checks': True,
                'created_at': datetime.now().isoformat()
            }).execute()

        # Update associated check run with resolution
        if review['check_run_id']:
            supabase_admin.table('check_runs') \
                .update({
                    'status': verdict,
                    'final_verdict': verdict,
                    'review_status': 'RESOLVED',
                    'human_review_resolution': resolution,
                    'updated_at': datetime.now().isoformat()
                }) \
                .eq('id', review['check_run_id']) \
                .eq('tenant_id', context.tenant_id) \
                .execute()

        return jsonify({
            'message': 'Review resolved successfully',
            'resolution': resolution
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to resolve review: {str(e)}'}), 500


@human_review_bp.route('/human-review/history', methods=['GET'])
def get_resolution_history():
    """
    Get history of resolved reviews.

    Query params:
    - resolved_by: Filter by resolver user_id
    - limit: Max results (default: 50)
    - offset: Pagination offset (default: 0)
    """
    context, error_response = request_context('super_admin')
    if error_response:
        return error_response

    resolved_by = request.args.get('resolved_by')
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))

    try:
        # Build query
        query = supabase_admin.table('human_reviews') \
            .select('*') \
            .eq('tenant_id', context.tenant_id) \
            .eq('status', 'resolved') \
            .order('resolved_at', desc=True) \
            .range(offset, offset + limit - 1)

        if resolved_by:
            query = query.eq('resolved_by', resolved_by)

        result = query.execute()

        reviews = result.data if result.data else []

        return jsonify({
            'reviews': reviews,
            'total': len(reviews),
            'limit': limit,
            'offset': offset
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch resolution history: {str(e)}'}), 500


@human_review_bp.route('/human-review/<review_id>/assign', methods=['POST'])
def assign_review(review_id):
    """
    Assign a review to a user.

    Body:
    {
        "assigned_to": "user_id" | null (to unassign)
    }
    """
    context, error_response = request_context('super_admin')
    if error_response:
        return error_response

    data = request.get_json()
    assigned_to = data.get('assigned_to')

    try:
        # Update assignment
        update_data = {
            'assigned_to': assigned_to,
            'updated_at': datetime.now().isoformat()
        }

        if assigned_to:
            update_data['status'] = 'in_progress'
        else:
            # Unassigning - set back to pending
            update_data['status'] = 'pending'

        result = supabase_admin.table('human_reviews') \
            .update(update_data) \
            .eq('id', review_id) \
            .eq('tenant_id', context.tenant_id) \
            .execute()

        if not result.data:
            return jsonify({'error': 'Review not found'}), 404

        return jsonify({
            'message': 'Review assigned successfully',
            'review': result.data[0]
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to assign review: {str(e)}'}), 500


@human_review_bp.route('/human-review/stats', methods=['GET'])
def get_review_stats():
    """Get statistics about human reviews"""
    context, error_response = request_context('super_admin')
    if error_response:
        return error_response

    try:
        # Count by status
        pending_result = supabase_admin.table('human_reviews') \
            .select('id', count='exact') \
            .eq('tenant_id', context.tenant_id) \
            .eq('status', 'pending') \
            .execute()

        in_progress_result = supabase_admin.table('human_reviews') \
            .select('id', count='exact') \
            .eq('tenant_id', context.tenant_id) \
            .eq('status', 'in_progress') \
            .execute()

        resolved_result = supabase_admin.table('human_reviews') \
            .select('id', count='exact') \
            .eq('tenant_id', context.tenant_id) \
            .eq('status', 'resolved') \
            .execute()

        stats = {
            'pending': pending_result.count if hasattr(pending_result, 'count') else 0,
            'in_progress': in_progress_result.count if hasattr(in_progress_result, 'count') else 0,
            'resolved': resolved_result.count if hasattr(resolved_result, 'count') else 0,
            'total': 0
        }

        stats['total'] = stats['pending'] + stats['in_progress'] + stats['resolved']

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch review stats: {str(e)}'}), 500
