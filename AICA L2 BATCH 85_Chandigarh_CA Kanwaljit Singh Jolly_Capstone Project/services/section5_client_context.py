"""
SECTION 5 - CLIENT CONTEXT INTERPRETATION ENGINE

Converts arbitrary, unstructured client information into structured,
machine-usable context model.

Core Principles:
- No predefined schema (accept ANYTHING)
- Multi-pass extraction (raw signals -> tagging -> rules)
- Conflicts preserved (NOT resolved)
- AI used for tagging ONLY (not inference)
- Does NOT decide violations

Extraction Pipeline: 3-pass
- PASS 1: Raw signal extraction (NO AI)
- PASS 2: Controlled semantic tagging (LIMITED AI)
- PASS 3: Rule candidate extraction
"""

import json
import os
import re
from typing import Any, Dict, List

from dotenv import load_dotenv

from services.llm_client import complete as llm_complete

load_dotenv()


# ==================== 5.4 CONTEXT EXTRACTION DOMAINS ====================

CONTEXT_DOMAINS = [
    'OPERATIONS',           # How the client actually works
    'PROCESS_VARIATIONS',   # Deviations from standard workflows
    'RISK_TOLERANCE',       # How strict the client is
    'APPROVAL_RULES',       # Who can approve what
    'TIMING_RULES',         # Deadlines, buffers
    'EXCEPTIONS',           # Explicitly allowed skips
    'JURISDICTION',         # Geography, regulators
    'TERMINOLOGY'           # Client-specific language
]


# ==================== PASS 1: RAW SIGNAL EXTRACTION (NO AI) ====================

def extract_raw_signals(client_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    PASS 1: Extract raw signals from client files WITHOUT interpretation.

    Extracts:
    - Bullet points
    - Headings
    - Tables
    - Keywords
    - Named entities (names, roles, dates)

    Args:
        client_files: Client context files from Section 2

    Returns:
        List of raw signal objects
    """
    signals = []

    for file_obj in client_files:
        filename = file_obj.get('file', '')
        text = file_obj.get('text', '')

        if not text or text.startswith('[Binary file'):
            # Skip binary files
            continue

        # Extract bullet points
        bullet_points = re.findall(r'^\s*[-•*]\s+(.+)$', text, re.MULTILINE)
        for bullet in bullet_points:
            signals.append({
                'type': 'bullet_point',
                'text': bullet.strip(),
                'source_file': filename,
                'confidence': 0.9
            })

        # Extract headings (lines ending with colon or all caps)
        headings = re.findall(r'^([A-Z][A-Z\s]+):?$', text, re.MULTILINE)
        for heading in headings:
            signals.append({
                'type': 'heading',
                'text': heading.strip(),
                'source_file': filename,
                'confidence': 0.85
            })

        # Extract numbered items
        numbered_items = re.findall(r'^\s*\d+\.\s+(.+)$', text, re.MULTILINE)
        for item in numbered_items:
            signals.append({
                'type': 'numbered_item',
                'text': item.strip(),
                'source_file': filename,
                'confidence': 0.9
            })

        # Extract paragraphs (simple heuristic: non-empty lines)
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        for para in paragraphs[:10]:  # Limit to first 10 paragraphs
            if len(para) > 20:  # Ignore very short paragraphs
                signals.append({
                    'type': 'paragraph',
                    'text': para,
                    'source_file': filename,
                    'confidence': 0.7
                })

        # Extract named entities (simple pattern matching)
        # Amount patterns
        amounts = re.findall(r'₹?[\d,]+(?:\.\d{2})?', text)
        for amount in amounts[:5]:  # Limit
            signals.append({
                'type': 'amount',
                'text': amount,
                'source_file': filename,
                'confidence': 0.8
            })

        # Date patterns
        dates = re.findall(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text)
        for date in dates[:5]:  # Limit
            signals.append({
                'type': 'date',
                'text': date,
                'source_file': filename,
                'confidence': 0.8
            })

    return signals


# ==================== PASS 2: CONTROLLED SEMANTIC TAGGING (LIMITED AI) ====================

def tag_signals_with_domains(signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    PASS 2: Use AI to tag signals with context domains.

    AI is used ONLY for tagging, never for inference.

    Args:
        signals: Raw signals from Pass 1

    Returns:
        Signals with domain tags added
    """
    print("   -> PASS 2: Controlled semantic tagging (AI)...")

    # Route by model name through llm_client (OpenAI / Anthropic / OpenRouter) so the
    # configured model + key are used and JSON fences are handled.
    model = os.getenv("AI_PRIMARY_MODEL") or os.getenv("AI_VALIDATION_MODEL", "gpt-4o-mini")

    # Batch signals for efficiency
    batch_size = 20
    tagged_signals = []

    for i in range(0, len(signals), batch_size):
        batch = signals[i:i+batch_size]

        # Build prompt
        signal_texts = [f"{j}. {s['text']}" for j, s in enumerate(batch)]
        signal_list = '\n'.join(signal_texts)

        prompt = f"""You are a context domain tagger. Tag each statement with one or more context domains from this list ONLY:

{', '.join(CONTEXT_DOMAINS)}

Do NOT infer meaning. Only tag based on explicit keywords.

STATEMENTS:
{signal_list}

Return JSON array with format:
[
  {{"statement_id": 0, "tags": ["APPROVAL_RULES"]}},
  {{"statement_id": 1, "tags": ["RISK_TOLERANCE", "EXCEPTIONS"]}}
]

Return ONLY valid JSON array, no other text."""

        try:
            result_text = llm_complete(
                model=model,
                system_prompt="You are a context domain tagger. Tag statements without inferring meaning.",
                user_prompt=prompt,
                temperature=0.0,
                json_mode=True,
            )

            # Wrap in object if it's an array (llm_client already stripped any fence)
            if result_text.strip().startswith('['):
                result_text = f'{{"tags": {result_text}}}'

            result = json.loads(result_text)
            tags_array = result.get('tags', [])

            # Apply tags to signals
            for tag_obj in tags_array:
                stmt_id = tag_obj.get('statement_id', 0)
                tags = tag_obj.get('tags', [])

                if stmt_id < len(batch):
                    batch[stmt_id]['domains'] = tags

        except Exception as e:
            print(f"      [WARNING] Tagging failed for batch: {e}")
            # Continue without tags
            for signal in batch:
                signal['domains'] = []

        tagged_signals.extend(batch)

    print(f"      [OK] Tagged {len(tagged_signals)} signals")
    return tagged_signals


# ==================== PASS 3: RULE CANDIDATE EXTRACTION ====================

def extract_rule_candidates(tagged_signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    PASS 3: Convert tagged statements into candidate constraints.

    Args:
        tagged_signals: Signals with domain tags from Pass 2

    Returns:
        List of rule candidates
    """
    print("   -> PASS 3: Rule candidate extraction...")

    candidates = []

    for signal in tagged_signals:
        text = signal.get('text', '')
        domains = signal.get('domains', [])
        source_file = signal.get('source_file', '')

        if not domains:
            continue

        # Simple rule extraction heuristics
        rule_candidate = {
            'domains': domains,
            'raw_text': text,
            'source_file': source_file,
            'structured_candidate': None,
            'confidence': 0.0
        }

        # Try to extract structured rule from text
        # Pattern: "X not required below Y"
        match = re.search(r'(.+?)\s+not required\s+(?:below|under|for)\s+(?:₹|Rs\.?|amounts?)\s*([\d,]+)', text, re.IGNORECASE)
        if match:
            what = match.group(1).strip()
            threshold = match.group(2).replace(',', '')
            rule_candidate['structured_candidate'] = {
                'type': 'threshold_exception',
                'subject': what,
                'condition': f'amount < {threshold}',
                'effect': f'{what}_not_required'
            }
            rule_candidate['confidence'] = 0.8

        # Pattern: "X required for Y"
        match = re.search(r'(.+?)\s+required\s+(?:for|when|if)\s+(.+)', text, re.IGNORECASE)
        if match:
            what = match.group(1).strip()
            condition = match.group(2).strip()
            rule_candidate['structured_candidate'] = {
                'type': 'requirement',
                'subject': what,
                'condition': condition,
                'effect': f'{what}_required'
            }
            rule_candidate['confidence'] = 0.75

        # Pattern: "Amount: X"
        match = re.search(r'(?:amount|threshold|limit).*?(?:₹|Rs\.?)\s*([\d,]+)', text, re.IGNORECASE)
        if match:
            amount_val = match.group(1).replace(',', '')
            rule_candidate['structured_candidate'] = {
                'type': 'threshold_value',
                'value': int(amount_val),
                'currency': 'INR'
            }
            rule_candidate['confidence'] = 0.7

        # Only include if we extracted something OR domains are interesting
        if rule_candidate['structured_candidate'] or 'APPROVAL_RULES' in domains or 'EXCEPTIONS' in domains:
            candidates.append(rule_candidate)

    print(f"      [OK] Extracted {len(candidates)} rule candidates")
    return candidates


# ==================== 5.7 CONFLICT DETECTION ====================

def detect_conflicts(rule_candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Detect conflicts in rule candidates.

    If two sources provide different values for the same thing, preserve as UNRESOLVED.

    Args:
        rule_candidates: Rule candidates from Pass 3

    Returns:
        List of detected conflicts
    """
    conflicts = []

    # Group by domain
    by_domain = {}
    for candidate in rule_candidates:
        for domain in candidate.get('domains', []):
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append(candidate)

    # Check for conflicts within each domain
    for domain, candidates in by_domain.items():
        # Look for threshold conflicts
        thresholds = [c for c in candidates if c.get('structured_candidate', {}).get('type') == 'threshold_value']

        if len(thresholds) > 1:
            values = [t['structured_candidate']['value'] for t in thresholds]
            if len(set(values)) > 1:  # Different values
                conflicts.append({
                    'conflict': f'{domain} threshold',
                    'sources': [
                        {
                            'value': t['structured_candidate']['value'],
                            'file': t['source_file']
                        }
                        for t in thresholds
                    ],
                    'resolution': 'UNRESOLVED'
                })

    return conflicts


# ==================== 5.6 CLIENT CONTEXT MODEL ASSEMBLY ====================

def assemble_context_model(rule_candidates: List[Dict[str, Any]], conflicts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Assemble final client context model from rule candidates.

    Args:
        rule_candidates: Rule candidates
        conflicts: Detected conflicts

    Returns:
        Client context model
    """
    print("   -> Assembling context model...")

    # Group by domain
    by_domain = {}
    for candidate in rule_candidates:
        for domain in candidate.get('domains', []):
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append(candidate)

    # Build model
    model = {
        'client_identity': {
            'name': 'UNKNOWN',  # Would extract from signals
            'jurisdiction': 'UNKNOWN'
        },
        'process_variations': by_domain.get('PROCESS_VARIATIONS', []),
        'approval_rules': by_domain.get('APPROVAL_RULES', []),
        'risk_profile': {
            'strictness': 'MEDIUM',  # Default
            'inferred_from': []
        },
        'explicit_exceptions': by_domain.get('EXCEPTIONS', []),
        'terminology_map': {},
        'timing_rules': by_domain.get('TIMING_RULES', []),
        'operations': by_domain.get('OPERATIONS', [])
    }

    # Infer risk profile from exceptions and approval rules
    exception_count = len(model['explicit_exceptions'])
    if exception_count > 5:
        model['risk_profile']['strictness'] = 'LOW'
        model['risk_profile']['inferred_from'].append(f'{exception_count} exceptions found')
    elif exception_count == 0:
        model['risk_profile']['strictness'] = 'HIGH'
        model['risk_profile']['inferred_from'].append('No exceptions found')

    return model


# ==================== 5.8 CONTEXT ↔ WORKFLOW INTERACTION ====================

def map_context_to_workflow(context_model: Dict[str, Any], workflow_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Map client context to workflow steps.

    Args:
        context_model: Client context model
        workflow_data: Workflow data from Section 4

    Returns:
        List of workflow interaction mappings
    """
    print("   -> Mapping context to workflow...")

    mappings = []

    # Get declared workflows
    declared_workflows = workflow_data.get('declared_workflows', [])

    for workflow in declared_workflows:
        steps = workflow.get('steps', [])

        for step in steps:
            step_text = step.get('raw_text', '').lower()

            # Check if any approval rules apply to this step
            for approval_rule in context_model.get('approval_rules', []):
                rule_text = approval_rule.get('raw_text', '').lower()

                # Simple keyword matching
                if 'approval' in step_text and 'approval' in rule_text:
                    structured = approval_rule.get('structured_candidate', {})

                    if structured:
                        mappings.append({
                            'step_id': step['step_id'],
                            'applicability': 'CONDITIONAL',
                            'condition': structured.get('condition', ''),
                            'source': 'client_context',
                            'confidence': approval_rule.get('confidence', 0.5)
                        })

    print(f"      [OK] Created {len(mappings)} workflow mappings")
    return mappings


# ==================== 5.9 CONTEXT CONFIDENCE SCORING ====================

def calculate_context_confidence(context_model: Dict[str, Any], rule_candidates: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculate confidence scores for each domain in context model.

    Args:
        context_model: Client context model
        rule_candidates: Rule candidates

    Returns:
        Confidence scores by domain
    """
    confidence = {}

    # Calculate confidence per domain
    for domain in CONTEXT_DOMAINS:
        domain_candidates = [c for c in rule_candidates if domain in c.get('domains', [])]

        if not domain_candidates:
            confidence[f'{domain.lower()}_confidence'] = 0.0
        else:
            avg_conf = sum(c.get('confidence', 0) for c in domain_candidates) / len(domain_candidates)
            confidence[f'{domain.lower()}_confidence'] = round(avg_conf, 2)

    # Overall confidence
    all_confidences = [v for v in confidence.values() if v > 0]
    confidence['overall_confidence'] = round(sum(all_confidences) / len(all_confidences), 2) if all_confidences else 0.0

    return confidence


# ==================== 5.11 SECTION 5 ORCHESTRATOR ====================

class Section5ClientContext:
    """
    Client Context Interpretation Engine - Section 5 orchestrator.

    Takes Section 2 manifest, Section 3 normalized inputs, Section 4 workflow,
    produces client context model.
    """

    def __init__(self, section2_manifest: Dict[str, Any], section3_output: Dict[str, Any],
                 section4_output: Dict[str, Any]):
        """
        Args:
            section2_manifest: Output from Section 2
            section3_output: Output from Section 3
            section4_output: Output from Section 4
        """
        self.manifest = section2_manifest
        self.normalized_inputs = section3_output
        self.workflow_data = section4_output
        self.warnings = []

    def interpret(self) -> Dict[str, Any]:
        """
        Execute full client context interpretation pipeline.

        Returns:
            {
                "client_context_model": {...},
                "context_confidence": {...},
                "context_warnings": [...]
            }
        """
        print("=" * 80)
        print("SECTION 5: CLIENT CONTEXT INTERPRETATION START")
        print("=" * 80)

        # Get client context files
        client_files = self.manifest.get('client_context_files', [])

        if not client_files:
            print("\n[WARNING] No client context files found - using defaults")
            return self._default_context()

        print(f"\n[1/8] Client document ingestion ({len(client_files)} files)...")

        # PASS 1: Raw signal extraction (NO AI)
        print("\n[2/8] PASS 1: Raw signal extraction (NO AI)...")
        raw_signals = extract_raw_signals(client_files)
        print(f"   [OK] Extracted {len(raw_signals)} raw signals")

        # PASS 2: Controlled semantic tagging (LIMITED AI)
        print("\n[3/8] PASS 2: Controlled semantic tagging...")
        tagged_signals = tag_signals_with_domains(raw_signals)

        # PASS 3: Rule candidate extraction
        print("\n[4/8] PASS 3: Rule candidate extraction...")
        rule_candidates = extract_rule_candidates(tagged_signals)

        # Conflict detection
        print("\n[5/8] Conflict detection...")
        conflicts = detect_conflicts(rule_candidates)
        if conflicts:
            print(f"   [WARNING] Found {len(conflicts)} conflicts")
            for conflict in conflicts:
                self.warnings.append(f"Conflict: {conflict['conflict']}")
        else:
            print("   [OK] No conflicts detected")

        # Context model assembly
        print("\n[6/8] Context model assembly...")
        context_model = assemble_context_model(rule_candidates, conflicts)

        # Workflow interaction mapping
        print("\n[7/8] Workflow interaction mapping...")
        workflow_mappings = map_context_to_workflow(context_model, self.workflow_data)

        # Add mappings to model
        context_model['workflow_interactions'] = workflow_mappings

        # Confidence scoring
        print("\n[8/8] Confidence scoring...")
        context_confidence = calculate_context_confidence(context_model, rule_candidates)

        # Check for low confidence
        for key, value in context_confidence.items():
            if value < 0.5 and value > 0:
                self.warnings.append(f"Low confidence: {key} = {value:.2f}")

        print("\n" + "=" * 80)
        print("SECTION 5: CLIENT CONTEXT INTERPRETATION COMPLETE")
        print("=" * 80)

        return {
            'client_context_model': context_model,
            'context_confidence': context_confidence,
            'context_warnings': self.warnings,
            'conflicts': conflicts
        }

    def _default_context(self) -> Dict[str, Any]:
        """Return default context when no client files available"""
        return {
            'client_context_model': {
                'client_identity': {'name': 'UNKNOWN', 'jurisdiction': 'UNKNOWN'},
                'process_variations': [],
                'approval_rules': [],
                'risk_profile': {'strictness': 'MEDIUM', 'inferred_from': ['No client data']},
                'explicit_exceptions': [],
                'terminology_map': {},
                'workflow_interactions': []
            },
            'context_confidence': {'overall_confidence': 0.0},
            'context_warnings': ['No client context files found - using defaults'],
            'conflicts': []
        }


# ==================== CONVENIENCE FUNCTION ====================

def interpret_client_context(section2_manifest: Dict[str, Any], section3_output: Dict[str, Any],
                             section4_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function for Section 5 client context interpretation.

    Args:
        section2_manifest: Output from Section 2
        section3_output: Output from Section 3
        section4_output: Output from Section 4

    Returns:
        Client context interpretation output
    """
    interpreter = Section5ClientContext(section2_manifest, section3_output, section4_output)
    return interpreter.interpret()
