from django.urls import include, path

urlpatterns = [
    path("", include("core.urls")),
    path("", include("accounts.urls")),
    path("", include("crm.urls")),
    path("", include("workflow.urls")),
    path("", include("documents.urls")),
    path("", include("billing.urls")),
]
