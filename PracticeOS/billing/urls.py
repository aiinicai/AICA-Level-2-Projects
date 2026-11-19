from django.urls import path

from . import views

urlpatterns = [
    path("time/", views.time_list, name="time_list"),
    path("time/new/", views.time_form, name="time_create"),
    path("time/<int:pk>/edit/", views.time_form, name="time_edit"),
    path("time/<int:pk>/delete/", views.time_delete, name="time_delete"),
    path("invoices/", views.invoice_list, name="invoice_list"),
    path("invoices/new/", views.invoice_create, name="invoice_create"),
    path("invoices/from-time/", views.invoice_from_time, name="invoice_from_time"),
    path("invoices/<int:pk>/", views.invoice_detail, name="invoice_detail"),
    path("invoices/<int:pk>/pay/", views.invoice_pay, name="invoice_pay"),
    path("invoices/<int:pk>/cancel/", views.invoice_cancel, name="invoice_cancel"),
    path("invoices/<int:pk>/send-email/", views.invoice_send_email, name="invoice_send_email"),
]
