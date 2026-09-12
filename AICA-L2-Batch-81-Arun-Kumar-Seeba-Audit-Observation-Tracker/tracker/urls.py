from django.urls import path
from tracker import views

urlpatterns = [
    # Auth & Admin User Management
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('force-password-change/', views.force_password_change, name='force_password_change'),
    path('admin/users/', views.admin_users_view, name='admin_users'),
    path('admin/users/<int:user_id>/unlock/', views.admin_unlock_user, name='admin_unlock_user'),

    # Dashboards
    path('', views.dashboard_view, name='dashboard'),

    # Masters: Clients & Contacts
    path('clients/', views.client_list, name='client_list'),
    path('clients/create/', views.client_create, name='client_create'),
    path('clients/<int:pk>/edit/', views.client_edit, name='client_edit'),
    path('clients/<int:client_id>/contact/create/', views.contact_create, name='contact_create'),
    path('contacts/<int:contact_id>/edit/', views.contact_edit, name='contact_edit'),
    path('contacts/<int:contact_id>/delete/', views.contact_delete, name='contact_delete'),

    # Masters: Staff
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/create/', views.staff_create, name='staff_create'),
    path('staff/<int:pk>/edit/', views.staff_edit, name='staff_edit'),

    # Engagements & Teams
    path('engagements/', views.engagement_list, name='engagement_list'),
    path('engagements/create/', views.engagement_create, name='engagement_create'),
    path('engagements/<int:pk>/', views.engagement_detail, name='engagement_detail'),
    path('engagements/<int:pk>/edit/', views.engagement_edit, name='engagement_edit'),
    path('engagements/<int:engagement_id>/team/assign/', views.team_assign, name='team_assign'),
    path('team/<int:assignment_id>/edit/', views.team_edit, name='team_edit'),
    path('team/<int:assignment_id>/release/', views.team_release, name='team_release'),
    path('team/<int:assignment_id>/independence/', views.declare_independence, name='declare_independence'),

    # Queries Lifecycle
    path('queries/', views.query_list, name='query_list'),
    path('queries/create/', views.query_create, name='query_create'),
    path('queries/create/<int:engagement_id>/', views.query_create, name='query_create_with_eng'),
    path('queries/<int:pk>/', views.query_detail, name='query_detail'),
    path('queries/<int:pk>/edit/', views.query_edit, name='query_edit'),
    path('queries/<int:pk>/transition/<str:target_status>/', views.query_transition_action, name='query_transition'),
    path('queries/<int:pk>/response/', views.query_post_response, name='query_post_response'),
    path('queries/export/excel/', views.query_export_excel_view, name='query_export_excel'),

    # Exception Approvals
    path('exceptions/', views.exception_list, name='exception_list'),
    path('exceptions/queue/', views.exception_queue, name='exception_queue'),
    path('exceptions/request/<int:engagement_id>/', views.exception_request, name='exception_request'),
    path('exceptions/<int:pk>/decision/', views.exception_decision, name='exception_decision'),

    # Audit Summary Memo
    path('memos/<int:engagement_id>/', views.memo_hub, name='memo_hub'),
    path('memos/<int:engagement_id>/generate/', views.memo_generate, name='memo_generate'),
    path('memos/<int:engagement_id>/signoff/', views.memo_signoff, name='memo_signoff'),
    path('memos/download/<int:memo_id>/', views.memo_download, name='memo_download'),

    # Notifications & Audit Trail
    path('notifications/', views.notifications_view, name='notifications'),
    path('audit-trail/', views.audit_trail_view, name='audit_trail'),
]
