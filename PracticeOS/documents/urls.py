from django.urls import path

from . import views

urlpatterns = [
    path("documents/", views.document_list, name="document_list"),
    path("documents/new/", views.document_create, name="document_create"),
    path("documents/<int:pk>/download/", views.download, name="document_download"),
    path("documents/<int:pk>/share/", views.toggle_share, name="document_share"),
    path("documents/<int:pk>/delete/", views.document_delete, name="document_delete"),
]
