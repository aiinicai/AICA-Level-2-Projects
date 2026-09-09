from django.urls import path

from . import views

app_name = "verification"

urlpatterns = [
    path("scan/", views.scan_home, name="scan_home"),
    path("scan/lookup/<str:asset_id>/", views.scan_lookup, name="scan_lookup"),
    path("scan/submit/", views.scan_submit, name="scan_submit"),
    path("mismatches/", views.mismatch_queue, name="mismatch_queue"),
    path("mismatches/<int:pk>/resolve/", views.mismatch_resolve, name="mismatch_resolve"),

    path("cycles/", views.cycle_list, name="cycle_list"),
    path("cycles/new/", views.cycle_create, name="cycle_create"),
    path("cycles/<int:pk>/", views.cycle_detail, name="cycle_detail"),
    path("cycles/<int:pk>/verify/<str:asset_id>/", views.cycle_verify_asset, name="cycle_verify_asset"),
]
