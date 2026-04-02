from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import ChickenRegistrationForm
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