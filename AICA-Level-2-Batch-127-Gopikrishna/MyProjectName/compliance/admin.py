from django.contrib import admin

from .models import BenamiDeclaration, FinancialYear


@admin.register(FinancialYear)
class FinancialYearAdmin(admin.ModelAdmin):
    list_display = ("entity", "label", "start_date", "end_date", "is_closed")
    list_filter = ("entity", "is_closed")


@admin.register(BenamiDeclaration)
class BenamiDeclarationAdmin(admin.ModelAdmin):
    list_display = ("entity", "financial_year", "proceedings_exist", "declared_by", "declared_at")
