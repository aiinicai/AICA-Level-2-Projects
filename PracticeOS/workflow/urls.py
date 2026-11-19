from django.urls import path

from . import views

urlpatterns = [
    path("tasks/", views.board, name="board"),
    path("tasks/new/", views.task_form, name="task_create"),
    path("tasks/<int:pk>/edit/", views.task_form, name="task_edit"),
    path("tasks/<int:pk>/delete/", views.task_delete, name="task_delete"),
    path("tasks/<int:pk>/status/", views.task_status, name="task_status"),
    path("tasks/recurring/", views.recurring_list, name="recurring_list"),
    path("tasks/recurring/new/", views.recurring_create, name="recurring_create"),
    path("tasks/recurring/run/", views.recurring_run, name="recurring_run"),
    path("tasks/recurring/<int:pk>/toggle/", views.recurring_toggle, name="recurring_toggle"),
    path("tasks/recurring/<int:pk>/delete/", views.recurring_delete, name="recurring_delete"),
]
