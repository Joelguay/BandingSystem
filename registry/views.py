from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import ChickenEditForm, ChickenRegistrationForm
from .models import AuditLog, Breeder, Chicken, OwnershipHistory
from .signals import log_action

# Dashboard

@login_required
def dashboard(request):
    """
    Home screen shown after login.
    Displays summary stat cards and the 5 most recently registered chickens.
    """
    return render(request, "registry/dashboard.html", {
        "page_title": "Dashboard",
        "total_chickens":  Chicken.objects.filter(is_active=True).count(),
        "total_breeders":  Breeder.objects.filter(is_active=True).count(),
        "total_transfers": OwnershipHistory.objects.count(),
        "recent_chickens": (
            Chicken.objects
            .filter(is_active=True)
            .select_related("breeder")
            .order_by("-created_at")[:5]
        ),
    })


# View 1 — Register Chicken

@login_required
def register_chicken(request):
    if request.method == "POST":
        form = ChickenRegistrationForm(request.POST)

        if form.is_valid():
            chicken = form.save()

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

            return redirect(
                f"{reverse('registry:verify_chicken')}?wingband={chicken.wingband_number}"
            )

    else:
        form = ChickenRegistrationForm()

    return render(request, "registry/register_chicken.html", {
        "form": form,
        "page_title": "Register Chicken",
    })


# View 2 — Verify Chicken

@login_required
def verify_chicken(request):

    chicken = None
    ownership_history = []
    search_term = request.GET.get("wingband", "").strip().upper()
    error_message = None

    if search_term:
        try:
            # Exact match only — wingband is an identifier, not a keyword.
            chicken = Chicken.objects.select_related("breeder").get(
                wingband_number=search_term,
                is_active=True,
            )
            ownership_history = chicken.ownership_history.select_related(
                "owner_breeder"
            ).all()

        except Chicken.DoesNotExist:
            error_message = (
                f'No active chicken found for wingband "{search_term}". '
                "Verify the number and try again."
            )

    return render(request, "registry/verify_chicken.html", {
        "page_title": "Verify Chicken",
        "search_term": search_term,
        "chicken": chicken,
        "ownership_history": ownership_history,
        "error_message": error_message,
    })

# View 3 — Chicken List

@login_required
def chicken_list(request):

    queryset = Chicken.objects.filter(is_active=True).select_related("breeder")

    # --- Optional filter: by Breeder ---
    breeder_id = request.GET.get("breeder", "").strip()
    if breeder_id.isdigit():
        queryset = queryset.filter(breeder_id=int(breeder_id))

    # --- Optional filter: by birth_category ---
    category = request.GET.get("category", "").strip().upper()
    if category in Chicken.BirthCategory.values:
        queryset = queryset.filter(birth_category=category)

    # --- Pagination ---
    paginator = Paginator(queryset, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    breeders = Breeder.objects.filter(is_active=True).order_by("name")

    return render(request, "registry/chicken_list.html", {
        "page_title": "Registered Chickens",
        "page_obj": page_obj,
        "breeders": breeders,
        "birth_categories": Chicken.BirthCategory.choices,
        
        # dropdowns selected after filtering.
        "selected_breeder": breeder_id,
        "selected_category": category,
    })


# View 4 — Soft Delete Chicken

@login_required
def soft_delete_chicken(request, pk):
    
    if request.method != "POST":
        return redirect("registry:chicken_list")

    chicken = get_object_or_404(Chicken, pk=pk)

    if not chicken.is_active:
        messages.warning(
            request,
            f"Chicken [{chicken.wingband_number}] is already inactive.",
        )
        return redirect("registry:chicken_list")

    wingband = chicken.wingband_number
    breeder_name = chicken.breeder.name

    chicken.delete()

    log_action(
        user=request.user,
        action=AuditLog.ActionType.DELETE,
        instance=chicken,
        details={
            "wingband_number": wingband,
            "breeder": breeder_name,
            "note": "soft-delete — record preserved in DB",
        },
    )

    # use warning (orange) instead of success (green).
    messages.warning(
        request,
        f"Chicken [{wingband}] has been deactivated. "
        "The record is preserved and can be restored via Django Admin.",
    )

    return redirect("registry:chicken_list")


# ===========================================================================
# View 5 — Edit Chicken (correction only)
# ===========================================================================

@login_required
def edit_chicken(request, pk):
    """
    Allow corrections to a chicken's physical attributes.

    IMMUTABLE FIELDS (enforced by ChickenEditForm exclusion):
        - wingband_number → never editable, ever
        - birth_category  → never editable, ever

    EDITABLE FIELDS (corrections only):
        - breeder, color, comb_type, leg_color

    Audit trail:
        Every save writes an UPDATE entry with a field-by-field diff:
        {
          "wingband_number": "WPC-001",
          "changed_fields": {
            "color": {"from": "Red", "to": "Black"},
            "breeder": {"from": "Juan dela Cruz", "to": "Pedro Reyes"}
          }
        }
        If nothing actually changed, no log entry is written.

    GET  → Show current values pre-filled in the edit form.
    POST → Validate, diff, save, log, redirect to verify page.
    """

    # Active-only — soft-deleted chickens cannot be edited
    chicken = get_object_or_404(Chicken, pk=pk, is_active=True)

    if request.method == "POST":
        form = ChickenEditForm(request.POST, instance=chicken)

        if form.is_valid():
            # ---------------------------------------------------------------
            # Capture BEFORE values for every changed field
            # Must happen BEFORE form.save() overwrites the instance.
            # ---------------------------------------------------------------
            changed_fields = {}
            for field_name in form.changed_data:
                # Get the human-readable "from" value
                display_method = f"get_{field_name}_display"
                if hasattr(chicken, display_method):
                    # Choice field → use Django's get_FOO_display()
                    old_value = getattr(chicken, display_method)()
                elif field_name == "breeder":
                    old_value = chicken.breeder.name if chicken.breeder else "—"
                else:
                    old_value = str(getattr(chicken, field_name))

                changed_fields[field_name] = {"from": old_value}

            # Now save — instance is updated in-place
            updated = form.save()

            # ---------------------------------------------------------------
            # Capture AFTER values for every changed field
            # ---------------------------------------------------------------
            for field_name in changed_fields:
                display_method = f"get_{field_name}_display"
                if hasattr(updated, display_method):
                    new_value = getattr(updated, display_method)()
                elif field_name == "breeder":
                    new_value = updated.breeder.name if updated.breeder else "—"
                else:
                    new_value = str(getattr(updated, field_name))

                changed_fields[field_name]["to"] = new_value

            # ---------------------------------------------------------------
            # Only log if something actually changed
            # (form.changed_data can sometimes be populated even if values
            #  are identical due to type coercion — the diff catches that)
            # ---------------------------------------------------------------
            actual_changes = {
                k: v for k, v in changed_fields.items()
                if v["from"] != v["to"]
            }

            if actual_changes:
                log_action(
                    user=request.user,
                    action=AuditLog.ActionType.UPDATE,
                    instance=updated,
                    details={
                        "wingband_number": updated.wingband_number,
                        "changed_fields": actual_changes,
                        "note": "correction edit via frontend",
                    },
                )
                messages.success(
                    request,
                    f"Chicken [{updated.wingband_number}] updated. "
                    f"{len(actual_changes)} field(s) changed.",
                )
            else:
                # No real changes — still redirect, but no log entry
                messages.info(request, "No changes were made.")

            return redirect(
                f"{reverse('registry:verify_chicken')}?wingband={updated.wingband_number}"
            )

    else:
        # GET — pre-fill form with current values
        form = ChickenEditForm(instance=chicken)

    return render(request, "registry/edit_chicken.html", {
        "form": form,
        "chicken": chicken,
        "page_title": f"Edit — {chicken.wingband_number}",
    })