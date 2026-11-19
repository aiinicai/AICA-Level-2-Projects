from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("signup/", views.signup_view, name="signup"),
    path("signup/subdomain-check/", views.subdomain_check, name="subdomain_check"),
    path("team/", views.team_list, name="team_list"),
    path("team/invite/", views.team_invite, name="team_invite"),
    path("team/<int:pk>/toggle-active/", views.team_toggle_active, name="team_toggle_active"),
    path("team/<int:pk>/toggle-role/", views.team_toggle_role, name="team_toggle_role"),
    path("settings/", views.firm_settings, name="firm_settings"),
    path("signature/", views.firm_signature, name="firm_signature"),
]
