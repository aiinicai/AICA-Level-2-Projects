import json
import logging
import dataclasses
from pathlib import Path
from flask import current_app
from app.services.job_state_service import update_job_status, get_job
from app.services.extraction_service import get_extraction_result
from app.services.bank_detector import BankDetector
from app.services.statement_metadata_service import StatementMetadataService
from app.services.transaction_normalizer import TransactionNormalizer
from app.database.db import get_db_connection
from decimal import Decimal
import datetime

logger = logging.getLogger(__name__)

def run_normalization(job_id, config, force_profile_id=None):
    job = get_job(config, job_id)
    if not job:
        return False, "Job not found"
        
    extraction_result = get_extraction_result(job_id, config)
    if not extraction_result:
        return False, "Digital extraction artifact not found. Please run extraction first."
        
    try:
        # 1. Combine all raw text for bank detection & metadata
        full_text = " ".join([page['raw_text'] for page in extraction_result.get('pages', []) if page['raw_text']])
        
        # 2. Bank Detection
        detector = BankDetector()
        bank_status, bank_name, signatures = detector.detect_bank(full_text)
        
        # 3. Statement Metadata
        date_order = config.get('normalization', 'default_date_order', fallback='DMY')
        meta_service = StatementMetadataService()
        metadata = meta_service.extract_metadata(full_text, date_order)
        if bank_status == 'detected':
            metadata.bank_name = bank_name
        metadata.source_job_id = job_id
        
        # 4. Gather Table Candidates & Apply Profile
        from app.services.profile_manager import ProfileManager
        from app.services.profile_matcher import ProfileMatcher
        from app.extractors.coordinate_extractor import CoordinateExtractor
        from app.models.extraction_result import ExtractionResult
        
        prof_manager = ProfileManager(config)
        matcher = ProfileMatcher(prof_manager.list_profiles(), config)
        
        page_width = 0.0
        page_height = 0.0
        if extraction_result.get('pages'):
            page_width = extraction_result['pages'][0].get('width', 0.0)
            page_height = extraction_result['pages'][0].get('height', 0.0)
            
        match_status, matched_profile, match_score, match_details = 'NO_PROFILES_AVAILABLE', None, 0, {}
        if force_profile_id:
            matched_profile = prof_manager.get_profile(force_profile_id)
            if matched_profile:
                match_status = 'MANUAL'
                match_score = 100
                match_details = {'forced': True}
        else:
            match_status, matched_profile, match_score, match_details = matcher.match(
                bank_detected=bank_name if bank_status == 'detected' else "",
                page_width=page_width,
                page_height=page_height,
                extracted_text=full_text
            )
        
        table_candidates = []
        applied_profile_id = None
        
        if match_status in ['AUTO_APPLIED', 'MANUAL'] and matched_profile:
            # Reconstruct ExtractionResult to use CoordinateExtractor
            # Actually ExtractionResult needs a custom from_dict for deep conversion, 
            # let's just do it directly here or write a tiny helper
            er = ExtractionResult(**{k: v for k, v in extraction_result.items() if k != 'pages'})
            from app.models.extraction_result import RawPage, RawWord, RawTableCandidate
            er.pages = []
            for p in extraction_result.get('pages', []):
                rp = RawPage(**{k: v for k, v in p.items() if k not in ['words', 'table_candidates']})
                rp.words = [RawWord(**w) for w in p.get('words', [])]
                rp.table_candidates = [RawTableCandidate(**tc) for tc in p.get('table_candidates', [])]
                er.pages.append(rp)
                
            coord_extractor = CoordinateExtractor(matched_profile)
            er = coord_extractor.extract(er)
            
            for page in er.pages:
                table_candidates.extend([tc.to_dict() if hasattr(tc, 'to_dict') else dataclasses.asdict(tc) for tc in page.table_candidates])
            
            applied_profile_id = matched_profile.profile_id
        else:
            # Fallback to heuristic tables
            for page in extraction_result.get('pages', []):
                table_candidates.extend(page.get('table_candidates', []))
            
        # 5. Normalize Transactions
        normalizer = TransactionNormalizer(default_date_order=date_order)
        transactions, norm_warnings = normalizer.normalize(table_candidates)
        
        # 6. Save Artifact
        temp_dir = Path(config.get('paths', 'temp', fallback='temp'))
        project_root = Path(__file__).resolve().parent.parent.parent
        job_dir = project_root / temp_dir / 'jobs' / job_id
        norm_dir = job_dir / 'normalization'
        norm_dir.mkdir(parents=True, exist_ok=True)
        
        artifact_path = norm_dir / 'normalized_statement.json'
        
        artifact_data = {
            'bank_detection': {
                'status': bank_status,
                'bank_name': bank_name,
                'signatures': signatures
            },
            'metadata': dataclasses.asdict(metadata),
            'profile_application': {
                'status': match_status,
                'profile_id': applied_profile_id,
                'profile_name': matched_profile.profile_name if matched_profile else None,
                'match_score': match_score,
                # Include candidates list when available (suggestion or ambiguous)
                'candidates': match_details.get('candidates', [])
            },
            'warnings': norm_warnings,
            'transactions': [txn.to_dict() for txn in transactions],
            'pages_processed': len(set(txn.source_page for txn in transactions if txn.source_page)),
            'page_count': extraction_result.get('page_count', 1)
        }
        
        with open(artifact_path, 'w', encoding='utf-8') as f:
            json.dump(artifact_data, f, ensure_ascii=False)
            
        # Invalidate stale review artifacts on re-normalization
        review_dir = job_dir / 'review'
        rev_path = review_dir / 'reviewed_statement.json'
        if rev_path.exists():
            try:
                rev_path.unlink()
            except Exception as e:
                logger.warning(f"Could not remove stale reviewed statement for {job_id}: {e}")
        rev_val_path = review_dir / 'reviewed_validation.json'
        if rev_val_path.exists():
            try:
                rev_val_path.unlink()
            except Exception as e:
                logger.warning(f"Could not remove stale reviewed validation for {job_id}: {e}")

        # 7. Update Database Metadata
        # We don't save full transactions or account numbers in SQLite
        total_tx_warnings = sum(1 for t in transactions if t.normalization_warnings) + len(norm_warnings)
        with get_db_connection(config) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE processing_jobs 
                SET bank_detected = ?,
                    bank_detection_status = ?,
                    normalization_status = ?,
                    transaction_count = ?,
                    normalization_warning_count = ?,
                    profile_id = ?,
                    profile_revision = ?,
                    profile_match_score = ?,
                    profile_application_status = ?,
                    review_status = 'UNREVIEWED',
                    status = 'normalized',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                bank_name if bank_status == 'detected' else None,
                bank_status,
                'success' if total_tx_warnings == 0 else 'warning',
                len(transactions),
                total_tx_warnings,
                applied_profile_id,
                matched_profile.revision_number if matched_profile else None,
                match_score,
                match_status,
                job_id
            ))
            
        # 8. Automatically run Validation Service
        from app.services.validation_service import ValidationService
        val_service = ValidationService(config)
        val_service.validate_job(job_id)
            
        return True, None
        
    except Exception as e:
        logger.error(f"Normalization failed for job {job_id}: {e}", exc_info=True)
        return False, str(e)

def get_normalization_result(job_id, config):
    temp_dir = Path(config.get('paths', 'temp', fallback='temp'))
    project_root = Path(__file__).resolve().parent.parent.parent
    artifact_path = project_root / temp_dir / 'jobs' / job_id / 'normalization' / 'normalized_statement.json'
    
    if artifact_path.exists():
        try:
            with open(artifact_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read normalization result for {job_id}: {e}")
    return None
