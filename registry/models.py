from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


# Abstract Base: Soft Delete

class SoftDeleteModel(models.Model):
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Soft-delete flag. False means the record is deactivated, not removed.",
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of when this record was soft-deleted. NULL if still active.",
    )

    class Meta:
        abstract = True

    # Soft-delete lifecycle methods

    def delete(self, using=None, keep_parents=False):
        """Override default delete to perform a soft-delete instead."""
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_active", "deleted_at"])

    def hard_delete(self):
        """Permanently remove this record from the database. Use with caution."""
        super().delete()

    def restore(self):
        """Restore a previously soft-deleted record back to active state."""
        self.is_active = True
        self.deleted_at = None
        self.save(update_fields=["is_active", "deleted_at"])


# Breeder

class Breeder(SoftDeleteModel):
    name = models.CharField(
        max_length=255,
        help_text="Full name of the breeder or farm/stable owner.",
    )
    location = models.CharField(
        max_length=255,
        help_text="City, municipality, province, or region the breeder is based in.",
    )
    contact = models.CharField(
        max_length=100,
        blank=True,
        help_text="Phone number or email address (optional but recommended).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"], name="breeder_name_idx"),
            models.Index(fields=["is_active"], name="breeder_active_idx"),
        ]
        verbose_name = "Breeder"
        verbose_name_plural = "Breeders"

    def __str__(self) -> str:
        tag = "" if self.is_active else " [INACTIVE]"
        return f"{self.name}{tag}"


# Chicken

class Chicken(SoftDeleteModel):
    # Enumerated choices

    class FeatherColor(models.TextChoices):
        BLACK      = "BLACK",     "Black"
        WHITE      = "WHITE",     "White"
        RED        = "RED",       "Red"
        BROWN      = "BROWN",     "Brown"
        GREY       = "GREY",      "Grey"
        PYLE       = "PYLE",      "Pyle"
        SPANGLED   = "SPANGLED",  "Spangled"
        DARK_RED   = "DARK_RED",  "Dark Red"
        MIXED      = "MIXED",     "Mixed"
        OTHER      = "OTHER",     "Other"

    class CombType(models.TextChoices):
        SINGLE      = "SINGLE",      "Single"
        DUPLEX      = "DUPLEX",      "Duplex"
        STRAWBERRY  = "STRAWBERRY",  "Strawberry"
        WALNUT      = "WALNUT",      "Walnut"
        PEA         = "PEA",         "Pea"
        CUSHION     = "CUSHION",     "Cushion"
        ROSE        = "ROSE",        "Rose"

    class LegColor(models.TextChoices):
        YELLOW  = "YELLOW",  "Yellow"
        WHITE   = "WHITE",   "White"
        WILLOW  = "WILLOW",  "Willow"
        BLACK   = "BLACK",   "Black"
        BLUE    = "BLUE",    "Blue"
        MIXED   = "MIXED",   "Mixed"

    class BirthCategory(models.TextChoices):
        """
        Permanent birth-period classification assigned at registration.
        These are WPC-style date-based tiers and cannot be changed.
        """
        EARLY_BIRD  = "EARLY_BIRD",  "Early Bird"
        LOCAL       = "LOCAL",       "Local"
        NATIONAL    = "NATIONAL",    "National"
        LATE_BORN   = "LATE_BORN",   "Late Born"

    # Fields
    wingband_number = models.CharField(
        max_length=50,
        unique=True,    # Enforced at DB level — wingband is its own identity
        db_index=True,  # Indexed explicitly for O(log n) verification lookups
        help_text=(
            "Unique wingband identifier (primary lookup key). "
            "Cannot be reused while this record exists (even if soft-deleted)."
        ),
    )
    breeder = models.ForeignKey(
        Breeder,
        on_delete=models.PROTECT,  # Block hard-delete of a Breeder that owns chickens
        related_name="chickens",
        help_text="The registered breeder this chicken is assigned to.",
    )
    color = models.CharField(
        max_length=20,
        choices=FeatherColor.choices,
        help_text="Primary feather color of the gamefowl.",
    )
    comb_type = models.CharField(
        max_length=20,
        choices=CombType.choices,
        help_text="Physical comb type of the gamefowl.",
    )
    leg_color = models.CharField(
        max_length=20,
        choices=LegColor.choices,
        help_text="Shank (leg) color of the gamefowl.",
    )
    birth_category = models.CharField(
        max_length=20,
        choices=BirthCategory.choices,
        help_text=(
            "Permanent birth-period tier assigned at registration. "
            "This field MUST NOT be changed after the record is created."
        ),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this chicken was first registered in the system.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["wingband_number"]
        indexes = [
            # Composite index: filter by breeder + active status together
            models.Index(
                fields=["breeder", "is_active"],
                name="chicken_breeder_active_idx",
            ),
            models.Index(
                fields=["birth_category"],
                name="chicken_birth_category_idx",
            ),
        ]
        verbose_name = "Chicken"
        verbose_name_plural = "Chickens"

    def __str__(self) -> str:
        tag = "" if self.is_active else " [DELETED]"
        return (
            f"[{self.wingband_number}] "
            f"{self.get_color_display()} · "
            f"{self.get_comb_type_display()}"
            f"{tag}"
        )


# Ownership History

class OwnershipHistory(models.Model):

    chicken = models.ForeignKey(
        Chicken,
        on_delete=models.PROTECT,  # Preserve history even if chicken is soft-deleted
        related_name="ownership_history",
        help_text="The chicken involved in this ownership transfer.",
    )
    owner_breeder = models.ForeignKey(
        Breeder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,  # If Breeder is hard-deleted, keep the text record
        related_name="received_chickens",
        help_text="Link to the registered Breeder who received this chicken (optional).",
    )
    owner_name = models.CharField(
        max_length=255,
        help_text=(
            "Full name of the new owner (required). "
            "Auto-populate from owner_breeder.name if the FK is provided."
        ),
    )
    date_transferred = models.DateField(
        help_text="Actual date the ownership transfer took place. Can be backdated.",
    )
    recorded_at = models.DateTimeField(
        auto_now_add=True,
        help_text="System timestamp of when this record was entered. Auto-set, not editable.",
    )
    notes = models.TextField(
        blank=True,
        help_text="Optional context about the transfer (e.g., event name, derby, reason).",
    )

    class Meta:
        ordering = ["-date_transferred", "-recorded_at"]
        indexes = [
            models.Index(
                fields=["chicken", "date_transferred"],
                name="ownership_chicken_date_idx",
            ),
        ]
        verbose_name = "Ownership History"
        verbose_name_plural = "Ownership Histories"

    def __str__(self) -> str:
        return (
            f"{self.chicken.wingband_number} → "
            f"{self.owner_name} "
            f"(transferred: {self.date_transferred})"
        )


# Audit Log

class AuditLog(models.Model):

    class ActionType(models.TextChoices):
        CREATE    = "CREATE",    "Create"
        UPDATE    = "UPDATE",    "Update"
        DELETE    = "DELETE",    "Delete"    # Soft-delete
        RESTORE   = "RESTORE",   "Restore"   # Undo soft-delete
        TRANSFER  = "TRANSFER",  "Transfer"  # Ownership transfer

    user = models.ForeignKey(
        User,
        null=True,   # Nullable for safety — never set to NULL intentionally
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        help_text="The admin user who triggered this action.",
    )
    action = models.CharField(
        max_length=20,
        choices=ActionType.choices,
        help_text="The type of action that was performed.",
    )
    model_name = models.CharField(
        max_length=100,
        help_text="Name of the affected model class (e.g., 'Chicken', 'Breeder').",
    )
    record_id = models.PositiveBigIntegerField(
        help_text="Primary key (ID) of the affected record.",
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Structured context about the action. "
            "e.g., {'wingband': 'WB-001', 'changed_fields': ['breeder']}."
        ),
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when this audit entry was created.",
    )

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            # Fast lookup: "show me all logs for this specific record"
            models.Index(
                fields=["model_name", "record_id"],
                name="auditlog_model_record_idx",
            ),
            # Fast lookup: "show me everything this admin did and when"
            models.Index(
                fields=["user", "timestamp"],
                name="auditlog_user_time_idx",
            ),
        ]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"

    def __str__(self) -> str:
        actor = self.user.username if self.user else "System"
        return (
            f"[{self.timestamp:%Y-%m-%d %H:%M}] "
            f"{actor} → {self.action} "
            f"{self.model_name} #{self.record_id}"
        )
