import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError, PermissionDenied
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.utils import timezone
from django.db.models import Count, Q, Sum
from django.conf import settings

from tracker.models import (
    User, Client, ClientContact, Staff, Engagement, EngagementTeam,
    Query, QueryResponse, Attachment, ExceptionApproval, AuditTrail, Memo, Notification
)
from tracker.forms import (
    LoginForm, ForcePasswordChangeForm, ClientForm, ClientContactForm,
    StaffForm, EngagementForm, EngagementTeamForm, QueryForm, QueryResponseForm,
    ExceptionRequestForm, ExceptionDecisionForm, StepUpAuthForm
)
from tracker.services.audit_service import log_audit
from tracker.services.permissions import (
    get_user_role_for_engagement, can_manage_masters, can_create_engagement,
    can_assign_team, can_create_query, can_issue_query, can_edit_query,
    can_close_query, can_request_exception, can_approve_exception,
    can_generate_memo, can_signoff_memo, can_view_query, can_post_response
)
from tracker.services.state_machine import transition_query
from tracker.services.memo_generator import check_memo_gate, generate_docx_memo
from tracker.services.excel_exporter import export_queries_to_excel


# ==========================================
# 1. AUTHENTICATION & USER MANAGEMENT
# ==========================================

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email'].lower()
        password = form.cleaned_data['password']

        user_obj = User.objects.filter(email=email).first()
        if user_obj and user_obj.is_locked:
            messages.error(request, "Account is locked due to multiple failed login attempts. Please contact System Administrator.")
            log_audit(request, 'User', email, 'Lockout', 'is_locked', 'True', 'True', performed_by_name=email)
            return render(request, 'tracker/login.html', {'form': form})

        user = authenticate(request, email=email, password=password)
        if user is not None:
            if not user.is_active:
                messages.error(request, "This account has been deactivated.")
                return render(request, 'tracker/login.html', {'form': form})

            user.reset_failed_attempts()
            login(request, user)
            log_audit(request, 'User', user.email, 'Login', user=user)

            if user.must_change_password:
                messages.info(request, "First login detected. Please set your new permanent password.")
                return redirect('force_password_change')

            messages.success(request, f"Welcome, {user.full_name}!")
            return redirect('dashboard')
        else:
            if user_obj:
                user_obj.record_failed_attempt()
                log_audit(request, 'User', email, 'Failed Login', 'failed_login_attempts', str(user_obj.failed_login_attempts - 1), str(user_obj.failed_login_attempts), performed_by_name=email)
                if user_obj.is_locked:
                    messages.error(request, "Your account has been locked after 5 failed login attempts. Contact Admin.")
                else:
                    attempts_left = 5 - user_obj.failed_login_attempts
                    messages.error(request, f"Invalid credentials. {attempts_left} attempt(s) remaining before lockout.")
            else:
                messages.error(request, "Invalid email or password.")
                log_audit(request, 'User', email, 'Failed Login', performed_by_name=email)

    return render(request, 'tracker/login.html', {'form': form})


def logout_view(request):
    if request.user.is_authenticated:
        log_audit(request, 'User', request.user.email, 'Logout', user=request.user)
        logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('login')


@login_required
def force_password_change(request):
    form = ForcePasswordChangeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        new_pwd = form.cleaned_data['new_password']
        user = request.user
        user.set_password(new_pwd)
        user.must_change_password = False
        user.save()
        login(request, user)
        log_audit(request, 'User', user.email, 'Password Change', 'must_change_password', 'True', 'False', user=user)
        messages.success(request, "Password successfully updated! You now have full access.")
        return redirect('dashboard')

    return render(request, 'tracker/force_password_change.html', {'form': form})


@login_required
def admin_users_view(request):
    if not (request.user.user_type == 'ADMIN' or request.user.is_superuser):
        raise PermissionDenied("Access restricted to System Administrators.")

    users = User.objects.all().order_by('-created_at')
    return render(request, 'tracker/admin_users.html', {'users': users})


@login_required
def admin_unlock_user(request, user_id):
    if not (request.user.user_type == 'ADMIN' or request.user.is_superuser):
        raise PermissionDenied("Access restricted to System Administrators.")

    target_user = get_object_or_404(User, id=user_id)
    target_user.reset_failed_attempts()
    log_audit(request, 'User', target_user.email, 'Unlock', 'is_locked', 'True', 'False', user=request.user)
    messages.success(request, f"Account {target_user.email} has been unlocked.")
    return redirect('admin_users')


# ==========================================
# 2. DASHBOARDS
# ==========================================

@login_required
def dashboard_view(request):
    user = request.user
    if user.must_change_password:
        return redirect('force_password_change')

    if user.user_type == 'ADMIN' or user.is_superuser:
        return admin_dashboard(request)
    elif user.user_type == 'CLIENT':
        return client_dashboard(request)
    else:
        staff = getattr(user, 'staff_profile', None)
        if staff and staff.designation == 'Partner':
            return partner_dashboard(request)
        elif staff and staff.designation == 'Manager':
            return manager_dashboard(request)
        else:
            return staff_dashboard(request)


def partner_dashboard(request):
    staff = request.user.staff_profile
    engagements = Engagement.objects.filter(
        team_members__staff=staff,
        team_members__is_active=True
    ).distinct()

    queries = Query.objects.filter(engagement__in=engagements)
    
    total_engagements = engagements.count()
    active_engagements = engagements.filter(status='In Progress').count()
    memo_ready_count = 0
    for eng in engagements:
        allowed, _, _ = check_memo_gate(eng)
        if allowed and eng.status != 'Memo Issued':
            memo_ready_count += 1

    total_queries = queries.count()
    open_queries = queries.exclude(status__in=['Closed', 'Closed - Exception Approved', 'Withdrawn']).count()
    closed_queries = total_queries - open_queries
    overdue_queries = [q for q in queries.filter(status__in=['Issued', 'Info Awaited', 'Pending Client Review']) if q.is_overdue]
    
    pending_exceptions = ExceptionApproval.objects.filter(
        engagement__in=engagements,
        decision='Pending'
    )

    status_counts = queries.values('status').annotate(count=Count('id'))
    status_dict = {item['status']: item['count'] for item in status_counts}

    area_counts = queries.values('area').annotate(count=Count('id')).order_by('-count')[:5]

    context = {
        'total_engagements': total_engagements,
        'active_engagements': active_engagements,
        'total_queries': total_queries,
        'open_queries': open_queries,
        'closed_queries': closed_queries,
        'overdue_count': len(overdue_queries),
        'overdue_queries': overdue_queries[:5],
        'pending_exceptions_count': pending_exceptions.count(),
        'pending_exceptions': pending_exceptions[:5],
        'memo_ready_count': memo_ready_count,
        'engagements': engagements[:5],
        'status_dict_json': json.dumps(status_dict),
        'area_labels_json': json.dumps([item['area'] for item in area_counts]),
        'area_data_json': json.dumps([item['count'] for item in area_counts]),
    }
    return render(request, 'tracker/dashboard_partner.html', context)


def manager_dashboard(request):
    staff = request.user.staff_profile
    engagements = Engagement.objects.filter(
        team_members__staff=staff,
        team_members__is_active=True
    ).distinct()

    selected_eng_id = request.GET.get('engagement')
    if selected_eng_id:
        active_eng = engagements.filter(id=selected_eng_id).first()
    else:
        active_eng = engagements.first()

    queries = active_eng.queries.all() if active_eng else Query.objects.none()

    total_q = queries.count()
    drafts = queries.filter(status__in=['Draft', 'Pending Internal Review']).count()
    issued = queries.filter(status='Issued').count()
    responded = queries.filter(status='Responded').count()
    closed = queries.filter(status__in=['Closed', 'Closed - Exception Approved']).count()

    ageing_0_7 = sum(1 for q in queries if q.ageing_bucket == '0-7 days' and not q.is_terminal)
    ageing_8_15 = sum(1 for q in queries if q.ageing_bucket == '8-15 days' and not q.is_terminal)
    ageing_16_30 = sum(1 for q in queries if q.ageing_bucket == '16-30 days' and not q.is_terminal)
    ageing_gt_30 = sum(1 for q in queries if q.ageing_bucket == '>30 days' and not q.is_terminal)

    area_counts = queries.values('area').annotate(count=Count('id')).order_by('-count')

    context = {
        'engagements': engagements,
        'active_eng': active_eng,
        'total_q': total_q,
        'drafts': drafts,
        'issued': issued,
        'responded': responded,
        'closed': closed,
        'queries': queries[:8],
        'ageing_data_json': json.dumps([ageing_0_7, ageing_8_15, ageing_16_30, ageing_gt_30]),
        'area_labels_json': json.dumps([item['area'] for item in area_counts]),
        'area_data_json': json.dumps([item['count'] for item in area_counts]),
    }
    return render(request, 'tracker/dashboard_manager.html', context)


def staff_dashboard(request):
    staff = request.user.staff_profile
    my_raised = Query.objects.filter(raised_by=staff).order_by('-raised_on')
    my_drafts = my_raised.filter(status='Draft')
    pending_review = my_raised.filter(status='Pending Internal Review')
    awaiting_client = my_raised.filter(status__in=['Issued', 'Info Awaited'])
    client_responded = my_raised.filter(status='Responded')

    context = {
        'my_raised_count': my_raised.count(),
        'my_drafts': my_drafts,
        'pending_review': pending_review,
        'awaiting_client': awaiting_client,
        'client_responded': client_responded,
        'recent_queries': my_raised[:6]
    }
    return render(request, 'tracker/dashboard_staff.html', context)


def client_dashboard(request):
    contact = getattr(request.user, 'client_contact', None)
    if not contact:
        return render(request, 'tracker/client_unlinked.html')

    client = contact.client
    engagements = client.engagements.filter(status__in=['Planned', 'In Progress', 'Queries Closed', 'Memo Issued'])

    visible_statuses = ['Issued', 'Pending Client Review', 'Responded', 'Info Awaited', 'Closed', 'Closed - Exception Approved']
    queries = Query.objects.filter(engagement__client=client, status__in=visible_statuses)

    pending_response = queries.filter(status__in=['Issued', 'Info Awaited'])
    overdue = [q for q in pending_response if q.is_overdue]
    responded = queries.filter(status='Responded')
    closed = queries.filter(status__in=['Closed', 'Closed - Exception Approved'])

    context = {
        'client': client,
        'contact': contact,
        'engagements': engagements,
        'total_visible': queries.count(),
        'pending_response_count': pending_response.count(),
        'overdue_count': len(overdue),
        'responded_count': responded.count(),
        'closed_count': closed.count(),
        'actionable_queries': pending_response.order_by('due_date'),
    }
    return render(request, 'tracker/dashboard_client.html', context)


def admin_dashboard(request):
    total_clients = Client.objects.count()
    total_staff = Staff.objects.count()
    total_engagements = Engagement.objects.count()
    locked_users = User.objects.filter(is_locked=True)
    recent_logs = AuditTrail.objects.all()[:10]

    context = {
        'total_clients': total_clients,
        'total_staff': total_staff,
        'total_engagements': total_engagements,
        'locked_users': locked_users,
        'recent_logs': recent_logs,
    }
    return render(request, 'tracker/dashboard_admin.html', context)


# ==========================================
# 3. MASTERS MANAGEMENT (CRUD)
# ==========================================

@login_required
def client_list(request):
    clients = Client.objects.all()
    q = request.GET.get('q')
    risk = request.GET.get('risk')
    status = request.GET.get('status')

    if q:
        clients = clients.filter(Q(client_name__icontains=q) | Q(client_code__icontains=q) | Q(city__icontains=q))
    if risk:
        clients = clients.filter(risk_category=risk)
    if status:
        clients = clients.filter(status=status)

    return render(request, 'tracker/masters/client_list.html', {'clients': clients})


@login_required
def client_create(request):
    if not can_manage_masters(request.user):
        raise PermissionDenied("Only System Administrators can create clients.")

    form = ClientForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        client = form.save(commit=False)
        client.created_by = request.user
        client.save()
        log_audit(request, 'Client', client.client_code, 'Create', user=request.user)
        messages.success(request, f"Client {client.client_name} ({client.client_code}) created successfully.")
        return redirect('client_list')

    return render(request, 'tracker/masters/client_form.html', {'form': form, 'title': 'Add New Client Master'})


@login_required
def client_edit(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if not can_manage_masters(request.user):
        raise PermissionDenied("Only System Administrators can edit clients.")

    form = ClientForm(request.POST or None, instance=client)
    if request.method == 'POST' and form.is_valid():
        client = form.save(commit=False)
        client.modified_by = request.user
        client.save()
        log_audit(request, 'Client', client.client_code, 'Update', user=request.user)
        messages.success(request, f"Client {client.client_name} updated successfully.")
        return redirect('client_list')

    contacts = client.contacts.all()
    return render(request, 'tracker/masters/client_form.html', {'form': form, 'client': client, 'contacts': contacts, 'title': f'Edit Client: {client.client_name}'})


@login_required
def contact_create(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    if not can_manage_masters(request.user):
        raise PermissionDenied("Only System Administrators can manage client contacts.")

    form = ClientContactForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        contact = form.save(commit=False)
        contact.client = client
        contact.created_by = request.user

        create_user = form.cleaned_data.get('create_user_account')
        if create_user:
            user, created = User.objects.get_or_create(
                email=contact.email.lower(),
                defaults={
                    'full_name': contact.contact_name,
                    'user_type': 'CLIENT',
                    'must_change_password': True
                }
            )
            if created:
                user.set_password('Client@123')
                user.save()
            contact.user = user

        contact.save()
        log_audit(request, 'ClientContact', contact.email, 'Create', user=request.user)
        messages.success(request, f"Contact {contact.contact_name} added to {client.client_name}.")
        return redirect('client_edit', pk=client.id)

    return render(request, 'tracker/masters/contact_form.html', {'form': form, 'client': client, 'title': f'Add Contact Person for {client.client_name}'})


@login_required
def contact_edit(request, contact_id):
    contact = get_object_or_404(ClientContact, id=contact_id)
    client = contact.client
    if not can_manage_masters(request.user):
        raise PermissionDenied("Only System Administrators can manage client contacts.")

    has_user = contact.user is not None
    form = ClientContactForm(request.POST or None, instance=contact, initial={'create_user_account': has_user})
    if request.method == 'POST' and form.is_valid():
        contact = form.save(commit=False)
        contact.modified_by = request.user

        create_user = form.cleaned_data.get('create_user_account')
        if create_user and not contact.user:
            user, created = User.objects.get_or_create(
                email=contact.email.lower(),
                defaults={
                    'full_name': contact.contact_name,
                    'user_type': 'CLIENT',
                    'must_change_password': True
                }
            )
            if created:
                user.set_password('Client@123')
                user.save()
            contact.user = user

        contact.save()
        log_audit(request, 'ClientContact', contact.email, 'Update', user=request.user)
        messages.success(request, f"Contact {contact.contact_name} updated successfully.")
        return redirect('client_edit', pk=client.id)

    return render(request, 'tracker/masters/contact_form.html', {'form': form, 'client': client, 'contact': contact, 'title': f'Edit Contact Person: {contact.contact_name}'})


@login_required
def contact_delete(request, contact_id):
    contact = get_object_or_404(ClientContact, id=contact_id)
    client_id = contact.client_id
    if not can_manage_masters(request.user):
        raise PermissionDenied("Only System Administrators can manage client contacts.")

    name = contact.contact_name
    contact.delete()
    log_audit(request, 'ClientContact', name, 'Delete', user=request.user)
    messages.success(request, f"Contact {name} removed.")
    return redirect('client_edit', pk=client_id)


@login_required
def staff_list(request):
    staff_members = Staff.objects.all()
    desig = request.GET.get('designation')
    status = request.GET.get('status')
    if desig:
        staff_members = staff_members.filter(designation=desig)
    if status:
        staff_members = staff_members.filter(status=status)

    return render(request, 'tracker/masters/staff_list.html', {'staff_members': staff_members})


@login_required
def staff_create(request):
    if not can_manage_masters(request.user):
        raise PermissionDenied("Only System Administrators can add staff members.")

    form = StaffForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        staff = form.save(commit=False)
        staff.created_by = request.user

        create_user = form.cleaned_data.get('create_user_account')
        if create_user:
            user, created = User.objects.get_or_create(
                email=staff.email.lower(),
                defaults={
                    'full_name': staff.full_name,
                    'user_type': 'STAFF',
                    'must_change_password': True
                }
            )
            if created:
                user.set_password('Audit@123')
                user.save()
            staff.user = user

        staff.save()
        log_audit(request, 'Staff', staff.staff_code, 'Create', user=request.user)
        messages.success(request, f"Staff member {staff.full_name} ({staff.staff_code}) registered.")
        return redirect('staff_list')

    return render(request, 'tracker/masters/staff_form.html', {'form': form, 'title': 'Register Staff Member'})


@login_required
def staff_edit(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    if not can_manage_masters(request.user):
        raise PermissionDenied("Only System Administrators can edit staff.")

    form = StaffForm(request.POST or None, instance=staff)
    if request.method == 'POST' and form.is_valid():
        staff = form.save(commit=False)
        staff.modified_by = request.user
        staff.save()
        log_audit(request, 'Staff', staff.staff_code, 'Update', user=request.user)
        messages.success(request, f"Staff member {staff.full_name} updated.")
        return redirect('staff_list')

    return render(request, 'tracker/masters/staff_form.html', {'form': form, 'staff': staff, 'title': f'Edit Staff: {staff.full_name}'})


# ==========================================
# 4. ENGAGEMENT & TEAM ASSIGNMENT
# ==========================================

@login_required
def engagement_list(request):
    user = request.user
    if user.user_type == 'CLIENT':
        contact = getattr(user, 'client_contact', None)
        engagements = Engagement.objects.filter(client=contact.client) if contact else Engagement.objects.none()
    elif user.user_type == 'ADMIN' or user.is_superuser:
        engagements = Engagement.objects.all()
    else:
        staff = getattr(user, 'staff_profile', None)
        engagements = Engagement.objects.filter(team_members__staff=staff, team_members__is_active=True).distinct()

    return render(request, 'tracker/engagements/engagement_list.html', {'engagements': engagements})


@login_required
def engagement_create(request):
    if not can_create_engagement(request.user):
        raise PermissionDenied("Only Partners, Managers, or Admins can create audit engagements.")

    form = EngagementForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        engagement = form.save(commit=False)
        engagement.created_by = request.user
        engagement.engagement_code = Engagement.generate_code(
            engagement.client.client_code,
            engagement.financial_year,
            engagement.audit_type
        )
        engagement.save()
        log_audit(request, 'Engagement', engagement.engagement_code, 'Create', user=request.user)
        messages.success(request, f"Engagement {engagement.engagement_code} created. Next, assign the engagement team.")
        return redirect('engagement_detail', pk=engagement.id)

    return render(request, 'tracker/engagements/engagement_form.html', {'form': form, 'title': 'Create New Engagement'})


@login_required
def engagement_edit(request, pk):
    engagement = get_object_or_404(Engagement, pk=pk)
    if not can_create_engagement(request.user):
        raise PermissionDenied("Only Partners, Managers, or Admins can edit audit engagements.")

    form = EngagementForm(request.POST or None, instance=engagement)
    if request.method == 'POST' and form.is_valid():
        engagement = form.save(commit=False)
        engagement.modified_by = request.user
        engagement.save()
        log_audit(request, 'Engagement', engagement.engagement_code, 'Update', user=request.user)
        messages.success(request, f"Engagement {engagement.engagement_code} updated successfully.")
        return redirect('engagement_detail', pk=engagement.id)

    return render(request, 'tracker/engagements/engagement_form.html', {'form': form, 'engagement': engagement, 'title': f'Edit Engagement: {engagement.engagement_code}'})


@login_required
def engagement_detail(request, pk):
    engagement = get_object_or_404(Engagement, pk=pk)
    team_members = engagement.team_members.all()
    queries = engagement.queries.all()

    memo_allowed, open_queries, has_ex03 = check_memo_gate(engagement)

    active_partners = team_members.filter(role_on_engagement='Partner', is_reviewer=False, is_active=True).count()
    lead_partner_missing = (active_partners == 0)

    user_role = get_user_role_for_engagement(request.user, engagement)

    context = {
        'engagement': engagement,
        'team_members': team_members,
        'queries': queries,
        'memo_allowed': memo_allowed,
        'open_queries_count': len(open_queries),
        'has_ex03': has_ex03,
        'lead_partner_missing': lead_partner_missing,
        'user_role': user_role,
        'can_assign': can_assign_team(request.user, engagement),
        'can_create_q': can_create_query(request.user, engagement),
        'can_memo': can_generate_memo(request.user, engagement),
        'can_sign': can_signoff_memo(request.user, engagement),
        'memos': engagement.memos.all(),
        'exceptions': engagement.exceptions.all(),
    }
    return render(request, 'tracker/engagements/engagement_detail.html', context)


@login_required
def team_assign(request, engagement_id):
    engagement = get_object_or_404(Engagement, id=engagement_id)
    if not can_assign_team(request.user, engagement):
        raise PermissionDenied("You do not have permission to assign team members.")

    form = EngagementTeamForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        assignment = form.save(commit=False)
        assignment.engagement = engagement
        assignment.created_by = request.user
        assignment.is_active = True
        
        if assignment.independence_declared:
            assignment.independence_declared_on = timezone.now()

        assignment.save()
        log_audit(request, 'EngagementTeam', f"{engagement.engagement_code}-{assignment.staff.staff_code}", 'Team Change', 'role_on_engagement', '', assignment.role_on_engagement, user=request.user)
        messages.success(request, f"Assigned {assignment.staff.full_name} as {assignment.role_on_engagement} to {engagement.engagement_code}.")
        return redirect('engagement_detail', pk=engagement.id)

    return render(request, 'tracker/engagements/team_form.html', {'form': form, 'engagement': engagement, 'title': f'Assign Team Member to {engagement.engagement_code}'})


@login_required
def team_edit(request, assignment_id):
    assignment = get_object_or_404(EngagementTeam, id=assignment_id)
    engagement = assignment.engagement
    if not can_assign_team(request.user, engagement):
        raise PermissionDenied("You do not have permission to edit team assignments.")

    form = EngagementTeamForm(request.POST or None, instance=assignment)
    if request.method == 'POST' and form.is_valid():
        assignment = form.save(commit=False)
        assignment.modified_by = request.user
        if assignment.independence_declared and not assignment.independence_declared_on:
            assignment.independence_declared_on = timezone.now()
        assignment.save()
        log_audit(request, 'EngagementTeam', f"{engagement.engagement_code}-{assignment.staff.staff_code}", 'Team Change', 'role_on_engagement', '', assignment.role_on_engagement, user=request.user)
        messages.success(request, f"Updated assignment for {assignment.staff.full_name} ({assignment.role_on_engagement}).")
        return redirect('engagement_detail', pk=engagement.id)

    return render(request, 'tracker/engagements/team_form.html', {'form': form, 'engagement': engagement, 'assignment': assignment, 'title': f'Edit Team Member: {assignment.staff.full_name}'})


@login_required
def team_release(request, assignment_id):
    assignment = get_object_or_404(EngagementTeam, id=assignment_id)
    if not can_assign_team(request.user, assignment.engagement):
        raise PermissionDenied("You do not have permission to release team members.")

    assignment.is_active = False
    assignment.released_on = timezone.localdate()
    assignment.modified_by = request.user
    assignment.save()
    log_audit(request, 'EngagementTeam', f"{assignment.engagement.engagement_code}-{assignment.staff.staff_code}", 'Team Change', 'is_active', 'True', 'False', user=request.user)
    messages.info(request, f"{assignment.staff.full_name} has been released from engagement team (historical queries preserved).")
    return redirect('engagement_detail', pk=assignment.engagement_id)


@login_required
def declare_independence(request, assignment_id):
    assignment = get_object_or_404(EngagementTeam, id=assignment_id)
    if assignment.staff.user != request.user:
        raise PermissionDenied("You can only declare independence for your own assignment.")

    assignment.independence_declared = True
    assignment.independence_declared_on = timezone.now()
    assignment.save()
    log_audit(request, 'EngagementTeam', f"{assignment.engagement.engagement_code}-{assignment.staff.staff_code}", 'Update', 'independence_declared', 'False', 'True', user=request.user)
    messages.success(request, f"Independence & Conflict of Interest declaration submitted for {assignment.engagement.engagement_code}.")
    return redirect('engagement_detail', pk=assignment.engagement_id)


# ==========================================
# 5. QUERY LIFECYCLE & THREADS
# ==========================================

@login_required
def query_list(request):
    user = request.user
    queries = Query.objects.all()

    if user.user_type == 'CLIENT':
        contact = getattr(user, 'client_contact', None)
        if not contact:
            return render(request, 'tracker/client_unlinked.html')
        queries = queries.filter(
            engagement__client=contact.client,
            status__in=['Issued', 'Pending Client Review', 'Responded', 'Info Awaited', 'Closed', 'Closed - Exception Approved']
        )
    elif user.user_type == 'STAFF':
        staff = getattr(user, 'staff_profile', None)
        eng_ids = EngagementTeam.objects.filter(staff=staff, is_active=True).values_list('engagement_id', flat=True)
        queries = queries.filter(engagement_id__in=eng_ids)

    engagement_id = request.GET.get('engagement')
    status = request.GET.get('status')
    area = request.GET.get('area')
    priority = request.GET.get('priority')
    risk = request.GET.get('risk')
    query_type = request.GET.get('query_type')
    overdue_only = request.GET.get('overdue')
    repeat_only = request.GET.get('repeat')
    search = request.GET.get('q')

    if engagement_id:
        queries = queries.filter(engagement_id=engagement_id)
    if status:
        queries = queries.filter(status=status)
    if area:
        queries = queries.filter(area=area)
    if priority:
        queries = queries.filter(priority=priority)
    if risk:
        queries = queries.filter(risk_rating=risk)
    if query_type:
        queries = queries.filter(query_type=query_type)
    if repeat_only == '1':
        queries = queries.filter(is_repeat_observation=True)
    if search:
        queries = queries.filter(Q(title__icontains=search) | Q(query_no__icontains=search) | Q(description__icontains=search))

    if overdue_only == '1':
        queries = [q for q in queries if q.is_overdue]

    if user.user_type == 'CLIENT':
        engagements_filter = Engagement.objects.filter(client=user.client_contact.client)
    elif user.user_type == 'ADMIN' or user.is_superuser:
        engagements_filter = Engagement.objects.all()
    else:
        engagements_filter = Engagement.objects.filter(team_members__staff=user.staff_profile, team_members__is_active=True).distinct()

    return render(request, 'tracker/queries/query_list.html', {
        'queries': queries,
        'engagements_filter': engagements_filter,
        'areas': Query.AREA_CHOICES,
        'statuses': Query.STATUS_CHOICES,
        'priorities': Query.PRIORITY_CHOICES,
        'risks': Query.RISK_RATING_CHOICES,
    })


@login_required
def query_create(request, engagement_id=None):
    if request.user.user_type != 'STAFF':
        raise PermissionDenied("Only audit staff can raise queries.")

    staff = request.user.staff_profile
    initial = {}
    if engagement_id:
        eng = get_object_or_404(Engagement, id=engagement_id)
        if not can_create_query(request.user, eng):
            raise PermissionDenied("You are not assigned to this engagement team.")
        initial['engagement'] = eng

    copy_from_id = request.GET.get('copy_from')
    roll_forward_id = request.GET.get('roll_forward')

    if copy_from_id:
        src = get_object_or_404(Query, id=copy_from_id)
        initial.update({
            'engagement': src.engagement,
            'query_type': src.query_type,
            'area': src.area,
            'title': f"Copy - {src.title}",
            'description': src.description,
            'priority': src.priority,
            'risk_rating': src.risk_rating,
            'condition': src.condition,
            'criteria': src.criteria,
            'cause': src.cause,
            'effect_risk': src.effect_risk,
            'recommendation': src.recommendation,
        })
    elif roll_forward_id:
        src = get_object_or_404(Query, id=roll_forward_id)
        initial.update({
            'query_type': src.query_type,
            'area': src.area,
            'title': f"Repeat: {src.title}",
            'description': src.description,
            'priority': src.priority,
            'risk_rating': src.risk_rating,
            'condition': src.condition,
            'criteria': src.criteria,
            'cause': src.cause,
            'effect_risk': src.effect_risk,
            'recommendation': src.recommendation,
            'is_repeat_observation': True,
            'prior_year_query_ref': src,
        })

    form = QueryForm(request.POST or None, request.FILES or None, initial=initial)
    
    assigned_engs = Engagement.objects.filter(team_members__staff=staff, team_members__is_active=True).distinct()
    form.fields['engagement'].queryset = assigned_engs

    if request.method == 'POST' and form.is_valid():
        query = form.save(commit=False)
        query.raised_by = staff
        query.created_by = request.user
        query.status = 'Draft'
        query.save()

        att_file = form.cleaned_data.get('attachment')
        if att_file:
            Attachment.objects.create(
                query=query,
                file=att_file,
                file_name=att_file.name,
                file_type=att_file.content_type,
                file_size=att_file.size,
                uploaded_by=request.user
            )

        log_audit(request, 'Query', f"Draft-{query.id}", 'Create', user=request.user)
        messages.success(request, f"Query '{query.title}' saved in Draft status.")

        submit_action = request.POST.get('action')
        if submit_action == 'submit_review':
            try:
                transition_query(query, 'Pending Internal Review', request.user, request=request)
                messages.success(request, "Query submitted for Internal Review.")
            except ValidationError as e:
                messages.error(request, str(e))
        elif submit_action == 'issue':
            try:
                transition_query(query, 'Issued', request.user, request=request)
                messages.success(request, f"Query issued to client with number {query.query_no}.")
            except ValidationError as e:
                messages.error(request, str(e))

        return redirect('query_detail', pk=query.id)

    return render(request, 'tracker/queries/query_form.html', {'form': form, 'title': 'Create Query / Audit Observation'})


@login_required
def query_detail(request, pk):
    query = get_object_or_404(Query, pk=pk)
    if not can_view_query(request.user, query):
        raise PermissionDenied("You do not have permission to view this query.")

    user_role = get_user_role_for_engagement(request.user, query.engagement)
    responses = query.responses.all()
    attachments = query.attachments.filter(is_active=True)
    
    history = AuditTrail.objects.filter(
        entity_type='Query',
        entity_id__in=[query.query_no, f"Draft-{query.id}"]
    ).order_by('performed_on')

    response_form = QueryResponseForm()

    can_issue = can_issue_query(request.user, query)
    can_close = can_close_query(request.user, query)
    can_edit = can_edit_query(request.user, query)
    can_respond = can_post_response(request.user, query)

    is_creator = (query.raised_by.user == request.user)

    context = {
        'query': query,
        'user_role': user_role,
        'responses': responses,
        'attachments': attachments,
        'history': history,
        'response_form': response_form,
        'can_issue': can_issue,
        'can_close': can_close,
        'can_edit': can_edit,
        'can_respond': can_respond,
        'is_creator': is_creator,
    }
    return render(request, 'tracker/queries/query_detail.html', context)


@login_required
def query_edit(request, pk):
    query = get_object_or_404(Query, pk=pk)
    if not can_edit_query(request.user, query):
        raise PermissionDenied("You do not have permission to edit this query in its current state.")

    form = QueryForm(request.POST or None, request.FILES or None, instance=query)
    if request.method == 'POST' and form.is_valid():
        q = form.save(commit=False)
        q.modified_by = request.user
        q.save()
        log_audit(request, 'Query', query.query_no or f"Draft-{query.id}", 'Update', user=request.user)
        messages.success(request, "Query details updated successfully.")
        return redirect('query_detail', pk=query.id)

    return render(request, 'tracker/queries/query_form.html', {'form': form, 'query': query, 'title': f'Edit: {query.query_no or query.title}'})


@login_required
def query_transition_action(request, pk, target_status):
    query = get_object_or_404(Query, pk=pk)
    remarks = request.POST.get('remarks', '').strip()
    new_due_date = request.POST.get('new_due_date')

    try:
        transition_query(
            query=query,
            to_status=target_status,
            user=request.user,
            remarks=remarks,
            new_due_date=new_due_date,
            request=request
        )
        messages.success(request, f"Query status successfully updated to '{target_status}'.")
    except ValidationError as e:
        messages.error(request, str(e.message if hasattr(e, 'message') else e))

    return redirect('query_detail', pk=query.id)


@login_required
def query_post_response(request, pk):
    query = get_object_or_404(Query, pk=pk)
    if not can_post_response(request.user, query):
        raise PermissionDenied("You do not have permission to post a response on this query.")

    form = QueryResponseForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        resp_text = form.cleaned_data['response_text']
        att_file = form.cleaned_data.get('attachment')

        is_client = (request.user.user_type == 'CLIENT')
        seq = query.responses.count() + 1

        needs_coord_approval = False
        if is_client and query.engagement.client_coordinator_review_enabled:
            contact = getattr(request.user, 'client_contact', None)
            if contact and not contact.is_primary_coordinator:
                needs_coord_approval = True

        resp = QueryResponse.objects.create(
            query=query,
            response_text=resp_text,
            responded_by_type='Client' if is_client else 'Staff',
            responded_by_user=request.user,
            is_client_submission=is_client,
            is_approved_by_coordinator=not needs_coord_approval,
            sequence_no=seq,
            status_at_response=query.status
        )

        if att_file:
            Attachment.objects.create(
                query=query,
                response=resp,
                file=att_file,
                file_name=att_file.name,
                file_type=att_file.content_type,
                file_size=att_file.size,
                uploaded_by=request.user
            )

        log_audit(request, 'QueryResponse', str(resp.id), 'Create', 'response_text', '', resp_text[:100], user=request.user)

        if is_client:
            if needs_coord_approval:
                transition_query(query, 'Pending Client Review', request.user, request=request)
                messages.info(request, "Response recorded and submitted to Client Coordinator for approval.")
            else:
                transition_query(query, 'Responded', request.user, request=request)
                messages.success(request, "Response successfully submitted to Audit Team.")
        else:
            messages.success(request, "Follow-up audit clarification posted.")

        return redirect('query_detail', pk=query.id)

    messages.error(request, "Failed to submit response. Please verify inputs.")
    return redirect('query_detail', pk=query.id)


@login_required
def query_export_excel_view(request):
    user = request.user
    queries = Query.objects.all()

    if user.user_type == 'CLIENT':
        contact = getattr(user, 'client_contact', None)
        queries = queries.filter(engagement__client=contact.client, status__in=['Issued', 'Responded', 'Info Awaited', 'Closed', 'Closed - Exception Approved'])
    elif user.user_type == 'STAFF':
        staff = getattr(user, 'staff_profile', None)
        eng_ids = EngagementTeam.objects.filter(staff=staff, is_active=True).values_list('engagement_id', flat=True)
        queries = queries.filter(engagement_id__in=eng_ids)

    engagement_id = request.GET.get('engagement')
    if engagement_id:
        queries = queries.filter(engagement_id=engagement_id)

    excel_file = export_queries_to_excel(queries)
    response = HttpResponse(
        excel_file.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=Audit_Queries_Export_{timezone.now().strftime("%Y%m%d")}.xlsx'
    return response


# ==========================================
# 6. EXCEPTION-BASED APPROVAL MODULE
# ==========================================

@login_required
def exception_list(request):
    user = request.user
    if user.user_type == 'CLIENT':
        raise PermissionDenied("Clients cannot access the exception register.")

    exceptions = ExceptionApproval.objects.all()
    status_filter = request.GET.get('status')
    type_filter = request.GET.get('type')

    if status_filter:
        exceptions = exceptions.filter(decision=status_filter)
    if type_filter:
        exceptions = exceptions.filter(exception_type=type_filter)

    return render(request, 'tracker/exceptions/exception_list.html', {
        'exceptions': exceptions,
        'types': ExceptionApproval.EXCEPTION_TYPE_CHOICES,
        'statuses': ExceptionApproval.DECISION_CHOICES
    })


@login_required
def exception_queue(request):
    if request.user.user_type != 'STAFF':
        raise PermissionDenied("Partner queue accessible to audit staff only.")
    
    staff = request.user.staff_profile
    if staff.designation != 'Partner':
        raise PermissionDenied("Only Audit Partners have access to the exception decision queue.")

    pending_items = ExceptionApproval.objects.filter(
        engagement__team_members__staff=staff,
        engagement__team_members__is_active=True,
        decision='Pending'
    ).distinct()

    return render(request, 'tracker/exceptions/exception_queue.html', {'pending_items': pending_items})


@login_required
def exception_request(request, engagement_id):
    engagement = get_object_or_404(Engagement, id=engagement_id)
    if not can_request_exception(request.user, engagement):
        raise PermissionDenied("You do not have permission to request an exception on this engagement.")

    query_id = request.GET.get('query_id')
    initial = {'engagement': engagement}
    if query_id:
        query = get_object_or_404(Query, id=query_id)
        initial['query'] = query

    form = ExceptionRequestForm(request.POST or None, initial=initial)
    form.fields['query'].queryset = engagement.queries.all()

    if request.method == 'POST' and form.is_valid():
        exc = form.save(commit=False)
        exc.engagement = engagement
        exc.requested_by = request.user.staff_profile
        exc.reference_no = ExceptionApproval.generate_reference_no()
        exc.save()

        log_audit(request, 'Exception', exc.reference_no, 'Exception Request', 'decision', '', 'Pending', user=request.user)

        lead_partner = engagement.get_lead_partner()
        if lead_partner and lead_partner.user:
            Notification.objects.create(
                recipient=lead_partner.user,
                title=f"New Exception Requested: {exc.reference_no}",
                message=f"Exception {exc.get_exception_type_display()} requested by {request.user.full_name} for {engagement.engagement_code}.",
                link=f"/exceptions/{exc.id}/decision/"
            )

        messages.success(request, f"Exception request {exc.reference_no} queued for Partner approval.")
        return redirect('engagement_detail', pk=engagement.id)

    return render(request, 'tracker/exceptions/exception_request_form.html', {'form': form, 'engagement': engagement})


@login_required
def exception_decision(request, pk):
    exc = get_object_or_404(ExceptionApproval, pk=pk)
    if not can_approve_exception(request.user, exc):
        raise PermissionDenied("You do not have authority to approve/reject this exception (or Partner maker-checker restriction applies).")

    form = ExceptionDecisionForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        decision = form.cleaned_data['decision']
        remarks = form.cleaned_data['partner_remarks']

        exc.decision = decision
        exc.partner_remarks = remarks
        exc.approved_by = request.user.staff_profile
        exc.approved_on = timezone.now()

        if exc.requested_by == exc.approved_by:
            exc.is_self_approved = True

        exc.save()

        if decision == 'Approved':
            if exc.exception_type == 'EX-01' and exc.query:
                transition_query(exc.query, 'Closed - Exception Approved', request.user, remarks=f"Approved under {exc.reference_no}: {remarks}", request=request, exception_obj=exc)
            elif exc.exception_type == 'EX-02' and exc.query:
                transition_query(exc.query, 'Withdrawn', request.user, remarks=f"Withdrawn under {exc.reference_no}: {remarks}", request=request, exception_obj=exc)
            elif exc.exception_type == 'EX-04' and exc.query:
                transition_query(exc.query, 'Issued', request.user, remarks=f"Reopened under {exc.reference_no}: {remarks}", request=request, exception_obj=exc)
            elif exc.exception_type == 'EX-05':
                eng = exc.engagement
                eng.status = 'In Progress'
                eng.save()

        log_audit(request, 'Exception', exc.reference_no, f"Exception {decision}", 'decision', 'Pending', decision, user=request.user)

        if exc.requested_by.user:
            Notification.objects.create(
                recipient=exc.requested_by.user,
                title=f"Exception Decision: {exc.reference_no} ({decision})",
                message=f"Your exception request for {exc.get_exception_type_display()} has been {decision} by Partner {request.user.full_name}.",
                link=f"/engagements/{exc.engagement_id}/"
            )

        messages.success(request, f"Exception {exc.reference_no} has been {decision} with step-up authorization.")
        return redirect('exception_queue')

    return render(request, 'tracker/exceptions/exception_decision.html', {'form': form, 'exc': exc})


# ==========================================
# 7. AUDIT SUMMARY MEMO & GATE
# ==========================================

@login_required
def memo_hub(request, engagement_id):
    engagement = get_object_or_404(Engagement, id=engagement_id)
    if not can_generate_memo(request.user, engagement):
        raise PermissionDenied("Only Partners or Managers can access the Memo Generation module.")

    is_allowed, open_queries, has_ex03 = check_memo_gate(engagement)
    memos = engagement.memos.all()

    context = {
        'engagement': engagement,
        'is_allowed': is_allowed,
        'open_queries': open_queries,
        'has_ex03': has_ex03,
        'memos': memos,
        'can_sign': can_signoff_memo(request.user, engagement),
    }
    return render(request, 'tracker/memos/memo_hub.html', context)


@login_required
def memo_generate(request, engagement_id):
    engagement = get_object_or_404(Engagement, id=engagement_id)
    if not can_generate_memo(request.user, engagement):
        raise PermissionDenied("You do not have permission to generate the summary memo.")

    staff = request.user.staff_profile
    try:
        memo_rec, filepath = generate_docx_memo(engagement, staff, is_draft=True, request=request)
        messages.success(request, f"Draft Audit Summary Memo ({memo_rec.version_no}) generated successfully.")
    except ValueError as e:
        messages.error(request, str(e))

    return redirect('memo_hub', engagement_id=engagement.id)


@login_required
def memo_signoff(request, engagement_id):
    engagement = get_object_or_404(Engagement, id=engagement_id)
    if not can_signoff_memo(request.user, engagement):
        raise PermissionDenied("Only the Lead Engagement Partner can sign off on the Final Summary Memo.")

    form = StepUpAuthForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        staff = request.user.staff_profile
        try:
            memo_rec, filepath = generate_docx_memo(engagement, staff, is_draft=False, request=request)
            messages.success(request, f"Final Audit Summary Memo signed off! Engagement {engagement.engagement_code} moved to 'Memo Issued' and locked.")
        except Exception as e:
            messages.error(request, f"Error generating final memo: {str(e)}")

        return redirect('memo_hub', engagement_id=engagement.id)

    return render(request, 'tracker/memos/memo_signoff_modal.html', {'form': form, 'engagement': engagement})


@login_required
def memo_download(request, memo_id):
    memo = get_object_or_404(Memo, id=memo_id)
    if not can_generate_memo(request.user, memo.engagement) and not (request.user.user_type == 'ADMIN' or request.user.is_superuser):
        raise PermissionDenied("Permission denied to download memo.")

    full_path = settings.MEDIA_ROOT / memo.file_path
    if not full_path.exists():
        messages.error(request, "Memo file could not be found on server.")
        return redirect('memo_hub', engagement_id=memo.engagement_id)

    with open(full_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename={full_path.name}'
        return response


# ==========================================
# 8. NOTIFICATIONS & AUDIT TRAIL
# ==========================================

@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    
    if request.GET.get('mark_all_read') == '1':
        notifications.filter(is_read=False).update(is_read=True)
        messages.success(request, "All notifications marked as read.")
        return redirect('notifications')

    return render(request, 'tracker/notifications.html', {'notifications': notifications})


@login_required
def audit_trail_view(request):
    if request.user.user_type != 'ADMIN' and not request.user.is_superuser:
        staff = getattr(request.user, 'staff_profile', None)
        if not staff or staff.designation not in ['Partner', 'Manager']:
            raise PermissionDenied("Audit Trail is restricted to Administrators, Partners, and Managers.")

    logs = AuditTrail.objects.all()

    action_filter = request.GET.get('action')
    entity_filter = request.GET.get('entity_type')
    q = request.GET.get('q')

    if action_filter:
        logs = logs.filter(action=action_filter)
    if entity_filter:
        logs = logs.filter(entity_type=entity_filter)
    if q:
        logs = logs.filter(Q(entity_id__icontains=q) | Q(performed_by_name__icontains=q) | Q(old_value__icontains=q) | Q(new_value__icontains=q))

    return render(request, 'tracker/audit_trail.html', {
        'logs': logs[:200],
        'actions': AuditTrail.ACTION_CHOICES,
        'entity_types': ['Query', 'Engagement', 'Client', 'Staff', 'User', 'Memo', 'Exception', 'EngagementTeam']
    })
