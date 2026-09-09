from django.urls import path

from . import views

app_name = "locations"

urlpatterns = [
    path("tree/", views.tree_view, name="tree"),
    path("tree/<int:pk>/", views.node_detail, name="node_detail"),
    path("locator/", views.locator, name="locator"),
]
