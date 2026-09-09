from django.urls import path

from . import views

app_name = "disposal"

urlpatterns = [
    path("", views.disposal_list, name="list"),
    path("new/", views.disposal_create, name="create"),
    path("<int:pk>/decide/", views.disposal_decide, name="decide"),
]
