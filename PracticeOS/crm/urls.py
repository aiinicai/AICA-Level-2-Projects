from django.urls import path

from . import views

urlpatterns = [
    path("clients/", views.client_list, name="client_list"),
    path("clients/new/", views.client_create, name="client_create"),
    path("clients/<int:pk>/", views.client_detail, name="client_detail"),
    path("clients/<int:pk>/edit/", views.client_edit, name="client_edit"),
    path("clients/<int:pk>/archive/", views.client_set_active, {"active": False}, name="client_archive"),
    path("clients/<int:pk>/restore/", views.client_set_active, {"active": True}, name="client_restore"),
    path("clients/<int:pk>/services/new/", views.service_form, name="service_create"),
    path("clients/<int:pk>/services/<int:service_pk>/edit/", views.service_form, name="service_edit"),
    path("clients/<int:pk>/services/<int:service_pk>/delete/", views.service_delete, name="service_delete"),
]
