from .models import AuditLog


def log_action(actor, action, metadata=None, ip=None):

    AuditLog.objects.create(
        actor=actor,
        action=action,
        metadata=metadata or {},
        ip_address=ip
    )