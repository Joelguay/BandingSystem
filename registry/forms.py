"""
Forms for the Gamefowl Banding Registration System.

Why forms exist separately from views:
    - Keeps validation logic out of views (views should only control flow)
    - Reusable across multiple views (admin panel, API, future CLI tools)
    - Gives friendly error messages before hitting the DB unique constraint
"""

from django import forms

from .models import Breeder, Chicken


# Chicken Registration Form

class ChickenRegistrationForm(forms.ModelForm):
    """
    Form for registering a new gamefowl.

    Key behaviors:
        - wingband_number is validated for uniqueness BEFORE hitting the DB.
          This prevents a raw IntegrityError crash and returns a clean field error.
        - birth_category is shown on creation only. It must NOT be editable
          after the record is saved (enforced in the view, not the form).
        - breeder dropdown only shows ACTIVE breeders. Inactive (soft-deleted)
          breeders cannot receive new chickens.
    """

    class Meta:
        model = Chicken
        fields = [
            "wingband_number",
            "breeder",
            "color",
            "comb_type",
            "leg_color",
            "birth_category",
        ]
        widgets = {
            # Use text inputs with explicit placeholders for clarity
            "wingband_number": forms.TextInput(attrs={
                "placeholder": "e.g. WPC-2024-001",
                "autofocus": True,
            }),
        }
        error_messages = {
            # Override Django's default "already exists" DB error with a
            # clear, admin-friendly message tied directly to the field.
            "wingband_number": {
                "unique": (
                    "This wingband number is already registered. "
                    "If the chicken was soft-deleted, it must be permanently "
                    "removed before this number can be reused."
                ),
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Only show ACTIVE breeders in the dropdown.
        # An inactive breeder cannot receive or own new chickens.
        self.fields["breeder"].queryset = Breeder.objects.filter(is_active=True)
        self.fields["breeder"].empty_label = "— Select a Breeder —"

    def clean_wingband_number(self):
        """
        Explicit uniqueness check that runs BEFORE the DB constraint fires.

        Why: Django's ModelForm already handles unique fields, but this
        check runs in Python so we can provide a better error message and
        catch it at the field level (not as a non-field error).

        The check includes ALL records (active AND soft-deleted) because a
        soft-deleted wingband is still reserved until permanently removed.
        """
        wingband = self.cleaned_data.get("wingband_number", "").strip().upper()

        if Chicken.objects.filter(wingband_number=wingband).exists():
            raise forms.ValidationError(
                "This wingband number is already taken. "
                "Soft-deleted wingbands remain reserved until permanently deleted."
            )

        return wingband
