from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from app.models import ParentAccess, ParentPortalAudit
from app.models.students import normalize_guardian_contact


def _normalized_name(value):
    return " ".join(str(value or "").casefold().split())


class ParentAccessError(ValueError):
    pass


def parent_username(contact):
    normalized = normalize_guardian_contact(contact)
    if not normalized:
        raise ParentAccessError("The student has no usable guardian contact.")
    return normalized


@transaction.atomic
def activate_parent_access(*, student, verified_by, allow_guardian_mismatch=False):
    """Create/reuse a portal login from the guardian data already on Student."""
    username = parent_username(student.contact)
    if not student.is_active:
        raise ParentAccessError("Parent access cannot be activated for an inactive student.")
    user = User.objects.select_for_update().filter(username=username).first()
    if user and hasattr(user, "staff_account"):
        raise ParentAccessError("That contact is already used by a staff login.")
    existing_accesses = ParentAccess.objects.select_related("student").filter(user=user) if user else ParentAccess.objects.none()
    if user and not existing_accesses.exists():
        raise ParentAccessError("That contact belongs to an existing non-parent account. Use a different contact or review the account manually.")
    guardian_names = {
        _normalized_name(access.student.guardian)
        for access in existing_accesses
        if access.student_id and access.student_id != student.pk
    }
    if guardian_names and _normalized_name(student.guardian) not in guardian_names and not allow_guardian_mismatch:
        raise ParentAccessError("This telephone number is already linked to a different guardian name. Confirm the identity in parent account management.")
    is_new_user = user is None
    has_live_access = bool(user and ParentAccess.objects.filter(user=user, is_active=True, is_verified=True).exists())
    if is_new_user:
        user = User(username=username, first_name=student.guardian[:150], is_active=True)
    user.is_active = True
    if not has_live_access:
        user.set_password("123")
    user.save()

    requires_change = not has_live_access
    expiry = timezone.now() + timedelta(hours=settings.PARENT_TEMP_PASSWORD_HOURS) if requires_change else None
    access, _ = ParentAccess.objects.update_or_create(
        user=user,
        student=student,
        defaults={
            "is_verified": True,
            "is_active": True,
            "must_change_password": requires_change,
            "temporary_password_expires_at": expiry,
            "verified_by": verified_by,
            "verified_at": timezone.now(),
        },
    )
    ParentPortalAudit.objects.create(
        user=user, student=student, action=ParentPortalAudit.ACTION_ACTIVATED,
        details={
            "verified_by": verified_by.pk,
            "temporary_password_expires_at": expiry.isoformat() if expiry else None,
            "existing_parent_account": has_live_access,
            "shared_contact_identity_confirmed": bool(allow_guardian_mismatch),
        },
    )
    return access


@transaction.atomic
def deactivate_parent_access(*, access_id, actor, reason=""):
    access = ParentAccess.objects.select_for_update().select_related("user", "student").get(pk=access_id)
    access.is_active = False
    access.save(update_fields=("is_active", "updated_at"))
    if not ParentAccess.objects.filter(user=access.user, is_active=True, is_verified=True).exists():
        access.user.is_active = False
        access.user.save(update_fields=("is_active",))
    ParentPortalAudit.objects.create(
        user=access.user, student=access.student, action=ParentPortalAudit.ACTION_DEACTIVATED,
        details={"actor": actor.pk, "reason": reason[:500]},
    )
    return access


@transaction.atomic
def reset_parent_password(*, user_id, actor):
    user = User.objects.select_for_update().get(pk=user_id)
    accesses = ParentAccess.objects.select_for_update().filter(user=user, is_active=True, is_verified=True)
    if not accesses.exists():
        raise ParentAccessError("This parent account has no active verified student access.")
    user.set_password("123")
    user.is_active = True
    user.save(update_fields=("password", "is_active"))
    expiry = timezone.now() + timedelta(hours=settings.PARENT_TEMP_PASSWORD_HOURS)
    accesses.update(must_change_password=True, temporary_password_expires_at=expiry)
    ParentPortalAudit.objects.create(
        user=user, action=ParentPortalAudit.ACTION_PASSWORD_RESET,
        details={"actor": actor.pk, "temporary_password_expires_at": expiry.isoformat()},
    )
    return user


def active_parent_accesses(user):
    return ParentAccess.objects.filter(
        user=user, is_active=True, is_verified=True, student__is_active=True,
    ).select_related("student", "student__current_class", "student__stream")


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")) or None
