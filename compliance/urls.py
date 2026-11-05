"""
LexSecure India Pro - URL Routing
"""

from django.urls import path
from compliance import views

urlpatterns = [
    # Dashboard / Executive Command Center
    path('', views.dashboard_view, name='home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Pillar 1: Contract / Document Review & Storage Workspace
    path('contracts/', views.contracts_view, name='contracts'),
    path('contracts/upload/', views.upload_contract, name='upload_contract'),
    path('contracts/clauses/<int:clause_id>/resolve/', views.resolve_clause, name='resolve_clause'),
    path('contracts/<int:doc_id>/reassign/', views.reassign_document_entity, name='reassign_document'),
    path('contracts/<int:doc_id>/download/', views.download_reviewed_document, name='download_reviewed_document'),

    # Pillar 2: Regulatory Intelligence Feed & Dispatch
    path('regulatory/', views.regulatory_view, name='regulatory'),
    path('regulatory/<int:update_id>/assess/', views.generate_impact_assessment, name='generate_impact_assessment'),
    path('regulatory/<int:update_id>/dispatch/', views.dispatch_impact_assessment, name='dispatch_impact_assessment'),

    # Pillar 3: Department Tasks & Evidence Hub
    path('tasks/', views.tasks_view, name='tasks'),
    path('tasks/<int:task_id>/toggle/', views.toggle_task_status, name='toggle_task_status'),
    path('tasks/<int:task_id>/evidence/', views.upload_task_evidence, name='upload_task_evidence'),

    # Pillar 4: Statutory Compliance Calendar
    path('calendar/', views.calendar_view, name='calendar'),

    # Pillar 5: Cryptographic Audit Trail & Defense Dossier
    path('audit/', views.audit_view, name='audit'),
    path('audit/dossier/', views.download_audit_dossier, name='download_audit_dossier'),

    # Governance & RBAC Access Matrix
    path('governance/', views.governance_view, name='governance'),
    path('governance/entity/add/', views.add_entity, name='add_entity'),
    path('governance/entity/<int:entity_id>/delete/', views.delete_entity, name='delete_entity'),
    path('governance/user/add/', views.add_user, name='add_user'),
    path('governance/user/<int:user_id>/delete/', views.delete_user, name='delete_user'),

    # Session Management
    path('session/switch-entity/', views.switch_active_entity, name='switch_entity'),
    path('session/switch-user/', views.switch_active_user, name='switch_user'),
]
