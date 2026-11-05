"""
LexSecure India Pro - Enterprise Legal & Regulatory Intelligence Web Application
Django Views & HTMX API Endpoints
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, FileResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils import timezone
from django.conf import settings

from compliance.models import (
    Organization, Entity, Department, User, AccessMatrixRule,
    Playbook, PlaybookRule, Document, DocumentClause,
    RegulatoryUpdate, ImpactAssessment, ComplianceTask,
    TaskEvidence, StatutoryCalendarEvent, TamperAuditLog
)
from services.document_parser import DocumentParser
from services.legal_ai_service import LegalAIService
from services.audit_service import AuditDefenseService


# =============================================================================
# HELPER FUNCTIONS & SESSION CONTEXT
# =============================================================================
def get_session_context(request):
    """
    Extracts or initializes the current active operating entity and corporate user.
    """
    org = Organization.objects.first()
    if not org:
        from django.core.management import call_command
        call_command('seed_enterprise_data')
        org = Organization.objects.first()

    entities = Entity.objects.filter(organization=org)
    users = User.objects.filter(organization=org, is_active=True)

    # Active Entity
    entity_id = request.session.get('current_entity_id')
    if not entity_id or not entities.filter(id=entity_id).exists():
        first_ent = entities.first()
        entity_id = first_ent.id if first_ent else 1
        request.session['current_entity_id'] = entity_id

    current_entity = entities.filter(id=entity_id).first()

    # Active User
    user_id = request.session.get('current_user_id')
    if not user_id or not users.filter(id=user_id).exists():
        first_usr = users.first()
        user_id = first_usr.id if first_usr else 1
        request.session['current_user_id'] = user_id

    current_user = users.filter(id=user_id).first()

    return {
        'org': org,
        'entities': entities,
        'current_entity': current_entity,
        'current_entity_id': entity_id,
        'users': users,
        'current_user': current_user,
        'current_user_id': user_id,
    }


def log_audit_trail(org, user, event_type, target_model, target_id, details_dict, request=None):
    """
    Appends a cryptographically chained SHA-256 event to TamperAuditLog.
    """
    ip = '127.0.0.1'
    if request:
        ip = request.META.get('REMOTE_ADDR', '127.0.0.1')

    actor_id = user.id if user else 1
    actor_name = user.full_name if user else 'System Admin'

    return TamperAuditLog.objects.create(
        organization=org,
        actor_id=actor_id,
        actor_name=actor_name,
        event_type=event_type,
        target_model=target_model,
        target_id=target_id,
        details_json=json.dumps(details_dict),
        ip_address=ip
    )


# =============================================================================
# 1. EXECUTIVE COMMAND CENTER / DASHBOARD
# =============================================================================
def dashboard_view(request):
    ctx = get_session_context(request)
    ent_id = ctx['current_entity_id']
    ent = ctx['current_entity']

    # 1. KPI Metrics
    entity_docs = Document.objects.filter(entity=ent)
    doc_count = entity_docs.count()
    if doc_count > 0:
        health_score = int(sum(d.overall_health_score for d in entity_docs) / doc_count)
    else:
        health_score = 92

    dealbreakers = DocumentClause.objects.filter(
        document__entity=ent, risk_tier='HIGH', is_resolved=False
    ).count()

    now = datetime.now().date()
    cal_events = StatutoryCalendarEvent.objects.filter(entity=ent)
    overdue_count = sum(1 for e in cal_events if e.due_date < now)
    approaching_count = sum(1 for e in cal_events if 0 <= (e.due_date - now).days <= 30)

    # Labour & FEMA compliance index
    fema_labour_scores = [d.labour_fema_score for d in entity_docs] or [88]
    fema_labour_index = int(sum(fema_labour_scores) / len(fema_labour_scores))

    # 2. Department Accountability Heatmap
    departments = Department.objects.filter(entity=ent)
    dept_heatmap = []
    for d in departments:
        tasks = ComplianceTask.objects.filter(department=d)
        total = tasks.count()
        comp = tasks.filter(status='COMPLETED').count()
        rate = int((comp / total) * 100) if total > 0 else 85
        dept_heatmap.append({
            'name': d.get_name_display(),
            'code': d.name,
            'total_tasks': total,
            'completed_tasks': comp,
            'completion_rate': rate,
        })

    # 3. Live Indian Regulatory Watchlist
    recent_circulars = RegulatoryUpdate.objects.order_by('-official_date')[:5]

    # 4. Upcoming Statutory Deadlines
    upcoming_events = []
    for ev in cal_events.order_by('due_date'):
        days_left = (ev.due_date - now).days
        upcoming_events.append({
            'event': ev,
            'days_left': days_left,
            'is_overdue': days_left < 0,
            'is_urgent': 0 <= days_left <= 14,
        })

    ctx.update({
        'health_score': health_score,
        'dealbreakers': dealbreakers,
        'overdue_count': overdue_count,
        'approaching_count': approaching_count,
        'fema_labour_index': fema_labour_index,
        'dept_heatmap': dept_heatmap,
        'recent_circulars': recent_circulars,
        'upcoming_events': upcoming_events,
    })
    return render(request, 'compliance/dashboard.html', ctx)


# =============================================================================
# 2. PILLAR 1: CONTRACT / DOCUMENT REVIEW & STORAGE WORKSPACE
# =============================================================================
def contracts_view(request):
    ctx = get_session_context(request)
    ent = ctx['current_entity']

    # Stored Documents for entity
    stored_docs = Document.objects.filter(entity=ent).order_by('-id')

    # Selected document to review
    doc_id = request.GET.get('doc_id')
    active_doc = None
    if doc_id:
        active_doc = Document.objects.filter(id=doc_id).first()
    if not active_doc:
        active_doc = stored_docs.first() or Document.objects.first()

    clauses = []
    if active_doc:
        clauses = DocumentClause.objects.filter(document=active_doc).order_by('id')

    ctx.update({
        'stored_docs': stored_docs,
        'active_doc': active_doc,
        'clauses': clauses,
        'contract_types': Playbook.CONTRACT_TYPE_CHOICES,
    })
    return render(request, 'compliance/contracts.html', ctx)


@require_http_methods(["POST"])
def upload_contract(request):
    ctx = get_session_context(request)
    org = ctx['org']
    user = ctx['current_user']

    uploaded_file = request.FILES.get('contract_file')
    entity_id = request.POST.get('entity_id') or ctx['current_entity_id']
    contract_type = request.POST.get('contract_type', 'MSA')
    entity = get_object_or_404(Entity, id=entity_id)

    if not uploaded_file:
        messages.error(request, "Please select a valid PDF, DOCX, or TXT file to upload.")
        return redirect('contracts')

    filename = uploaded_file.name
    # Save file to media/contracts
    upload_dir = Path(settings.MEDIA_ROOT) / 'contracts'
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / filename

    with open(file_path, 'wb+') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)

    # Parse Document Text
    parser = DocumentParser()
    try:
        parsed = parser.parse_file(str(file_path))
        doc_text = parsed.get('text', '')
        ocr_applied = parsed.get('ocr_applied', False)
    except Exception as e:
        messages.error(request, f"File parsing error: {str(e)}")
        return redirect('contracts')

    # AI & Statutory Heuristic Scanning
    ai_service = LegalAIService()
    analysis = ai_service.analyze_contract_against_playbook(doc_text)

    # Create Document record
    doc = Document.objects.create(
        entity=entity,
        uploaded_by=user,
        file=f"contracts/{filename}",
        original_filename=filename,
        doc_type=contract_type,
        status='REVIEWED',
        overall_health_score=analysis.get('overall_health_score', 75),
        liability_score=analysis.get('liability_score', 70),
        statutory_score=analysis.get('statutory_score', 70),
        labour_fema_score=analysis.get('labour_fema_score', 80),
        ocr_applied=ocr_applied,
        raw_content=doc_text
    )

    # Save Clauses
    for c in analysis.get('clauses', []):
        DocumentClause.objects.create(
            document=doc,
            page_number=c.get('page_number', 1),
            clause_type=c.get('clause_type', 'GENERAL_TERM'),
            raw_text=c.get('raw_text', ''),
            risk_tier=c.get('risk_tier', 'CAUTION'),
            flag_reason=c.get('flag_reason', ''),
            indian_law_violation=c.get('indian_law_violation', ''),
            suggested_redline=c.get('suggested_redline', ''),
            is_resolved=False
        )

    # Chained SHA-256 Audit Trail
    log_audit_trail(
        org=org,
        user=user,
        event_type="CONTRACT_UPLOAD",
        target_model="Document",
        target_id=doc.id,
        details_dict={
            "filename": filename,
            "entity_id": entity.id,
            "score": doc.overall_health_score,
            "clauses_detected": len(analysis.get('clauses', []))
        },
        request=request
    )

    # Set active entity in session to match uploaded doc
    request.session['current_entity_id'] = entity.id
    messages.success(request, f"Contract '{filename}' uploaded and analyzed successfully against Indian Statutory Playbook!")
    return redirect(f"/contracts/?doc_id={doc.id}")


@require_http_methods(["POST"])
def resolve_clause(request, clause_id):
    """
    HTMX Endpoint: 1-Click Accept Redline.
    Updates clause, recomputes health score, logs audit event, and returns refreshed HTML partial.
    """
    ctx = get_session_context(request)
    clause = get_object_or_404(DocumentClause, id=clause_id)
    doc = clause.document

    clause.is_resolved = True
    clause.save()

    # Recalculate health score
    all_clauses = DocumentClause.objects.filter(document=doc)
    unresolved_high = all_clauses.filter(risk_tier='HIGH', is_resolved=False).count()
    unresolved_caution = all_clauses.filter(risk_tier='CAUTION', is_resolved=False).count()
    new_score = min(100, 100 - (unresolved_high * 18 + unresolved_caution * 8))

    doc.overall_health_score = new_score
    doc.save()

    # Cryptographic Audit Log
    log_audit_trail(
        org=ctx['org'],
        user=ctx['current_user'],
        event_type="REDLINE_ACCEPTED",
        target_model="DocumentClause",
        target_id=clause.id,
        details_dict={
            "clause_type": clause.clause_type,
            "document_id": doc.id,
            "new_score": new_score
        },
        request=request
    )

    # Return HTMX response with clause card and trigger header
    response = render(request, 'compliance/partials/clause_card.html', {
        'clause': clause,
        'doc': doc,
    })
    response['HX-Trigger'] = json.dumps({
        'scoreUpdated': {'score': new_score},
        'showToast': f"Redline for {clause.clause_type} accepted! Health Score: {new_score}%"
    })
    return response


@require_http_methods(["POST"])
def reassign_document_entity(request, doc_id):
    """
    Reassigns a stored document to a different operating entity.
    """
    ctx = get_session_context(request)
    doc = get_object_or_404(Document, id=doc_id)
    new_entity_id = request.POST.get('new_entity_id')
    new_entity = get_object_or_404(Entity, id=new_entity_id)

    old_ent_name = doc.entity.legal_name
    doc.entity = new_entity
    doc.save()

    log_audit_trail(
        org=ctx['org'],
        user=ctx['current_user'],
        event_type="DOCUMENT_REASSIGNED",
        target_model="Document",
        target_id=doc.id,
        details_dict={
            "document_id": doc.id,
            "from_entity": old_ent_name,
            "to_entity": new_entity.legal_name
        },
        request=request
    )

    messages.success(request, f"Document '{doc.original_filename}' successfully re-assigned to {new_entity.legal_name}.")
    return redirect('contracts')


def download_reviewed_document(request, doc_id):
    """
    Exports a publication-grade HTML report of the reviewed document with colored statutory highlights.
    """
    doc = get_object_or_404(Document, id=doc_id)
    clauses = DocumentClause.objects.filter(document=doc).order_by('id')

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>LexSecure India Pro - Statutory Review Report: {doc.original_filename}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #0F172A; color: #F8FAFC; padding: 30px; line-height: 1.6; }}
        .header {{ border-bottom: 2px solid #0D9488; padding-bottom: 14px; margin-bottom: 24px; }}
        .title {{ font-size: 20px; font-weight: bold; color: #10B981; margin: 0; }}
        .subtitle {{ font-size: 12px; color: #94A3B8; margin-top: 5px; }}
        .score-bar {{ background-color: #1E293B; border: 1px solid #334155; border-radius: 8px; padding: 14px 20px; margin-bottom: 25px; }}
        .clause-box {{ border-radius: 6px; padding: 14px 18px; margin-bottom: 16px; border: 1px solid #334155; }}
        .high-risk {{ background: rgba(239, 68, 68, 0.15); border-left: 6px solid #EF4444; border-color: rgba(239, 68, 68, 0.4); }}
        .caution-risk {{ background: rgba(245, 158, 11, 0.15); border-left: 6px solid #F59E0B; border-color: rgba(245, 158, 11, 0.4); }}
        .compliant-risk {{ background: rgba(16, 185, 129, 0.15); border-left: 6px solid #10B981; border-color: rgba(16, 185, 129, 0.4); }}
        .badge {{ font-size: 11px; font-weight: bold; padding: 3px 8px; border-radius: 4px; display: inline-block; }}
        .redline-box {{ background-color: rgba(16, 185, 129, 0.1); border: 1px dashed #10B981; padding: 10px 14px; border-radius: 6px; margin-top: 10px; font-size: 12.5px; color: #6EE7B7; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 13px; }}
        th, td {{ border: 1px solid #334155; padding: 10px; text-align: left; }}
        th {{ background-color: #1E293B; color: #10B981; }}
        tr:nth-child(even) {{ background-color: rgba(30, 41, 59, 0.5); }}
    </style>
</head>
<body>
    <div class="header">
        <div class="title">LEXSECURE INDIA PRO — STATUTORY CONTRACT REVIEW & AUDIT REPORT</div>
        <div class="subtitle">Entity: {doc.entity.legal_name} | Jurisdiction: India | Exported on {datetime.now().strftime('%B %d, %Y %I:%M %p')}</div>
    </div>
    <div class="score-bar">
        <b>Document:</b> {doc.original_filename} &nbsp;|&nbsp;
        <b>Overall Health Score:</b> <span style="color: {'#10B981' if doc.overall_health_score >= 80 else '#EF4444'}; font-weight: bold;">{doc.overall_health_score}%</span> &nbsp;|&nbsp;
        <b>Liability Score:</b> {doc.liability_score}% &nbsp;|&nbsp;
        <b>Statutory Alignment:</b> {doc.statutory_score}%
    </div>
    <h3>1. Highlighted Clauses & Indian Statutory Infractions</h3>
"""
    for c in clauses:
        css = "compliant-risk" if c.is_resolved or c.risk_tier == 'COMPLIANT' else ("high-risk" if c.risk_tier == 'HIGH' else "caution-risk")
        badge_color = "#10B981" if c.is_resolved or c.risk_tier == 'COMPLIANT' else ("#EF4444" if c.risk_tier == 'HIGH' else "#F59E0B")
        badge_text = "✔ COMPLIANT / RESOLVED" if c.is_resolved else f"[{c.risk_tier}] {c.clause_type}"

        html += f"""
    <div class="clause-box {css}">
        <span class="badge" style="background-color: {badge_color}; color: white;">{badge_text}</span>
        <div style="margin-top: 8px; font-size: 13px;"><b>Statutory Assessment:</b> {c.indian_law_violation or 'Aligned with Indian Statutory Playbook.'}</div>
        <div style="margin-top: 8px; font-size: 13px; color: #CBD5E1;"><b>Contract Provision:</b><br/>{c.raw_text}</div>
        {f'<div class="redline-box"><b>Recommended Playbook Redline:</b><br/>{c.suggested_redline}</div>' if c.suggested_redline else ''}
    </div>
"""

    html += f"""
    <h3 style="margin-top: 30px;">2. Complete Statutory Compliance Schedule</h3>
    <table>
        <tr>
            <th>Clause Type</th>
            <th>Risk Tier</th>
            <th>Statutory Citation / Infraction</th>
            <th>Status</th>
        </tr>
"""
    for c in clauses:
        html += f"""
        <tr>
            <td><b>{c.clause_type}</b></td>
            <td><span class="badge" style="background-color: {'#EF4444' if c.risk_tier == 'HIGH' else ('#F59E0B' if c.risk_tier == 'CAUTION' else '#10B981')}; color: white;">{c.risk_tier}</span></td>
            <td>{c.indian_law_violation or 'Compliant'}</td>
            <td>{'Resolved' if c.is_resolved else 'Pending Action'}</td>
        </tr>
"""
    html += """
    </table>
</body>
</html>"""

    response = HttpResponse(html, content_type='text/html')
    response['Content-Disposition'] = f'attachment; filename="LexSecure_Review_{doc.original_filename}.html"'
    return response


# =============================================================================
# 3. PILLAR 2: REGULATORY INTELLIGENCE GAZETTE & DISPATCH
# =============================================================================
def regulatory_view(request):
    ctx = get_session_context(request)
    statutory_body = request.GET.get('body')
    severity = request.GET.get('severity')

    circulars = RegulatoryUpdate.objects.all().order_by('-official_date')
    if statutory_body:
        circulars = circulars.filter(statutory_body=statutory_body)
    if severity:
        circulars = circulars.filter(severity=severity)

    ctx.update({
        'circulars': circulars,
        'bodies': RegulatoryUpdate.STATUTORY_BODY_CHOICES,
        'severities': RegulatoryUpdate.SEVERITY_CHOICES,
        'selected_body': statutory_body,
        'selected_severity': severity,
    })
    return render(request, 'compliance/regulatory.html', ctx)


def generate_impact_assessment(request, update_id):
    """
    HTMX Endpoint: Generates AI Impact Assessment for circular.
    """
    circ = get_object_or_404(RegulatoryUpdate, id=update_id)
    ai_service = LegalAIService()
    assessment = ai_service.generate_impact_assessment(circ.raw_text, circ.statutory_body)

    return render(request, 'compliance/partials/impact_modal.html', {
        'circ': circ,
        'assessment': assessment,
    })


@require_http_methods(["POST"])
def dispatch_impact_assessment(request, update_id):
    """
    Dispatches tasks from impact assessment to department leads.
    """
    ctx = get_session_context(request)
    circ = get_object_or_404(RegulatoryUpdate, id=update_id)
    user = ctx['current_user']
    ent = ctx['current_entity']

    summary = request.POST.get('executive_summary', 'Automated AI Impact Assessment')
    affected_depts = request.POST.get('affected_departments', 'LEGAL, INFOSEC_TECH')
    deadline_str = request.POST.get('statutory_deadline')
    deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else (datetime.now().date() + timedelta(days=30))

    ia = ImpactAssessment.objects.create(
        regulatory_update=circ,
        approved_by=user,
        status='DISPATCHED',
        executive_summary=summary,
        affected_departments=affected_depts,
        statutory_deadline=deadline
    )

    # Auto create tasks for departments
    dept_map = {d.name: d for d in Department.objects.filter(entity=ent)}
    depts_to_notify = [d.strip() for d in affected_depts.split(',') if d.strip()]

    tasks_created = 0
    now = datetime.now().date()
    for d_name in depts_to_notify:
        dept_obj = dept_map.get(d_name) or Department.objects.filter(entity=ent, name='LEGAL').first()
        if dept_obj:
            ComplianceTask.objects.create(
                impact_assessment=ia,
                department=dept_obj,
                assigned_to=user,
                title=f"Regulatory Compliance Action: {circ.circular_number}",
                description=f"Implement statutory requirements from {circ.statutory_body} circular '{circ.title}'. Summary: {summary[:200]}...",
                deadline=now + timedelta(days=14),
                priority='HIGH',
                status='PENDING'
            )
            tasks_created += 1

    log_audit_trail(
        org=ctx['org'],
        user=user,
        event_type="IMPACT_ASSESSMENT_DISPATCHED",
        target_model="ImpactAssessment",
        target_id=ia.id,
        details_dict={
            "circular_number": circ.circular_number,
            "tasks_dispatched": tasks_created
        },
        request=request
    )

    messages.success(request, f"Successfully dispatched {tasks_created} statutory compliance tasks to department queues!")
    return redirect('regulatory')


# =============================================================================
# 4. PILLAR 3: DEPARTMENT COMPLIANCE TASKS & EVIDENCE
# =============================================================================
def tasks_view(request):
    ctx = get_session_context(request)
    ent = ctx['current_entity']

    dept_filter = request.GET.get('dept')
    status_filter = request.GET.get('status')

    tasks = ComplianceTask.objects.filter(department__entity=ent).order_by('deadline')
    if dept_filter:
        tasks = tasks.filter(department__name=dept_filter)
    if status_filter:
        tasks = tasks.filter(status=status_filter)

    ctx.update({
        'tasks': tasks,
        'departments': Department.objects.filter(entity=ent),
        'statuses': ComplianceTask.STATUS_CHOICES,
        'selected_dept': dept_filter,
        'selected_status': status_filter,
    })
    return render(request, 'compliance/tasks.html', ctx)


@require_http_methods(["POST"])
def toggle_task_status(request, task_id):
    """
    HTMX: Cycles task status: PENDING -> IN_PROGRESS -> COMPLETED
    """
    ctx = get_session_context(request)
    task = get_object_or_404(ComplianceTask, id=task_id)

    order = ['PENDING', 'IN_PROGRESS', 'COMPLETED']
    cur_idx = order.index(task.status) if task.status in order else 0
    next_status = order[(cur_idx + 1) % len(order)]
    task.status = next_status
    task.save()

    log_audit_trail(
        org=ctx['org'],
        user=ctx['current_user'],
        event_type="TASK_STATUS_UPDATED",
        target_model="ComplianceTask",
        target_id=task.id,
        details_dict={"new_status": next_status, "title": task.title},
        request=request
    )

    return render(request, 'compliance/partials/task_row.html', {'task': task})


@require_http_methods(["POST"])
def upload_task_evidence(request, task_id):
    """
    Uploads evidence file and notes for a compliance task.
    """
    ctx = get_session_context(request)
    task = get_object_or_404(ComplianceTask, id=task_id)
    notes = request.POST.get('notes', '')
    evidence_file = request.FILES.get('evidence_file')

    filename = ""
    if evidence_file:
        filename = evidence_file.name
        upload_dir = Path(settings.MEDIA_ROOT) / 'evidence'
        upload_dir.mkdir(parents=True, exist_ok=True)
        with open(upload_dir / filename, 'wb+') as dest:
            for chunk in evidence_file.chunks():
                dest.write(chunk)

    TaskEvidence.objects.create(
        task=task,
        uploaded_by=ctx['current_user'],
        evidence_file=filename,
        notes=notes
    )

    task.status = 'COMPLETED'
    task.save()

    log_audit_trail(
        org=ctx['org'],
        user=ctx['current_user'],
        event_type="EVIDENCE_UPLOADED",
        target_model="ComplianceTask",
        target_id=task.id,
        details_dict={"notes": notes, "file": filename},
        request=request
    )

    messages.success(request, f"Evidence uploaded for '{task.title}'. Task marked COMPLIANT.")
    return redirect('tasks')


# =============================================================================
# 5. PILLAR 4: STATUTORY COMPLIANCE CALENDAR
# =============================================================================
def calendar_view(request):
    ctx = get_session_context(request)
    ent = ctx['current_entity']

    now = datetime.now().date()
    events = StatutoryCalendarEvent.objects.filter(entity=ent).order_by('due_date')

    event_list = []
    for ev in events:
        days_left = (ev.due_date - now).days
        event_list.append({
            'ev': ev,
            'days_left': days_left,
            'is_overdue': days_left < 0,
            'is_urgent': 0 <= days_left <= 14,
        })

    ctx.update({
        'calendar_events': event_list,
    })
    return render(request, 'compliance/calendar.html', ctx)


# =============================================================================
# 6. PILLAR 5: CRYPTOGRAPHIC AUDIT TRAIL & DOSSIER
# =============================================================================
def audit_view(request):
    ctx = get_session_context(request)
    org = ctx['org']

    logs = TamperAuditLog.objects.filter(organization=org).order_by('-id')

    # Verify SHA-256 chain mathematical integrity
    all_logs_asc = list(TamperAuditLog.objects.filter(organization=org).order_by('id'))
    is_intact = True
    broken_id = None
    expected_prev = '0' * 64

    import hashlib
    for entry in all_logs_asc:
        if entry.prev_hash != expected_prev:
            is_intact = False
            broken_id = entry.id
            break

        now_str = entry.timestamp.isoformat() if entry.timestamp else ""
        raw_payload = f"{entry.prev_hash}|{now_str}|{entry.actor_id}|{entry.actor_name}|{entry.event_type}|{entry.target_model}|{entry.target_id}|{entry.details_json}"
        calc_hash = hashlib.sha256(raw_payload.encode('utf-8')).hexdigest()
        if calc_hash != entry.current_hash:
            is_intact = False
            broken_id = entry.id
            break
        expected_prev = entry.current_hash

    latest_hash = all_logs_asc[-1].current_hash if all_logs_asc else ('0' * 64)

    ctx.update({
        'logs': logs,
        'is_intact': is_intact,
        'broken_id': broken_id,
        'latest_hash': latest_hash,
        'total_logs': len(all_logs_asc),
    })
    return render(request, 'compliance/audit.html', ctx)


def download_audit_dossier(request):
    """
    Exports a comprehensive PDF Defense Dossier with cryptographic integrity certificates.
    """
    ctx = get_session_context(request)
    org = ctx['org']

    output_dir = Path(settings.MEDIA_ROOT) / 'dossiers'
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / f"LexSecure_India_Pro_Defense_Dossier_{org.id}.pdf"

    service = AuditDefenseService()
    try:
        service.generate_defense_dossier_pdf(str(pdf_path), org.id)
        return FileResponse(open(pdf_path, 'rb'), as_attachment=True, filename=f"LexSecure_Defense_Dossier_{org.name.replace(' ', '_')}.pdf")
    except Exception as e:
        messages.error(request, f"Dossier generation failed: {e}")
        return redirect('audit')


# =============================================================================
# 7. GOVERNANCE & RBAC ACCESS MATRIX
# =============================================================================
def governance_view(request):
    ctx = get_session_context(request)
    org = ctx['org']

    entities = Entity.objects.filter(organization=org)
    users = User.objects.filter(organization=org)
    matrix_rules = AccessMatrixRule.objects.all().order_by('role', 'resource')

    ctx.update({
        'entities': entities,
        'users': users,
        'matrix_rules': matrix_rules,
        'roles': User.ROLE_CHOICES,
        'entity_types': Entity.ENTITY_CHOICES,
    })
    return render(request, 'compliance/governance.html', ctx)


@require_http_methods(["POST"])
def add_entity(request):
    ctx = get_session_context(request)
    org = ctx['org']
    legal_name = request.POST.get('legal_name')
    entity_type = request.POST.get('entity_type', 'PVT_LTD')
    registered_state = request.POST.get('registered_state')

    if not legal_name or not registered_state:
        messages.error(request, "Entity name and registered state are required.")
        return redirect('governance')

    entity = Entity.objects.create(
        organization=org,
        legal_name=legal_name,
        entity_type=entity_type,
        registered_state=registered_state
    )

    # Provision standard 5 departments
    depts = ['LEGAL', 'HR_LABOUR', 'FINANCE_TAX', 'INFOSEC_TECH', 'OPERATIONS']
    for d in depts:
        Department.objects.create(entity=entity, name=d)

    log_audit_trail(
        org=org,
        user=ctx['current_user'],
        event_type="ENTITY_CREATED",
        target_model="Entity",
        target_id=entity.id,
        details_dict={"legal_name": legal_name, "state": registered_state},
        request=request
    )

    messages.success(request, f"Operating entity '{legal_name}' created with 5 provisioned departments!")
    return redirect('governance')


@require_http_methods(["POST"])
def delete_entity(request, entity_id):
    ctx = get_session_context(request)
    org = ctx['org']
    if Entity.objects.filter(organization=org).count() <= 1:
        messages.error(request, "Cannot delete the sole operating entity of the organization.")
        return redirect('governance')

    entity = get_object_or_404(Entity, id=entity_id, organization=org)
    name = entity.legal_name
    entity.delete()

    log_audit_trail(
        org=org,
        user=ctx['current_user'],
        event_type="ENTITY_DELETED",
        target_model="Entity",
        target_id=entity_id,
        details_dict={"deleted_name": name},
        request=request
    )

    # If current entity was deleted, reset session
    if request.session.get('current_entity_id') == entity_id:
        request.session['current_entity_id'] = Entity.objects.filter(organization=org).first().id

    messages.success(request, f"Operating entity '{name}' removed.")
    return redirect('governance')


@require_http_methods(["POST"])
def add_user(request):
    ctx = get_session_context(request)
    org = ctx['org']
    full_name = request.POST.get('full_name')
    email = request.POST.get('email')
    role = request.POST.get('role', 'DEPT_LEAD')
    pin = request.POST.get('pin', '1234')
    dept_id = request.POST.get('department_id')

    if not full_name or not email:
        messages.error(request, "Name and email are required.")
        return redirect('governance')

    dept = Department.objects.filter(id=dept_id).first() if dept_id else None

    user = User.objects.create(
        organization=org,
        full_name=full_name,
        email=email,
        role=role,
        department=dept,
        pin=pin,
        is_active=True
    )

    log_audit_trail(
        org=org,
        user=ctx['current_user'],
        event_type="USER_CREATED",
        target_model="User",
        target_id=user.id,
        details_dict={"email": email, "role": role},
        request=request
    )

    messages.success(request, f"Corporate user '{full_name}' added under role '{user.get_role_display()}'.")
    return redirect('governance')


@require_http_methods(["POST"])
def delete_user(request, user_id):
    ctx = get_session_context(request)
    org = ctx['org']
    if User.objects.filter(organization=org).count() <= 1:
        messages.error(request, "Cannot delete the sole administrative user.")
        return redirect('governance')

    user = get_object_or_404(User, id=user_id, organization=org)
    name = user.full_name
    user.delete()

    log_audit_trail(
        org=org,
        user=ctx['current_user'],
        event_type="USER_DELETED",
        target_model="User",
        target_id=user_id,
        details_dict={"deleted_user": name},
        request=request
    )

    if request.session.get('current_user_id') == user_id:
        request.session['current_user_id'] = User.objects.filter(organization=org).first().id

    messages.success(request, f"Corporate user '{name}' removed.")
    return redirect('governance')


# =============================================================================
# 8. SWITCH USER & SWITCH ENTITY SESSION HANDLERS
# =============================================================================
@require_http_methods(["POST"])
def switch_active_entity(request):
    entity_id = request.POST.get('entity_id')
    if entity_id:
        request.session['current_entity_id'] = int(entity_id)
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))


@require_http_methods(["POST"])
def switch_active_user(request):
    user_id = request.POST.get('user_id')
    pin = request.POST.get('pin', '')
    user = User.objects.filter(id=user_id).first()

    if user:
        if pin and user.pin != pin:
            messages.error(request, f"Invalid PIN for user '{user.full_name}'. Default is 1234.")
            return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

        request.session['current_user_id'] = user.id
        messages.success(request, f"Authenticated session switched to {user.full_name} ({user.get_role_display()})")
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))
