from django.contrib import admin
from .models import AuditLog, Breeder, Chicken, OwnershipHistory

@admin.register(Breeder)
class BreederAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "contact", "is_active", "created_at")
    search_fields = ("name", "location", "contact")


@admin.register(Chicken)
class ChickenAdmin(admin.ModelAdmin):
    list_display = (
        "wingband_number",
        "breeder",
        "color",
        "comb_type",
        "leg_color",
        "birth_category",
        "is_active",
        "created_at",
    )

    search_fields = ("wingband_number", "breeder__name")


@admin.register(OwnershipHistory)
class OwnershipHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "chicken",
        "owner_name",
        "owner_breeder",
        "date_transferred",
        "recorded_at",
    )

    search_fields = ("chicken__wingband_number", "owner_name")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user", "action", "model_name", "record_id")
    search_fields = ("model_name", "record_id", "user__username")
