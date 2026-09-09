from django.urls import path

from . import views

app_name = "assets"

urlpatterns = [
    path("", views.asset_list, name="list"),
    path("new/", views.asset_create, name="create"),

    # NOTE: every literal-prefix path below (cwip/, capex/, labels/, revaluation/,
    # impairment/, approvals/, depreciation/, bulk/) must be registered BEFORE the
    # catch-all "<str:asset_id>/" patterns further down — otherwise Django matches
    # e.g. "cwip/" as asset_detail(asset_id="cwip") and 404s.
    path("cwip/", views.cwip_list, name="cwip_list"),
    path("cwip/new/", views.cwip_create, name="cwip_create"),
    path("cwip/<int:pk>/", views.cwip_detail, name="cwip_detail"),
    path("cwip/<int:pk>/capitalise/", views.cwip_capitalise, name="cwip_capitalise"),

    path("capex/", views.capex_list, name="capex_list"),
    path("capex/new/", views.capex_create, name="capex_create"),
    path("capex/<int:pk>/decide/", views.capex_decide, name="capex_decide"),

    path("labels/print/", views.label_print, name="label_print"),

    path("revaluation/", views.revaluation_list, name="revaluation_list"),
    path("revaluation/new/", views.revaluation_create, name="revaluation_create"),
    path("revaluation/<int:pk>/decide/", views.revaluation_decide, name="revaluation_decide"),
    path("impairment/new/<str:asset_id>/", views.impairment_create, name="impairment_create"),

    path("approvals/", views.approval_inbox, name="approval_inbox"),
    path("approvals/<int:pk>/decide/", views.approval_decide, name="approval_decide"),

    path("depreciation/run/", views.depreciation_run, name="depreciation_run"),

    path("bulk/", views.bulk_import, name="bulk_import"),
    path("bulk/template.csv", views.bulk_template, name="bulk_template"),
    path("bulk/export.csv", views.bulk_export, name="bulk_export"),

    # Catch-all asset-detail routes — must stay last.
    path("<str:asset_id>/", views.asset_detail, name="detail"),
    path("<str:asset_id>/edit/", views.asset_edit, name="edit"),
    path("<str:asset_id>/qr.png", views.asset_qr_png, name="qr_png"),
    path("<str:asset_id>/documents/upload/", views.document_upload, name="document_upload"),
]
