from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Entity, Location


@admin.register(Entity)
class EntityAdmin(SimpleHistoryAdmin):
    list_display = ("name", "cin", "is_listed_parent")
    search_fields = ("name", "cin")


@admin.register(Location)
class LocationAdmin(SimpleHistoryAdmin):
    list_display = ("name", "node_type", "entity", "parent", "code", "is_active")
    list_filter = ("entity", "node_type", "is_active")
    search_fields = ("name", "code")
    autocomplete_fields = ("parent",)
