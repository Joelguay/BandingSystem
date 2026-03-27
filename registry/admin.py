from django.contrib import admin

from .models import AuditLog, Breeder, Chicken, OwnershipHistory

# Breeder Admin

@admin.register(Breeder)
class BreederAdmin(admin.ModelAdmin):

    list_display = ("name", "location", "contact", "is_active", "created_at")
    search_fields = ("name", "location", "contact")
    list_filter = ("is_active",)
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    ordering = ("-created_at",)
    list_per_page = 25

# Chicken Admin

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

    list_filter = ("birth_category", "is_active", "color", "breeder")

    readonly_fields = (
        "birth_category",
        "created_at",
        "updated_at",
        "deleted_at",
    )

    ordering = ("-created_at",)
    list_per_page = 25

# Ownership History Admin

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
    list_filter = ("date_transferred", "owner_breeder")

    readonly_fields = (
        "chicken",
        "owner_breeder",
        "owner_name",
        "date_transferred",
        "recorded_at",
        "notes",
    )

    ordering = ("-date_transferred", "-recorded_at")
    list_per_page = 25

# Audit Log Admin

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):

    list_display = ("timestamp", "user", "action", "model_name", "record_id")
    search_fields = ("model_name", "record_id", "user__username")
    list_filter = ("action", "model_name")

    readonly_fields = (
        "user",
        "action",
        "model_name",
        "record_id",
        "details",
        "timestamp",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    ordering = ("-timestamp",)
    list_per_page = 50  
