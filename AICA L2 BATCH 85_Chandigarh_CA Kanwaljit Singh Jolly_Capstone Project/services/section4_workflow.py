"""
SECTION 4 - WORKFLOW RECONSTRUCTION ENGINE

Converts unstructured workflow descriptions into structured models
and reconstructs actual execution from file artifacts.

Core Principles:
- Compare declared workflow vs actual execution
- Record deviations WITHOUT judging correctness
- NO AI, NO LLM - Pure logic only
- Explicit confidence scoring

Implementation: DETERMINISTIC ONLY
"""

import os
import re
from datetime import datetime
from typing import Any, Dict, List, Tuple

# ==================== 4.2 WORKFLOW TEXT INGESTION ====================

def parse_workflow_blocks(workflow_text: str) -> List[Dict[str, Any]]:
    """
    Parse workflow text into hierarchical blocks.

    Numbered headings (1., 2., 3.) become step blocks with ALL content underneath
    collected until the next numbered heading.

    Args:
        workflow_text: Raw workflow text

    Returns:
        List of blocks:
        - type='step': Numbered heading with all content underneath
        - type='paragraph': Intro/overview text before first numbered step
    """
    blocks = []
    lines = workflow_text.split('\n')

    current_step = None
    block_id = 1

    for line_no, line in enumerate(lines, 1):
        stripped = line.strip()

        if not stripped:
            # Empty lines are ignored - we group content continuously
            continue

        # Check for numbered heading: "1. Title", "2. Title", etc.
        numbered_match = re.match(r'^(\d+)\.\s+(.+)$', stripped)

        if numbered_match:
            # Save previous step if it exists
            if current_step:
                blocks.append(current_step)

            # Start new step
            step_num = int(numbered_match.group(1))
            step_heading = numbered_match.group(2).strip()

            current_step = {
                'block_id': f'b{block_id}',
                'type': 'step',
                'step_number': step_num,
                'heading': step_heading,
                'content_lines': [],  # Collect all lines under this step
                'order': block_id,
                'line_no': line_no
            }
            block_id += 1

        elif current_step:
            # We're inside a step - accumulate all content
            current_step['content_lines'].append(stripped)

        else:
            # Not in a step yet - this is intro/overview text
            blocks.append({
                'block_id': f'b{block_id}',
                'type': 'paragraph',
                'text': stripped,
                'order': block_id,
                'line_no': line_no
            })
            block_id += 1

    # Add last step if exists
    if current_step:
        blocks.append(current_step)

    return blocks


# ==================== 4.3 DECLARED WORKFLOW PARSING ====================

# Step detection keywords
STEP_KEYWORDS = ['step', 'stage', 'phase', 'process', 'procedure', 'action']

# Conditional keywords
CONDITIONAL_KEYWORDS = ['if', 'only when', 'in case of', 'otherwise', 'unless', 'when']


def detect_steps(blocks: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Extract steps from blocks.

    Now uses hierarchical 'step' blocks that contain:
    - heading: The numbered title (e.g., "Exported File Details")
    - content_lines: All paragraphs under that heading until next numbered step

    Args:
        blocks: Parsed workflow blocks

    Returns:
        (steps, is_structured)
    """
    steps = []

    for block in blocks:
        if block['type'] == 'step':
            # Block represents a complete step with heading + all content underneath
            step_num = block['step_number']
            step_heading = block['heading']
            content_lines = block.get('content_lines', [])

            # Join content lines into full description
            full_content = '\n'.join(content_lines)

            # Extract sub-sections (e.g., "Serial Number", "Section Code", etc.)
            sub_sections = extract_sub_sections(content_lines)

            # Format description with sub-sections clearly marked
            if sub_sections:
                description_parts = []
                for subsection in sub_sections:
                    subsection_text = f"**{subsection['heading']}**\n" + '\n'.join(subsection['content'])
                    description_parts.append(subsection_text)
                formatted_description = '\n\n'.join(description_parts)
            else:
                formatted_description = full_content

            # Combine heading + content for raw_text
            raw_text = f"{step_num}. {step_heading}\n{full_content}"

            steps.append({
                'step_id': f'STEP_{step_num:02d}',
                'sequence': step_num,
                'order': step_num,
                'title': step_heading,
                'description': formatted_description,
                'raw_text': raw_text,
                'sub_sections': sub_sections,  # NEW: structured sub-sections
                'artifacts_expected': extract_artifacts(full_content),
                'dependencies': [],
                'conditions': extract_conditions(full_content),
                'confidence': 0.95,  # High confidence for numbered steps with content
                'source_block': block['block_id']
            })

    # Determine if workflow is structured
    is_structured = len(steps) >= 2

    return (steps, is_structured)


def extract_artifacts(step_text: str, task=None) -> List[str]:
    """
    Extract expected artifacts from step text.

    Look for file types, document names, etc.
    NOW GENERIC: Can accept task-specific patterns.
    """
    artifacts = []

    # Generic artifact keywords (task-agnostic)
    artifact_patterns = [
        r'(excel|spreadsheet|csv|xlsx)',
        r'(pdf|document|report)',
        r'(invoice|receipt|form)',
        r'(ledger|statement|account)',
        r'(file|output|result)'
    ]

    # Add task-specific patterns if task provided
    if task:
        try:
            task_patterns = task.get_document_type_patterns()
            artifact_patterns.extend(task_patterns)
        except (AttributeError, NotImplementedError):
            pass  # Task doesn't have custom patterns

    for pattern in artifact_patterns:
        if re.search(pattern, step_text, re.IGNORECASE):
            artifacts.append(pattern.strip('()'))

    return artifacts


def extract_sub_sections(content_lines: List[str]) -> List[Dict[str, Any]]:
    """
    Extract sub-sections from step content.

    Sub-sections are typically:
    - Short lines (< 60 chars) that look like headings
    - Followed by explanatory paragraphs

    Example:
        Serial Number
        Add serial numbers sequentially.

        Section Code
        Section code represents the nature of payment.

    Returns:
        List of sub-sections with heading and content
    """
    sub_sections = []
    current_subsection = None

    for line in content_lines:
        # Heuristic: Sub-section headers are:
        # - Short (< 60 chars)
        # - Don't end with period (not a sentence)
        # - Start with capital letter
        # - Have at least 2 words
        words = line.split()
        looks_like_header = (
            len(line) < 60 and
            not line.endswith('.') and
            not line.endswith(',') and
            len(words) >= 2 and
            words[0][0].isupper() and
            not any(line.startswith(prefix) for prefix in ['The ', 'It ', 'This ', 'If ', 'When ', 'Enter ', 'Fill ', 'Add ', 'Select '])
        )

        if looks_like_header:
            # Save previous subsection
            if current_subsection and current_subsection['content']:
                sub_sections.append(current_subsection)

            # Start new subsection
            current_subsection = {
                'heading': line,
                'content': []
            }
        elif current_subsection:
            # Add to current subsection content
            current_subsection['content'].append(line)

    # Add last subsection
    if current_subsection and current_subsection['content']:
        sub_sections.append(current_subsection)

    return sub_sections


def extract_conditions(step_text: str) -> List[str]:
    """
    Extract conditional logic from step text.

    Only mark as conditional if explicit keywords appear at sentence boundaries.
    This prevents false positives from words containing "if" like "specific", "verify", etc.
    """
    conditions = []

    # Look for conditional keywords at word boundaries (not inside words)
    step_lower = step_text.lower()

    for keyword in CONDITIONAL_KEYWORDS:
        # Use word boundary regex to avoid matching inside words
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, step_lower):
            # Additional check: only flag if it's at the start of a sentence or after punctuation
            # This avoids flagging "If the 4th character..." which is just descriptive, not conditional
            if re.search(r'(^|\. |\n)' + pattern, step_lower):
                conditions.append(f"Conditional: {keyword}")

    return conditions


# ==================== 4.4 DECLARED WORKFLOW GRAPH ====================

def build_workflow_graph(steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build DAG representation of declared workflow.

    Args:
        steps: List of declared steps

    Returns:
        {
            "nodes": ["STEP_01", "STEP_02"],
            "edges": [{"from": "STEP_01", "to": "STEP_02", "type": "SEQUENCE"}]
        }
    """
    nodes = [step['step_id'] for step in steps]
    edges = []

    # Build sequential edges (linear execution unless conditional)
    for i in range(len(steps) - 1):
        from_step = steps[i]
        to_step = steps[i + 1]

        edge_type = 'CONDITIONAL' if from_step.get('conditions') else 'SEQUENCE'

        edges.append({
            'from': from_step['step_id'],
            'to': to_step['step_id'],
            'type': edge_type
        })

    return {
        'nodes': nodes,
        'edges': edges
    }


# ==================== 4.5 ACTUAL EXECUTION RECONSTRUCTION ====================

def extract_execution_events(output_files: List[Dict[str, Any]], normalized_outputs: List[Dict[str, Any]] = None, task=None) -> List[Dict[str, Any]]:
    """
    Extract execution events with TWO-TIER evidence model.

    NOW GENERIC: Delegates task-specific event detection to task pack.

    TIER 1 (Structural Evidence - proves workflow COULD be executed):
    - Worksheets/data structures present
    - Required fields exist in structure
    - File format matches expected output

    TIER 2 (Content Evidence - proves workflow WAS executed correctly):
    - Data actually populated (non-empty)
    - Data quality checks (sequential, valid, complete)
    - Cross-field validations

    Args:
        output_files: List of output file metadata from Section 2
        normalized_outputs: List of extracted output data from Section 3
        task: Task pack instance (optional)

    Returns:
        List of execution events with tier classification
    """
    events = []
    event_id = 1

    # If we have normalized outputs and task pack, use task-specific event detection
    if normalized_outputs and task:
        # Delegate to task pack for event detection
        normalized_data = {'normalized_outputs': normalized_outputs}
        events = task.detect_workflow_events(normalized_data)

    elif normalized_outputs:
        # Fallback: Generic file presence detection (no task-specific logic)
        for output in normalized_outputs:
            filename = output.get('file', '')
            events.append({
                'event_id': f'EVT_{event_id:02d}',
                'event_type': 'OUTPUT_FILE_PRESENT',
                'tier': 1,
                'file': filename,
                'details': 'Output file exists (no task-specific analysis)',
                'evidence': ['file_presence'],
                'confidence': 0.30,
                'related_step_keywords': ['file', 'output', 'created']
            })
            event_id += 1

    else:
        # Fallback: metadata-only (old behavior) - Tier 1 at best
        for file_meta in output_files:
            filename = file_meta.get('name', '')
            events.append({
                'event_id': f'EVT_{event_id:02d}',
                'event_type': 'FILE_CREATED',
                'tier': 1,
                'file': filename,
                'details': 'File exists (no content analysis available)',
                'evidence': ['file_presence'],
                'confidence': 0.30,  # Very low - can't infer anything meaningful
                'related_step_keywords': []
            })
            event_id += 1

    return events


def build_execution_timeline(events: List[Dict[str, Any]]) -> List[str]:
    """
    Sort events by timestamp to build execution timeline.

    Args:
        events: List of execution events

    Returns:
        List of event IDs in chronological order
    """
    # Separate events with and without timestamps
    events_with_ts = [e for e in events if e.get('timestamp')]
    events_without_ts = [e for e in events if not e.get('timestamp')]

    # Sort events with timestamps
    try:
        sorted_events = sorted(events_with_ts, key=lambda e: datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00')))
    except Exception:
        # Fallback if timestamp parsing fails
        sorted_events = events_with_ts

    # Append events without timestamps at the end (ambiguous order)
    all_events = sorted_events + events_without_ts

    return [e['event_id'] for e in all_events]


# ==================== 4.6 STEP ↔ EVENT MATCHING ====================

def match_steps_to_events(steps: List[Dict[str, Any]], events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Match declared steps to execution events with TIER-AWARE scoring.

    Matching rules:
    - Tier 2 events (content evidence) contribute more to match confidence
    - Tier 1 events (structural evidence) provide baseline confidence
    - Step text keywords match event keywords
    - Artifact expectations match file types

    Args:
        steps: Declared steps
        events: Execution events (with 'tier' field: 1=structural, 2=content)

    Returns:
        List of match records with tier-aware confidence
    """
    matches = []

    for step in steps:
        step_text_lower = step['raw_text'].lower()
        step_title_lower = step.get('title', '').lower()
        matched_events = []
        match_type = 'NONE'

        for event in events:
            # NEW: Use related_step_keywords from content-based events
            event_keywords = event.get('related_step_keywords', [])
            event_tier = event.get('tier', 1)  # Default to tier 1 if not specified

            # Check if step keywords match event keywords
            score = 0

            # Check title match (e.g., "ChallanDetails" step matches "CHALLANDETAILS_POPULATED" event)
            for keyword in event_keywords:
                if keyword in step_title_lower or keyword in step_text_lower:
                    # TIER MULTIPLIER: Tier 2 events get higher score
                    base_score = 3
                    score += base_score * (1.5 if event_tier == 2 else 1.0)  # Tier 2: 4.5 points, Tier 1: 3 points

            # Check sub-section keywords
            for subsection in step.get('sub_sections', []):
                subsection_heading = subsection.get('heading', '').lower()
                for keyword in event_keywords:
                    if keyword in subsection_heading:
                        base_score = 2
                        score += base_score * (1.5 if event_tier == 2 else 1.0)  # Tier 2: 3 points, Tier 1: 2 points

            # Fallback: Check artifact keywords
            for artifact in step.get('artifacts_expected', []):
                for keyword in event_keywords:
                    if keyword in artifact.lower():
                        base_score = 1
                        score += base_score * (1.5 if event_tier == 2 else 1.0)  # Tier 2: 1.5 points, Tier 1: 1 point

            if score > 0:
                matched_events.append({
                    'event_id': event['event_id'],
                    'score': score,
                    'tier': event_tier,
                    'event_type': event.get('event_type', 'UNKNOWN'),
                    'confidence': event.get('confidence', 0.5)
                })

        # Determine match type based on score AND tier composition
        if matched_events:
            # Sort by score
            matched_events.sort(key=lambda x: x['score'], reverse=True)
            best_score = matched_events[0]['score']

            # Count tier breakdown
            tier1_events = [e for e in matched_events if e['tier'] == 1]
            tier2_events = [e for e in matched_events if e['tier'] == 2]

            # Match type determination (tier-aware)
            if best_score >= 4.0 and tier2_events:  # Strong match with Tier 2 evidence
                match_type = 'FULL'
            elif best_score >= 3.0:  # Strong keyword match
                match_type = 'FULL'
            elif best_score >= 2.0:  # Medium match
                match_type = 'PARTIAL'
            else:  # Weak match
                match_type = 'POSSIBLE'

        # Calculate confidence based on match quality AND tier evidence
        confidence = 0.0
        tier_bonus = 0.0

        if matched_events:
            # Base confidence from match type
            if match_type == 'FULL':
                confidence = 0.70  # Lowered base - tier bonus will boost it
            elif match_type == 'PARTIAL':
                confidence = 0.50
            elif match_type == 'POSSIBLE':
                confidence = 0.25

            # Tier bonus: Having Tier 2 events significantly boosts confidence
            tier2_events = [e for e in matched_events if e['tier'] == 2]
            tier1_events = [e for e in matched_events if e['tier'] == 1]

            if tier2_events:
                # Tier 2 content evidence found - strong boost
                tier_bonus = 0.20
            elif tier1_events:
                # Only Tier 1 structural evidence - moderate boost
                tier_bonus = 0.10

            confidence = min(0.95, confidence + tier_bonus)  # Cap at 0.95

        matches.append({
            'step_id': step['step_id'],
            'matched_events': [e['event_id'] for e in matched_events],  # Extract just IDs
            'event_details': matched_events,  # Keep full details for analysis
            'match_type': match_type,
            'confidence': confidence,
            'tier_breakdown': {
                'tier1_count': len([e for e in matched_events if e.get('tier') == 1]),
                'tier2_count': len([e for e in matched_events if e.get('tier') == 2])
            }
        })

    return matches


# ==================== 4.7 WORKFLOW COMPARISON ====================

def compare_workflows(declared_steps: List[Dict[str, Any]], matches: List[Dict[str, Any]],
                      events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Compare declared workflow vs actual execution.

    Detects:
    - Missing steps (declared but not executed)
    - Extra steps (executed but not declared)
    - Out-of-order steps

    Args:
        declared_steps: Declared workflow steps
        matches: Step-event matches
        events: Execution events

    Returns:
        List of comparison records
    """
    comparisons = []

    # Check declared steps
    for step in declared_steps:
        step_id = step['step_id']
        match = next((m for m in matches if m['step_id'] == step_id), None)

        executed = match and match['match_type'] in ['FULL', 'PARTIAL']

        comparison = {
            'step_id': step_id,
            'declared': True,
            'executed': executed,
            'reason': '',
            'severity_hint': ''
        }

        if not executed:
            comparison['reason'] = 'No matching execution evidence'
            comparison['severity_hint'] = 'POTENTIAL_SKIP'
        elif match['match_type'] == 'PARTIAL':
            comparison['reason'] = 'Partial execution evidence'
            comparison['severity_hint'] = 'INCOMPLETE_EXECUTION'

        comparisons.append(comparison)

    # Check for extra events (not matched to any step)
    all_matched_events = set()
    for match in matches:
        all_matched_events.update(match['matched_events'])

    for event in events:
        if event['event_id'] not in all_matched_events:
            comparisons.append({
                'step_id': None,
                'event_id': event['event_id'],
                'declared': False,
                'executed': True,
                'reason': 'Execution event not matched to any declared step',
                'severity_hint': 'EXTRA_STEP'
            })

    return comparisons


def find_unmatched_steps(comparisons: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract unmatched steps (declared but not executed).

    Args:
        comparisons: Workflow comparison results

    Returns:
        List of unmatched steps
    """
    return [c for c in comparisons if c['declared'] and not c['executed']]


# ==================== 4.10 SECTION 4 ORCHESTRATOR ====================

class Section4Workflow:
    """
    Workflow Reconstruction Engine - Section 4 orchestrator.

    Takes Section 2 manifest + Section 3 normalized inputs,
    produces workflow comparison.
    NOW GENERIC: Uses task packs for task-specific event detection.
    """

    def __init__(self, section2_manifest: Dict[str, Any], section3_output: Dict[str, Any], task_id: str):
        """
        Args:
            section2_manifest: Output from Section 2
            section3_output: Output from Section 3
            task_id: Task identifier (e.g., "tds_26q")
        """
        self.manifest = section2_manifest
        self.normalized_inputs = section3_output
        self.task_id = task_id
        self.confidence_notes = []

        # Load task pack
        from services.task_loader import load_task
        self.task = load_task(task_id)

    def reconstruct(self) -> Dict[str, Any]:
        """
        Execute full workflow reconstruction pipeline.

        Returns:
            {
                "declared_workflows": [...],
                "reconstructed_execution": {...},
                "workflow_comparison": [...],
                "unmatched_steps": [...],
                "confidence_notes": [...]
            }
        """
        print("=" * 80)
        print("SECTION 4: WORKFLOW RECONSTRUCTION START")
        print("=" * 80)

        # Step 1: Parse workflow text
        print("\n[1/7] Parsing workflow text...")
        workflow_files = self.manifest.get('workflow_files', [])

        if not workflow_files:
            print("   [WARNING] No workflow files found")
            return self._empty_result()

        declared_workflows = []

        for wf in workflow_files:
            # Handle both string paths (from Section 2) and dict format (from other sources)
            if isinstance(wf, str):
                # wf is a file path string
                workflow_file_path = wf
                filename = os.path.basename(workflow_file_path)

                # Extract text from the workflow file
                print(f"   -> Extracting text from: {filename}")

                if workflow_file_path.endswith('.docx'):
                    from services.file_processor import extract_docx_text
                    raw_text = extract_docx_text(workflow_file_path)
                elif workflow_file_path.lower().endswith(('.txt', '.md')):
                    with open(workflow_file_path, 'r', encoding='utf-8') as f:
                        raw_text = f.read()
                else:
                    print(f"   [WARNING] Unsupported workflow file type: {filename}")
                    continue
            else:
                # wf is a dict with pre-extracted content
                filename = wf.get('workflow_file', '')
                raw_text = wf.get('raw_text', '')

            print(f"   -> Processing: {filename}")

            # Parse blocks
            blocks = parse_workflow_blocks(raw_text)

            # Detect steps
            steps, is_structured = detect_steps(blocks)

            if not is_structured:
                self.confidence_notes.append({
                    'file': filename,
                    'note': 'Workflow marked as UNSTRUCTURED - step detection has low confidence'
                })

            # Build graph
            workflow_graph = build_workflow_graph(steps)

            declared_workflows.append({
                'workflow_file': filename,
                'blocks': blocks,
                'steps': steps,
                'is_structured': is_structured,
                'workflow_graph': workflow_graph
            })

            print(f"      [OK] Detected {len(steps)} steps (structured: {is_structured})")

        # Step 2: Extract execution events (from content, not just metadata)
        print("\n[2/7] Extracting execution events...")
        output_files = self.manifest.get('role_index', {}).get('OUTPUTS', [])
        normalized_outputs = self.normalized_inputs.get('normalized_outputs', [])
        events = extract_execution_events(output_files, normalized_outputs, task=self.task)
        print(f"   [OK] Extracted {len(events)} events")

        # Step 3: Build execution timeline
        print("\n[3/7] Building execution timeline...")
        timeline = build_execution_timeline(events)
        print(f"   [OK] Timeline built ({len(timeline)} events)")

        # Step 4: Match steps to events
        print("\n[4/7] Matching steps to events...")
        all_steps = []
        for wf in declared_workflows:
            all_steps.extend(wf['steps'])

        matches = match_steps_to_events(all_steps, events)
        matched_count = sum(1 for m in matches if m['match_type'] in ['FULL', 'PARTIAL'])
        print(f"   [OK] Matched {matched_count}/{len(all_steps)} steps")

        # Step 5: Compare workflows
        print("\n[5/7] Comparing declared vs actual...")
        comparisons = compare_workflows(all_steps, matches, events)
        print(f"   [OK] Generated {len(comparisons)} comparisons")

        # Step 6: Find unmatched steps
        print("\n[6/7] Finding unmatched steps...")
        unmatched = find_unmatched_steps(comparisons)
        if unmatched:
            print(f"   [WARNING] Found {len(unmatched)} unmatched steps")
        else:
            print("   [OK] All declared steps matched")

        # Step 7: Build final output
        print("\n[7/7] Building output...")

        result = {
            'declared_workflows': declared_workflows,
            'reconstructed_execution': {
                'events': events,
                'timeline': timeline
            },
            'step_event_matches': matches,
            'workflow_comparison': comparisons,
            'unmatched_steps': unmatched,
            'confidence_notes': self.confidence_notes
        }

        print("\n" + "=" * 80)
        print("SECTION 4: WORKFLOW RECONSTRUCTION COMPLETE")
        print("=" * 80)

        return result

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result when no workflow files found"""
        return {
            'declared_workflows': [],
            'reconstructed_execution': {'events': [], 'timeline': []},
            'step_event_matches': [],
            'workflow_comparison': [],
            'unmatched_steps': [],
            'confidence_notes': [{'note': 'No workflow files found'}]
        }


# ==================== CONVENIENCE FUNCTION ====================

def reconstruct_workflow(section2_manifest: Dict[str, Any], section3_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function for Section 4 workflow reconstruction.

    Args:
        section2_manifest: Output from Section 2
        section3_output: Output from Section 3

    Returns:
        Workflow reconstruction output
    """
    reconstructor = Section4Workflow(section2_manifest, section3_output)
    return reconstructor.reconstruct()
