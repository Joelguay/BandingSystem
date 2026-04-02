from django import forms

from .models import Breeder, Chicken


# Chicken Registration Form

class ChickenRegistrationForm(forms.ModelForm):

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
        wingband = self.cleaned_data.get("wingband_number", "").strip().upper()

        if Chicken.objects.filter(wingband_number=wingband).exists():
            raise forms.ValidationError(
                "This wingband number is already taken. "
                "Soft-deleted wingbands remain reserved until permanently deleted."
            )

        return wingband


# ===========================================================================
# Chicken Edit Form
# ===========================================================================

class ChickenEditForm(forms.ModelForm):
    """
    Form for correcting a chicken's physical attributes.

    PERMANENT EXCLUSIONS — these fields are NEVER in this form:
        - wingband_number : the chicken's identity — immutable by design
        - birth_category  : permanent classification — set once at registration

    Only allows corrections to: breeder, color, comb_type, leg_color.
    """

    class Meta:
        model = Chicken
        fields = ["breeder", "color", "comb_type", "leg_color"]
        # wingband_number and birth_category are intentionally absent

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only active breeders can receive reassigned chickens
        self.fields["breeder"].queryset = Breeder.objects.filter(is_active=True)
        self.fields["breeder"].empty_label = "— Select a Breeder —"
