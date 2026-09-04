from django.urls import path

from . import views

app_name = "transfers"

urlpatterns = [
    path("", views.transfer_list, name="list"),
    path("new/", views.transfer_create, name="create"),
    path("<int:pk>/sign-off/", views.transfer_sign_off, name="sign_off"),
]
