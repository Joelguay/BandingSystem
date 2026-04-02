from django.contrib import admin

from .models import AuditLog, Breeder, Chicken, OwnershipHistory
from .signals import log_action


# ===========================================================================
# Breeder Admin — with full AuditLog integration
# ===========================================================================

@admin.register(Breeder)
class BreederAdmin(admin.ModelAdmin):

    list_display = ("name", "location", "contact", "is_active", "created_at")
    search_fields = ("name", "location", "contact")
    list_filter = ("is_active",)
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    ordering = ("-created_at",)
    list_per_page = 25

    def save_model(self, request, obj, form, change):
        """
        Hook called by Django Admin every time a Breeder is saved.
        'change=True'  → UPDATE (existing record edited)
        'change=False' → CREATE (new record being added)
        """
        super().save_model(request, obj, form, change)

        action = AuditLog.ActionType.UPDATE if change else AuditLog.ActionType.CREATE
        details = {"name": obj.name, "location": obj.location}

        if change and form.changed_data:
            # Record which fields were changed for the UPDATE log
            details["changed_fields"] = form.changed_data

        log_action(user=request.user, action=action, instance=obj, details=details)

    def delete_model(self, request, obj):
        """
        Hook called when a single Breeder is deleted via the admin detail page.
        Captures name before delete since soft-delete preserves the row.
        """
        details = {
            "name": obj.name,
            "location": obj.location,
            "note": "soft-deleted via Django Admin",
        }
        super().delete_model(request, obj)  # triggers SoftDeleteModel.delete()
        log_action(user=request.user, action=AuditLog.ActionType.DELETE, instance=obj, details=details)


# ===========================================================================
# Chicken Admin — with full AuditLog integration
# ===========================================================================

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
        # These two can NEVER be edited — enforced here at the admin level
        "wingband_number",
        "birth_category",
        # Timestamps
        "created_at",
        "updated_at",
        "deleted_at",
    )

    ordering = ("-created_at",)
    list_per_page = 25

    def save_model(self, request, obj, form, change):
        """
        Logs all Chicken saves done via Django Admin.
        Captures which fields changed on UPDATE.
        """
        super().save_model(request, obj, form, change)

        action = AuditLog.ActionType.UPDATE if change else AuditLog.ActionType.CREATE
        details = {"wingband_number": obj.wingband_number}

        if change and form.changed_data:
            details["changed_fields"] = form.changed_data

        log_action(user=request.user, action=action, instance=obj, details=details)

    def delete_model(self, request, obj):
        """
        Logs single-record soft-deletes done via Django Admin detail page.
        """
        details = {
            "wingband_number": obj.wingband_number,
            "breeder": obj.breeder.name,
            "note": "soft-deleted via Django Admin",
        }
        super().delete_model(request, obj)
        log_action(user=request.user, action=AuditLog.ActionType.DELETE, instance=obj, details=details)


# ===========================================================================
# Ownership History Admin — append-only, no saving hooks needed
# ===========================================================================

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

    # All fields are read-only — ownership history is append-only
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


# ===========================================================================
# Audit Log Admin — immutable, no add/delete, all fields read-only
# ===========================================================================

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):

    list_display = ("timestamp", "user", "action", "model_name", "record_id", "details")
    search_fields = ("model_name", "record_id", "user__username")
    list_filter = ("action", "model_name")

    # Every field is read-only — no human can change an audit log entry
    readonly_fields = (
        "user",
        "action",
        "model_name",
        "record_id",
        "details",
        "timestamp",
    )

    # No one can manually add or delete audit log entries
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # No one can change an existing audit log entry
    def has_change_permission(self, request, obj=None):
        return False

    ordering = ("-timestamp",)
    list_per_page = 50
