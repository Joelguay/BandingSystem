import logging

from .models import AuditLog

logger = logging.getLogger(__name__)


def log_action(user, action, instance, details=None):
    if details is None:
        details = {}
    if user is None:
        logger.warning(
            "log_action called with user=None for action=%s on %s #%s. "
            "This should never happen in application code.",
            action,
            instance.__class__.__name__,
            instance.pk,
        )

    try:
        entry = AuditLog.objects.create(
            user=user,
            action=action,
            model_name=instance.__class__.__name__,   # e.g. "Chicken"
            record_id=instance.pk,                    # e.g. 42
            details=details,
        )
        return entry

    except Exception as exc:
        # Logging must NEVER crash the main request.
        logger.error(
            "Failed to create AuditLog entry for action=%s on %s #%s: %s",
            action,
            instance.__class__.__name__,
            instance.pk,
            exc,
        )
        return None
