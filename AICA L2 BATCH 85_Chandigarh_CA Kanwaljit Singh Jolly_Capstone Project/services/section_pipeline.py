"""
Section Pipeline Orchestrator

Coordinates the execution of Sections 2-7 in sequence:
- Section 2: OneDrive Ingestion
- Section 3: Normalization
- Section 4: Workflow Reconstruction
- Section 5: Client Context Interpretation
- Section 6: Deterministic Rule Engine
- Section 7: AI Audit & Explanation Engine

Each section follows strict input/output contracts as defined in specification docs.
"""

import logging
import os
import sys
import time
from typing import Any, Dict, Optional

from services.section2_ingestion import Section2Ingestion
from services.section3_normalization import Section3Normalization
from services.section4_workflow import Section4Workflow
from services.section5_client_context import Section5ClientContext

# Configure logging for pipeline
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - PIPELINE - %(levelname)s - %(message)s',
    stream=sys.stdout
)


class SectionPipeline:
    """
    Orchestrates the full Sections 2-5 pipeline
    """

    def __init__(self, user_id: str, agent_id: str, access_token: str = None, file_source=None):
        """
        Initialize pipeline

        Args:
            user_id: User ID for temp directory naming
            agent_id: Agent ID for temp directory naming
            access_token: OneDrive access token (used to build an OneDriveSource if
                no explicit file_source is supplied)
            file_source: Optional FileSource (e.g. LocalDirSource) for offline runs/tests.
        """
        from services.file_source import OneDriveSource

        self.user_id = user_id
        self.agent_id = agent_id
        self.access_token = access_token
        if file_source is None:
            if not access_token:
                raise ValueError("SectionPipeline requires either access_token or file_source")
            file_source = OneDriveSource(access_token)
        self.file_source = file_source
        self.timestamp = int(time.time())

        # Create base work directory
        self.work_dir = f'/tmp/taskchecker_sections_{user_id}_{agent_id}_{self.timestamp}'
        os.makedirs(self.work_dir, exist_ok=True)

    def run(
        self,
        task_folder: str,
        task_id: str = "tds_26q",
        client_folder: Optional[str] = None,
        kb_folders: Optional[list] = None,
        kb_files: Optional[list] = None,
        task_description: str = "",
        reference_texts: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Execute the full Sections 2-5 pipeline

        Args:
            task_folder: OneDrive path to task folder (required)
            task_id: Task identifier for task pack (default: "tds_26q")
            client_folder: OneDrive path to client folder (optional)
            kb_folders: List of OneDrive paths to KB folders (optional)
            kb_files: List of OneDrive paths to KB files (optional)

        Returns:
            Dictionary with all section outputs:
            {
                'section2_manifest': {...},
                'section3_normalized': {...},
                'section4_workflow': {...},
                'section5_context': {...},
                'work_dir': '/tmp/...',
                'execution_time_seconds': 12.5
            }
        """
        start_time = time.time()
        pipeline_result = {
            'work_dir': self.work_dir,
            'execution_time_seconds': 0
        }

        try:
            # ========== SECTION 2: INGESTION ==========
            logger.info("="*80)
            logger.info("🚀 STARTING SECTIONS 2-7 PIPELINE EXECUTION")
            logger.info("="*80)
            print("\n" + "=" * 60, flush=True)
            print("SECTION 2 - ONEDRIVE INGESTION", flush=True)
            print("=" * 60, flush=True)
            sys.stdout.flush()

            section2 = Section2Ingestion(
                task_id=f"{self.agent_id}_{self.timestamp}",
                onedrive_root_path=task_folder,
                local_work_dir=self.work_dir,
                file_source=self.file_source
            )

            # Ingest task folder (required)
            print(f"📥 Ingesting task folder: {task_folder}")
            manifest = section2.ingest()
            print("[OK] Section 2 complete:")
            print(f"   - Total files: {len(manifest.get('file_inventory', []))}")
            print(f"   - Workflow files: {len(manifest.get('workflow_files', []))}")
            print(f"   - Input files: {len(manifest.get('role_index', {}).get('INPUTS', []))}")
            print(f"   - Output files: {len(manifest.get('role_index', {}).get('OUTPUTS', []))}")

            pipeline_result['section2_manifest'] = manifest

            # Ingest client folder (optional)
            if client_folder:
                print(f"\n📥 Ingesting client context folder: {client_folder}")
                client_section2 = Section2Ingestion(
                    task_id=f"{self.agent_id}_{self.timestamp}_client",
                    onedrive_root_path=client_folder,
                    local_work_dir=os.path.join(self.work_dir, 'client_context'),
                    file_source=self.file_source
                )
                client_manifest = client_section2.ingest()
                print(f"[OK] Client context ingested: {len(client_manifest.get('file_inventory', []))} files")
                pipeline_result['section2_client_manifest'] = client_manifest
            else:
                print("\nℹ️ No client folder configured, skipping client context ingestion")
                pipeline_result['section2_client_manifest'] = None

            # Ingest KB files (optional)
            if kb_folders or kb_files:
                print("\n📥 Ingesting KB files...")
                kb_work_dir = os.path.join(self.work_dir, 'kb_files')
                os.makedirs(kb_work_dir, exist_ok=True)

                # For KB files, we'll download them directly
                # (Section 2 is designed for folder ingestion, KB files are individual)
                from services.onedrive import download_onedrive_file, download_onedrive_folder
                kb_downloaded = []

                if kb_folders:
                    for kb_folder_path in kb_folders:
                        try:
                            kb_folder_name = os.path.basename(kb_folder_path) or "kb_folder"
                            kb_dest = os.path.join(kb_work_dir, kb_folder_name)
                            os.makedirs(kb_dest, exist_ok=True)
                            download_onedrive_folder(self.access_token, kb_folder_path, kb_dest)
                            kb_downloaded.append(kb_folder_path)
                            print(f"   [OK] Downloaded KB folder: {kb_folder_path}")
                        except Exception as e:
                            print(f"   [WARNING] Failed to download KB folder {kb_folder_path}: {e}")

                if kb_files:
                    kb_files_dir = os.path.join(kb_work_dir, "_individual_files")
                    os.makedirs(kb_files_dir, exist_ok=True)
                    for kb_file_path in kb_files:
                        try:
                            kb_filename = os.path.basename(kb_file_path)
                            kb_dest_path = os.path.join(kb_files_dir, kb_filename)
                            download_onedrive_file(self.access_token, kb_file_path, kb_dest_path)
                            kb_downloaded.append(kb_file_path)
                            print(f"   [OK] Downloaded KB file: {kb_filename}")
                        except Exception as e:
                            print(f"   [WARNING] Failed to download KB file {kb_file_path}: {e}")

                print(f"[OK] KB files downloaded: {len(kb_downloaded)} items")
                pipeline_result['kb_downloaded'] = kb_downloaded
                pipeline_result['kb_work_dir'] = kb_work_dir
            else:
                print("\nℹ️ No KB files configured, skipping KB ingestion")
                pipeline_result['kb_downloaded'] = []
                pipeline_result['kb_work_dir'] = None

            # ========== SECTION 3: NORMALIZATION ==========
            print("\n" + "=" * 60)
            print("SECTION 3 - NORMALIZATION")
            print("=" * 60)

            section3 = Section3Normalization(manifest, task_id=task_id)
            normalized_data = section3.normalize()

            print("[OK] Section 3 complete:")
            print(f"   - Normalized inputs: {len(normalized_data.get('normalized_inputs', []))}")
            print(f"   - Normalized outputs: {len(normalized_data.get('normalized_outputs', []))}")
            print(f"   - Ambiguities logged: {len(normalized_data.get('ambiguities', []))}")

            pipeline_result['section3_normalized'] = normalized_data

            # Normalize client files (optional)
            if pipeline_result.get('section2_client_manifest'):
                print("\n🔄 Normalizing client context files...")
                client_section3 = Section3Normalization(pipeline_result['section2_client_manifest'], task_id=task_id)
                client_normalized = client_section3.normalize()
                print(f"[OK] Client context normalized: {len(client_normalized.get('normalized_inputs', []))} files")
                pipeline_result['section3_client_normalized'] = client_normalized
            else:
                pipeline_result['section3_client_normalized'] = None

            # ========== SECTION 4: WORKFLOW RECONSTRUCTION ==========
            print("\n" + "=" * 60)
            print("SECTION 4 - WORKFLOW RECONSTRUCTION")
            print("=" * 60)

            section4 = Section4Workflow(
                section2_manifest=manifest,
                section3_output=normalized_data,
                task_id=task_id
            )
            workflow_data = section4.reconstruct()

            print("[OK] Section 4 complete:")
            print(f"   - Declared workflows: {len(workflow_data.get('declared_workflows', []))}")
            print(f"   - Execution events: {len(workflow_data.get('execution_timeline', []))}")
            print(f"   - Step comparisons: {len(workflow_data.get('workflow_comparison', []))}")
            print(f"   - Unmatched steps: {len(workflow_data.get('unmatched_steps', []))}")

            pipeline_result['section4_workflow'] = workflow_data

            # ========== SECTION 5: CLIENT CONTEXT INTERPRETATION ==========
            print("\n" + "=" * 60)
            print("SECTION 5 - CLIENT CONTEXT INTERPRETATION")
            print("=" * 60)

            section5 = Section5ClientContext(
                section2_manifest=manifest,
                section3_output=normalized_data,
                section4_output=workflow_data
            )
            context_data = section5.interpret()

            print("[OK] Section 5 complete:")
            print(f"   - Context domains: {len(context_data.get('client_context_model', {}).keys())}")
            print(f"   - Conflicts detected: {len(context_data.get('conflicts', []))}")
            print(f"   - Context warnings: {len(context_data.get('context_warnings', []))}")

            # Print context confidence
            confidence = context_data.get('context_confidence', {})
            if confidence:
                print("   - Context confidence:")
                for domain, score in confidence.items():
                    print(f"     • {domain}: {score:.2f}")

            pipeline_result['section5_context'] = context_data

            # ========== SPECIALIZATION ROUTER ==========
            # Fully automatic: detect a specialized task pack from the materials.
            # If none matches, use the generic criteria engine.
            from services.specialization_router import detect_specialization

            specialization = detect_specialization(normalized_data)
            pipeline_result['specialization'] = specialization
            pipeline_result['mode'] = 'specialization' if specialization else 'generic'

            print("\n" + "=" * 60)
            if specialization:
                print(f"ROUTER: specialization detected -> {specialization}")
            else:
                print("ROUTER: no specialization matched -> generic engine")
            print("=" * 60)

            if specialization:
                self._run_specialization_path(
                    pipeline_result, specialization, normalized_data, workflow_data, context_data
                )
            else:
                self._run_generic_path(
                    pipeline_result, normalized_data, workflow_data,
                    task_description=task_description, reference_texts=reference_texts
                )

            # ========== PIPELINE COMPLETE ==========
            execution_time = time.time() - start_time
            pipeline_result['execution_time_seconds'] = execution_time

            print("\n" + "=" * 60)
            print(f"[OK] SECTIONS 2-7 PIPELINE COMPLETE ({execution_time:.1f}s)")
            print("=" * 60)

            return pipeline_result

        except Exception as e:
            execution_time = time.time() - start_time
            pipeline_result['execution_time_seconds'] = execution_time
            pipeline_result['error'] = str(e)
            print(f"\n[FAIL] Pipeline failed after {execution_time:.1f}s: {e}")
            raise

    # ================= ROUTER BRANCHES =================

    def _run_specialization_path(self, pipeline_result, specialization, normalized_data,
                                 workflow_data, context_data):
        """Exact, hand-coded checks for a detected specialization (e.g. TDS 26Q)."""
        print("\n" + "=" * 60)
        print(f"SECTION 6 - DETERMINISTIC RULES ({specialization})")
        print("=" * 60)
        from services.section6_rule_engine_simple import SimplifiedRuleEngine

        section6 = SimplifiedRuleEngine(task_id=specialization)
        rule_engine_output = section6.evaluate(
            normalized_data=normalized_data,
            workflow_data=workflow_data,
            client_context=context_data,
        )
        print(f"   Passed {rule_engine_output.passed_count}, "
              f"Failed {rule_engine_output.failed_count}, "
              f"Indeterminate {rule_engine_output.indeterminate_count}")
        pipeline_result['section6_rules'] = rule_engine_output

        print("\n" + "=" * 60)
        print(f"SECTION 7 - AI WORKFLOW VALIDATOR ({specialization})")
        print("=" * 60)
        from services.section7_ai_validator import AIWorkflowValidator
        try:
            section7 = AIWorkflowValidator(task_id=specialization)
            ai_validation_results = section7.validate(
                workflow_data=workflow_data,
                normalized_data=normalized_data,
                rule_engine_results=rule_engine_output,
            )
            summary = ai_validation_results.get('summary', {})
            print(f"   Overall: {summary.get('overall_status', 'UNKNOWN')} "
                  f"({summary.get('passed_steps', 0)}/{summary.get('total_steps', 0)} steps passed)")
            pipeline_result['section7_validation'] = ai_validation_results
        except Exception as e:
            logger.error(f"Section 7 failed: {e}", exc_info=True)
            print(f"[WARNING] Section 7 failed: {e}")
            pipeline_result['section7_validation'] = None
            pipeline_result['section7_error'] = str(e)

    def _run_generic_path(self, pipeline_result, normalized_data, workflow_data,
                          task_description="", reference_texts=None):
        """Generic engine: derive criteria, run deterministic checks + AI validation."""
        print("\n" + "=" * 60)
        print("GENERIC ENGINE - CRITERIA DERIVATION + VALIDATION")
        print("=" * 60)

        from services.criteria_engine import derive_check_spec
        from services.generic_checks import run_generic_checks
        from services.generic_validator import GenericValidator
        from services.jury import PanelValidator, should_convene_panel
        from services.llm_client import supports_tool_loop
        from services.tool_validator import ToolCallingValidator, agentic_validation_enabled

        client_texts, kb_texts = self._gather_text_materials(pipeline_result)

        from services import cost
        cost_scope = cost.track()
        cost_tracker = cost_scope.__enter__()  # capture derivation + validation token usage
        try:
            check_spec = derive_check_spec(
                normalized_data, workflow_data,
                task_description=task_description,
                client_context_texts=client_texts,
                kb_texts=kb_texts,
                reference_texts=reference_texts,
            )
            print(f"   Derived {len(check_spec.criteria)} criteria "
                  f"({len(check_spec.deterministic_criteria)} deterministic, "
                  f"{len(check_spec.semantic_criteria)} semantic)")
            pipeline_result['check_spec'] = check_spec.to_dict()

            deterministic_results = run_generic_checks(check_spec, normalized_data)
            print(f"   Deterministic results computed for {len(deterministic_results)} criteria")

            # Validator selection. Deterministic checks above already used "real tools"
            # for every criterion whose structure maps. For the rest:
            #   PANEL (switchable, AI_PANEL_ENABLED) -> multiple judges + adversarial critic
            #   else AGENTIC default -> the model decides per criterion: call a full-data
            #         tool when one fits, otherwise read/reason directly (like an agent
            #         harness). Falls back to the plain chunked validator only when the
            #         configured model can't do tool calling.
            tl_model = os.getenv("AI_TOOL_LOOP_MODEL") or os.getenv("AI_VALIDATION_MODEL") or os.getenv("AI_PRIMARY_MODEL", "gpt-4o-mini")
            if should_convene_panel(check_spec):
                print("   Validation mode: PANEL (auto-convened: jurors + adversarial critic)")
                validator = PanelValidator()
            elif agentic_validation_enabled() and supports_tool_loop(tl_model):
                print("   Validation mode: AGENTIC (model calls full-data tools, reads where no tool fits)")
                validator = ToolCallingValidator()
            else:
                print("   Validation mode: plain AI validator (model not tool-capable / disabled)")
                validator = GenericValidator()

            generic_result = validator.validate(
                check_spec, normalized_data, workflow_data,
                deterministic_results=deterministic_results,
            )
            summary = generic_result.get('summary', {})
            print(f"   Overall: {summary.get('overall_status', 'UNKNOWN')} "
                  f"({summary.get('passed', 0)} passed / {summary.get('failed', 0)} failed / "
                  f"{summary.get('unclear', 0)} unclear of {summary.get('total', 0)})")
            pipeline_result['generic_validation'] = generic_result

        except Exception as e:
            logger.error(f"Generic engine failed: {e}", exc_info=True)
            print(f"[WARNING] Generic engine failed: {e}")
            pipeline_result['check_spec'] = pipeline_result.get('check_spec')
            pipeline_result['generic_validation'] = None
            pipeline_result['generic_error'] = str(e)
        finally:
            cost_scope.__exit__(None, None, None)
            pipeline_result['cost'] = cost_tracker.summary()
            print(f"   Cost: ${pipeline_result['cost']['cost_usd']} "
                  f"({pipeline_result['cost']['input_tokens']}+{pipeline_result['cost']['output_tokens']} tokens, "
                  f"{pipeline_result['cost']['calls']} calls)")

    def _gather_text_materials(self, pipeline_result):
        """Collect client-context and KB text to feed criteria derivation."""
        client_texts = []
        client_manifest = pipeline_result.get('section2_client_manifest')
        if client_manifest:
            for f in client_manifest.get('client_context_files', []) or []:
                text = (f.get('text') or '').strip()
                if text and not text.startswith('[Binary'):
                    client_texts.append(f"{f.get('file', '')}:\n{text}")

        kb_texts = []
        manifest = pipeline_result.get('section2_manifest', {})
        for f in (manifest or {}).get('knowledge_base_files', []) or []:
            text = (f.get('text') or '').strip()
            if text and not text.startswith('[Binary'):
                kb_texts.append(f"{f.get('file', '')}:\n{text}")

        # Separately-downloaded KB files (agent kb_files / kb_folders)
        kb_dir = pipeline_result.get('kb_work_dir')
        if kb_dir and os.path.isdir(kb_dir):
            from services.section2_ingestion import extract_kb_text
            for root, _dirs, files in os.walk(kb_dir):
                for name in files:
                    try:
                        data = extract_kb_text(os.path.join(root, name))
                        text = (data.get('text') or '').strip()
                        if text and not text.startswith('[Binary'):
                            kb_texts.append(f"{name}:\n{text}")
                    except Exception:
                        continue

        return client_texts, kb_texts

    def cleanup(self):
        """Clean up temporary work directory"""
        import shutil
        if os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir, ignore_errors=True)
            print(f"🧹 Cleaned up work directory: {self.work_dir}")


def run_section_pipeline(
    user_id: str,
    agent_id: str,
    access_token: str,
    task_folder: str,
    task_id: str = "tds_26q",
    client_folder: Optional[str] = None,
    kb_folders: Optional[list] = None,
    kb_files: Optional[list] = None,
    file_source=None,
    task_description: str = "",
    reference_texts: Optional[list] = None
) -> Dict[str, Any]:
    """
    Convenience function to run the full Sections 2-7 pipeline

    Args:
        user_id: User ID
        agent_id: Agent ID
        access_token: OneDrive access token
        task_folder: OneDrive path to task folder
        task_id: Task identifier for task pack (default: "tds_26q")
        client_folder: Optional OneDrive path to client folder
        kb_folders: Optional list of KB folder paths
        kb_files: Optional list of KB file paths

    Returns:
        Pipeline result dictionary with outputs from all sections (2-7)
    """
    pipeline = SectionPipeline(user_id, agent_id, access_token, file_source=file_source)
    return pipeline.run(
        task_folder, task_id, client_folder, kb_folders, kb_files,
        task_description=task_description, reference_texts=reference_texts,
    )
