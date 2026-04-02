from django.urls import path

from . import views

app_name = "registry"

urlpatterns = [
    # Root — Dashboard
    path("", views.dashboard, name="dashboard"),

    #Chicken List (dashboard)
    path("chickens/", views.chicken_list, name="chicken_list"),

    #Register a new chicken
    path("chickens/add/", views.register_chicken, name="register_chicken"),

    #Verify a chicken by wingband
    path("chickens/verify/", views.verify_chicken, name="verify_chicken"),

    # Autocomplete — JSON endpoint for wingband prefix search
    # Usage: GET /chickens/autocomplete/?q=WPC-2024
    path("chickens/autocomplete/", views.wingband_autocomplete, name="wingband_autocomplete"),

    # Soft delete a chicken
    path("chickens/<int:pk>/delete/", views.soft_delete_chicken, name="soft_delete_chicken"),

    # Edit a chicken (correction only — wingband and birth_category are immutable)
    path("chickens/<int:pk>/edit/", views.edit_chicken, name="edit_chicken"),
]
