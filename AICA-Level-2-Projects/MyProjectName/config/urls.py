from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", views.dashboard, name="dashboard"),
    path("assets/", include("assets.urls")),
    path("locations/", include("locations.urls")),
    path("verification/", include("verification.urls")),
    path("transfers/", include("transfers.urls")),
    path("disposal/", include("disposal.urls")),
    path("compliance/", include("compliance.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
