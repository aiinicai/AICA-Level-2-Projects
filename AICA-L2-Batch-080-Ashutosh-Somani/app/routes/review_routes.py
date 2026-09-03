from flask import Blueprint, request, jsonify, current_app, render_template
import logging
from app.services.review_service import ReviewService
from app.services.audit_service import AuditService
from app.services.correction_service import CorrectionService
from app.services.profile_suggestion_service import ProfileSuggestionService
from app.services.extraction_service import get_extraction_result

review_bp = Blueprint('review', __name__, url_prefix='/review')
logger = logging.getLogger(__name__)

def _get_services():
    config = current_app.config['APP_CONFIG']
    audit_svc = AuditService(config)
    review_svc = ReviewService(config)
    profile_sugg_svc = ProfileSuggestionService(config)
    correction_svc = CorrectionService(review_svc, audit_svc, profile_sugg_svc)
    return config, review_svc, audit_svc, correction_svc, profile_sugg_svc

@review_bp.route('/<job_id>')
def review_page(job_id):
    """
    Renders the Advanced Review UI for a given job.
    """
    config, review_svc, audit_svc, correction_svc, profile_sugg_svc = _get_services()
    
    # Initialize if missing
    try:
        review_svc.initialize_review(job_id)
    except FileNotFoundError:
        return jsonify({"status": "error", "message": "Normalization artifact missing. Run analysis first."}), 404
        
    return render_template('review.html', job_id=job_id)

@review_bp.route('/api/<job_id>/data', methods=['GET'])
def get_review_data(job_id):
    try:
        config, review_svc, audit_svc, correction_svc, profile_sugg_svc = _get_services()
        
        statement = review_svc.load_reviewed_statement(job_id)
        val_result = review_svc.load_reviewed_validation(job_id)
        suggestions = profile_sugg_svc.get_suggestions(job_id)
        
        return jsonify({
            "status": "success",
            "review_revision": statement.review_revision,
            "review_status": statement.review_status.value,
            "transactions": [t.to_dict() for t in statement.transactions],
            "validation": val_result,
            "suggestions": suggestions
        })
    except Exception as e:
        logger.error(f"Error loading review data: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@review_bp.route('/api/<job_id>/audit', methods=['GET'])
def get_audit_trail(job_id):
    try:
        config, review_svc, audit_svc, _, _ = _get_services()
        events = audit_svc.get_events(job_id)
        return jsonify({
            "status": "success",
            "events": [e.to_dict() for e in events]
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@review_bp.route('/api/<job_id>/edit', methods=['POST'])
def edit_transaction(job_id):
    try:
        config, review_svc, audit_svc, correction_svc, _ = _get_services()
        data = request.json
        
        expected_rev = data.get("expected_revision")
        tx_id = data.get("transaction_id")
        updates = data.get("updates", {})
        reason = data.get("reason")
        
        statement = correction_svc.apply_edit(job_id, expected_rev, tx_id, updates, reason)
        
        return jsonify({
            "status": "success",
            "review_revision": statement.review_revision
        })
    except ValueError as e:
        if "REVIEW_REVISION_CONFLICT" in str(e):
            return jsonify({"status": "error", "code": "REVIEW_REVISION_CONFLICT", "message": "The data was updated in another session. Please refresh."}), 409
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Error applying edit: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Internal error"}), 500

@review_bp.route('/api/<job_id>/action', methods=['POST'])
def perform_action(job_id):
    try:
        config, review_svc, audit_svc, correction_svc, _ = _get_services()
        data = request.json
        
        expected_rev = data.get("expected_revision")
        action = data.get("action")
        
        if action == "MARK_NON_TRANSACTION":
            statement = correction_svc.mark_non_transaction(job_id, expected_rev, data["transaction_id"], data.get("reason"))
        elif action == "RESTORE_TRANSACTION":
            statement = correction_svc.restore_transaction(job_id, expected_rev, data["transaction_id"], data.get("reason"))
        elif action == "REVERT_CORRECTION":
            statement = correction_svc.revert_transaction(job_id, expected_rev, data["transaction_id"])
        elif action == "ROW_MERGE":
            statement = correction_svc.merge_rows(job_id, expected_rev, data["parent_ids"], data["merged_data"])
        elif action == "ROW_SPLIT":
            statement = correction_svc.split_row(job_id, expected_rev, data["parent_id"], data["child_data_list"])
        else:
            return jsonify({"status": "error", "message": "Unknown action"}), 400
            
        return jsonify({
            "status": "success",
            "review_revision": statement.review_revision
        })
    except ValueError as e:
        if "REVIEW_REVISION_CONFLICT" in str(e):
            return jsonify({"status": "error", "code": "REVIEW_REVISION_CONFLICT", "message": "Conflict. Please refresh."}), 409
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Error performing action: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Internal error"}), 500
