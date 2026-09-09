from django.urls import path

from . import views

app_name = "compliance"

urlpatterns = [
    path("", views.home, name="home"),
    path("schedule-iii/", views.schedule_iii, name="schedule_iii"),
    path("ind-as-16/", views.ind_as_16, name="ind_as_16"),
    path("caro-pack/", views.caro_pack, name="caro_pack"),
    path("verification-papers/", views.verification_papers, name="verification_papers"),
    path("xbrl-export/", views.xbrl_export, name="xbrl_export"),
    path("benami/new/", views.benami_declare, name="benami_declare"),
]
