from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "FAR profile",
            {"fields": ("employee_id", "designation", "department", "is_active_custodian")},
        ),
    )
    list_display = (
        "username",
        "get_full_name",
        "department",
        "designation",
        "is_active_custodian",
        "is_staff",
    )
    list_filter = BaseUserAdmin.list_filter + ("department", "is_active_custodian")
