from django.apps import AppConfig


class RegistryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "registry"
    verbose_name = "Gamefowl Registry"

    def ready(self):
        """
        Step 3: App startup hook.

        NOTE: We do NOT import signals.py here.

        Reason: Our audit logging uses a direct helper function (log_action)
        called explicitly from each view — not Django's post_save/post_delete
        signal system. This means:
            - No need to auto-register receivers on app startup
            - No import required here

        If we ever switch to signal-based logging in the future, add:
            import registry.signals  # noqa: F401
        """
        pass
