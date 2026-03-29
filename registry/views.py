"""
Views for the Gamefowl Banding Registration and Verification System.

All views are:
    - Protected by @login_required (admin-only system)
    - Function-based (simpler, easier to follow the exact logic flow)
    - Responsible for calling log_action() after every state change

Pattern used throughout:
    GET  → render the form/page
    POST → process the action, then redirect (PRG pattern)
          PRG = Post/Redirect/Get — prevents duplicate submissions on refresh
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ChickenRegistrationForm
from .models import AuditLog, Chicken
from .signals import log_action


# ===========================================================================
# View 1 — Register Chicken
# ===========================================================================

@login_required
def register_chicken(request):
    """
    Register a new gamefowl with a unique wingband number.

    GET  → Display the blank registration form.
    POST → Validate and save. On success, redirect to the verify page
           pre-filled with the new wingband so the admin can immediately
           confirm the record was saved correctly.

    AuditLog: A CREATE entry is written after every successful save.
    """

    if request.method == "POST":
        form = ChickenRegistrationForm(request.POST)

        if form.is_valid():
            # Save the chicken — birth_category is permanent from this point on.
            # The form's clean_wingband_number() already confirmed uniqueness,
            # but the DB unique constraint is the final safety net below.
            chicken = form.save()

            # Write a CREATE audit log entry.
            # details stores the wingband so the log is useful without
            # having to look up the record separately.
            log_action(
                user=request.user,
                action=AuditLog.ActionType.CREATE,
                instance=chicken,
                details={
                    "wingband_number": chicken.wingband_number,
                    "breeder": chicken.breeder.name,
                    "birth_category": chicken.birth_category,
                },
            )

            # Success message displayed on the verify page.
            messages.success(
                request,
                f"Chicken [{chicken.wingband_number}] registered successfully.",
            )

            # PRG: Redirect to verify page pre-filled with the new wingband.
            # The admin can immediately confirm the record is searchable.
            return redirect(
                f"{request.build_absolute_uri('/chickens/verify/')}?wingband={chicken.wingband_number}"
            )

        # Form is invalid — fall through and re-render with errors.
        # Django's form object already has the error messages attached.

    else:
        # GET request — show a fresh blank form.
        form = ChickenRegistrationForm()

    return render(request, "registry/register_chicken.html", {
        "form": form,
        "page_title": "Register Chicken",
    })