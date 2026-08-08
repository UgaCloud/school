from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Avg, Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from app.decorators.decorators import role_required_any
from app.decorators.features import feature_required
from app.decorators.parent_portal import parent_required
from app.forms.parent_portal import (
    ParentAccessPermissionsForm, ParentConversationStartForm, ParentFirstPasswordForm,
    ParentLoginForm, ParentMessageForm,
)
from app.models import (
    Announcement, AttendanceRecord, LibraryLoan, Message, ParentAccess, ParentConversation,
    ParentNotification, ParentPortalAudit, Result, Student, Term,
)
from app.services.parent_portal import (
    ParentAccessError, activate_parent_access, active_parent_accesses, client_ip,
    deactivate_parent_access, eligible_parent_teachers, parent_username, reset_parent_password,
    start_parent_conversation, sync_parent_notifications,
)
from app.utils.pdf_utils import generate_student_report_pdf


PARENT_MANAGEMENT_ROLES = ("Admin", "Head Teacher", "Head master", "Director of Studies")


def _rate_key(request, phone):
    return f"parent-login:{client_ip(request)}:{phone}"


@feature_required("PARENT_PORTAL_ENABLED")
def parent_login(request):
    if request.user.is_authenticated and active_parent_accesses(request.user).exists():
        return redirect("parent_dashboard")
    form = ParentLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            username = parent_username(form.cleaned_data["phone"])
        except ParentAccessError:
            username = ""
        key = _rate_key(request, username)
        failures = int(cache.get(key, 0))
        if failures >= settings.PARENT_LOGIN_MAX_ATTEMPTS:
            form.add_error(None, "Too many failed attempts. Try again later or contact the school.")
        else:
            user = authenticate(request, username=username, password=form.cleaned_data["password"])
            accesses = active_parent_accesses(user) if user else ParentAccess.objects.none()
            expired = bool(user and accesses.filter(must_change_password=True, temporary_password_expires_at__lte=timezone.now()).exists())
            if user and accesses.exists() and not expired:
                cache.delete(key)
                login(request, user)
                ParentPortalAudit.objects.create(user=user, action=ParentPortalAudit.ACTION_LOGIN, ip_address=client_ip(request))
                return redirect("parent_force_password" if accesses.filter(must_change_password=True).exists() else "parent_dashboard")
            cache.set(key, failures + 1, settings.PARENT_LOGIN_LOCK_SECONDS)
            ParentPortalAudit.objects.create(
                user=user, action=ParentPortalAudit.ACTION_LOGIN_FAILED, ip_address=client_ip(request),
                details={"username": username, "expired": expired},
            )
            form.add_error(None, "Invalid or expired credentials. Contact the school if this continues.")
    return render(request, "parent_portal/login.html", {"form": form})


@feature_required("PARENT_PORTAL_ENABLED")
@login_required
def parent_force_password(request):
    accesses = active_parent_accesses(request.user)
    if not accesses.exists():
        return redirect("parent_login")
    if not accesses.filter(must_change_password=True).exists():
        return redirect("parent_dashboard")
    if accesses.filter(temporary_password_expires_at__lte=timezone.now()).exists():
        logout(request)
        messages.error(request, "The temporary password expired. Ask the school to reactivate access.")
        return redirect("parent_login")
    form = ParentFirstPasswordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        request.user.set_password(form.cleaned_data["password"])
        request.user.save(update_fields=["password"])
        accesses.update(must_change_password=False, temporary_password_expires_at=None)
        ParentPortalAudit.objects.create(user=request.user, action=ParentPortalAudit.ACTION_PASSWORD_CHANGED, ip_address=client_ip(request))
        update_session_auth_hash(request, request.user)
        return redirect("parent_dashboard")
    return render(request, "parent_portal/force_password.html", {"form": form})


def _selected_access(request, student_id=None):
    qs = getattr(request, "parent_accesses", active_parent_accesses(request.user))
    return get_object_or_404(qs, student_id=student_id) if student_id else qs.first()


@feature_required("PARENT_PORTAL_ENABLED")
@parent_required
def parent_dashboard(request):
    sync_parent_notifications(request.user)
    selected = request.GET.get("student", "")
    access = _selected_access(request, selected if selected.isdigit() else None)
    student = access.student
    bills = student.bills.prefetch_related("items", "payments", "applied_credits") if access.can_view_finance else []
    balance = sum((bill.balance for bill in bills), 0)
    attendance = student.attendance_records.exclude(status="unmarked") if access.can_view_attendance else AttendanceRecord.objects.none()
    attendance_total = attendance.count()
    present = attendance.filter(status__in=("present", "late")).count()
    attendance_percent = round((present / attendance_total) * 100, 1) if attendance_total else None
    recent_results = Result.objects.none()
    academic_average = None
    if access.can_view_academics:
        verified_results = Result.objects.filter(student=student, status="VERIFIED")
        academic_average = verified_results.aggregate(value=Avg("score"))["value"]
        recent_results = verified_results.select_related(
            "assessment__subject", "assessment__assessment_type"
        ).order_by("-assessment__date")[:8]
    announcements = Announcement.objects.filter(is_active=True, audience="all", starts_at__lte=timezone.now()).filter(
        Q(ends_at__isnull=True) | Q(ends_at__gte=timezone.now())
    )[:5]
    library_loans = LibraryLoan.objects.none()
    if getattr(settings, "LIBRARY_ENABLED", False):
        library_loans = LibraryLoan.objects.filter(student=student, returned_at__isnull=True).select_related("copy__book").order_by("due_at")
    ParentPortalAudit.objects.create(user=request.user, student=student, action=ParentPortalAudit.ACTION_VIEWED, ip_address=client_ip(request), details={"page": "dashboard"})
    return render(request, "parent_portal/dashboard.html", {
        "access": access, "student": student, "children": request.parent_accesses,
        "balance": balance, "attendance_percent": attendance_percent,
        "recent_results": recent_results, "announcements": announcements,
        "library_loans": library_loans, "academic_average": academic_average,
        "unread_notification_count": ParentNotification.objects.filter(user=request.user, read_at__isnull=True).count(),
    })


@feature_required("PARENT_PORTAL_ENABLED")
@parent_required
def parent_children(request):
    rows = []
    for access in request.parent_accesses:
        student = access.student
        attendance = student.attendance_records.exclude(status="unmarked") if access.can_view_attendance else AttendanceRecord.objects.none()
        total = attendance.count()
        present = attendance.filter(status__in=("present", "late")).count()
        bills = student.bills.prefetch_related("items", "payments", "applied_credits") if access.can_view_finance else []
        rows.append({
            "access": access, "student": student,
            "attendance_percent": round((present / total) * 100, 1) if total else None,
            "balance": sum((bill.balance for bill in bills), 0) if access.can_view_finance else None,
            "average": Result.objects.filter(student=student, status="VERIFIED").aggregate(value=Avg("score"))["value"] if access.can_view_academics else None,
        })
    return render(request, "parent_portal/children.html", {"child_rows": rows, "children": request.parent_accesses})


@feature_required("PARENT_PORTAL_ENABLED")
@parent_required
def parent_finance(request, student_id):
    access = _selected_access(request, student_id)
    if not access.can_view_finance:
        messages.error(request, "Financial access is not enabled for this child.")
        return redirect("parent_dashboard")
    bills = access.student.bills.prefetch_related("items", "payments", "applied_credits").order_by("-bill_date")
    ParentPortalAudit.objects.create(user=request.user, student=access.student, action=ParentPortalAudit.ACTION_VIEWED, ip_address=client_ip(request), details={"page": "finance"})
    return render(request, "parent_portal/finance.html", {"access": access, "student": access.student, "bills": bills})


@feature_required("PARENT_PORTAL_ENABLED")
@parent_required
def parent_results(request, student_id):
    access = _selected_access(request, student_id)
    if not access.can_view_academics:
        messages.error(request, "Academic access is not enabled for this child.")
        return redirect("parent_dashboard")
    results = Result.objects.filter(student=access.student, status="VERIFIED").select_related(
        "assessment__subject", "assessment__assessment_type", "assessment__academic_class"
    ).order_by("-assessment__date", "assessment__subject__name")
    ParentPortalAudit.objects.create(user=request.user, student=access.student, action=ParentPortalAudit.ACTION_VIEWED, ip_address=client_ip(request), details={"page": "results"})
    return render(request, "parent_portal/results.html", {"access": access, "student": access.student, "results": results})


@feature_required("PARENT_PORTAL_ENABLED")
@parent_required
def parent_attendance(request, student_id):
    access = _selected_access(request, student_id)
    if not access.can_view_attendance:
        messages.error(request, "Attendance access is not enabled for this child.")
        return redirect("parent_dashboard")
    records = AttendanceRecord.objects.filter(
        student=access.student, session__is_locked=True,
    ).exclude(status="unmarked").select_related("session__subject", "session__term").order_by("-session__date")
    counts = {row["status"]: row["total"] for row in records.values("status").annotate(total=Count("id"))}
    total = sum(counts.values())
    present = counts.get("present", 0) + counts.get("late", 0)
    return render(request, "parent_portal/attendance.html", {
        "access": access, "student": access.student, "records": records[:100], "counts": counts,
        "attendance_percent": round((present / total) * 100, 1) if total else None,
    })


@feature_required("PARENT_PORTAL_ENABLED")
@parent_required
def parent_announcements(request):
    now = timezone.now()
    announcements = Announcement.objects.filter(
        is_active=True, audience__in=("all", "parents"), starts_at__lte=now,
    ).filter(Q(ends_at__isnull=True) | Q(ends_at__gte=now))
    return render(request, "parent_portal/announcements.html", {"announcements": announcements, "children": request.parent_accesses})


@feature_required("PARENT_PORTAL_ENABLED")
@parent_required
def parent_library(request, student_id):
    access = _selected_access(request, student_id)
    if not getattr(settings, "LIBRARY_ENABLED", False):
        return redirect("parent_dashboard")
    loans = LibraryLoan.objects.filter(student=access.student).select_related("copy__book").order_by("-issued_at")
    return render(request, "parent_portal/library.html", {
        "access": access, "student": access.student, "current_loans": loans.filter(returned_at__isnull=True),
        "history": loans.filter(returned_at__isnull=False)[:30],
    })


@feature_required("PARENT_PORTAL_ENABLED")
@parent_required
def parent_report_download(request, student_id):
    access = _selected_access(request, student_id)
    if not access.can_view_academics:
        return redirect("parent_dashboard")
    term_id = request.GET.get("term_id", "")
    results = Result.objects.filter(student=access.student, status="VERIFIED").select_related(
        "assessment__subject", "assessment__assessment_type"
    ).order_by("assessment__subject__name", "assessment__date")
    if term_id.isdigit():
        results = results.filter(assessment__academic_class__term_id=int(term_id))
    if not results.exists():
        messages.error(request, "No verified results are available for this report.")
        return redirect("parent_results", student_id=student_id)
    buffer = generate_student_report_pdf(access.student, results)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{access.student.reg_no}-verified-results.pdf"'
    ParentPortalAudit.objects.create(
        user=request.user, student=access.student, action=ParentPortalAudit.ACTION_VIEWED,
        ip_address=client_ip(request), details={"page": "report_download", "term_id": term_id},
    )
    return response


@feature_required("PARENT_PORTAL_ENABLED")
@parent_required
def parent_notifications(request):
    sync_parent_notifications(request.user)
    notifications = ParentNotification.objects.filter(user=request.user).select_related("student")
    return render(request, "parent_portal/notifications.html", {"notifications": notifications, "children": request.parent_accesses})


@feature_required("PARENT_PORTAL_ENABLED")
@parent_required
def parent_notification_open(request, notification_id):
    notification = get_object_or_404(ParentNotification, pk=notification_id, user=request.user)
    if not notification.read_at:
        notification.read_at = timezone.now()
        notification.save(update_fields=("read_at",))
    return redirect(notification.destination or "parent_notifications")


@feature_required("PARENT_PORTAL_ENABLED")
@parent_required
def parent_messages(request):
    conversations = ParentConversation.objects.filter(
        parent=request.user, student_id__in=request.parent_accesses.values("student_id"), is_active=True,
    ).select_related("student", "staff", "thread").prefetch_related("thread__messages")
    return render(request, "parent_portal/messages.html", {"conversations": conversations, "children": request.parent_accesses})


@feature_required("PARENT_PORTAL_ENABLED")
@parent_required
def parent_message_new(request, student_id):
    access = _selected_access(request, student_id)
    teachers = eligible_parent_teachers(access.student)
    form = ParentConversationStartForm(request.POST or None, teachers=teachers)
    if request.method == "POST" and form.is_valid():
        try:
            conversation = start_parent_conversation(
                parent=request.user, student=access.student, teacher=form.cleaned_data["teacher"],
                subject=form.cleaned_data["subject"], body=form.cleaned_data["message"],
            )
            return redirect("parent_message_thread", conversation_id=conversation.pk)
        except ParentAccessError as exc:
            form.add_error(None, str(exc))
    return render(request, "parent_portal/message_new.html", {
        "form": form, "student": access.student, "children": request.parent_accesses,
    })


@feature_required("PARENT_PORTAL_ENABLED")
@parent_required
def parent_message_thread(request, conversation_id):
    conversation = get_object_or_404(
        ParentConversation.objects.select_related("thread", "student", "staff"),
        pk=conversation_id, parent=request.user, is_active=True,
        student_id__in=request.parent_accesses.values("student_id"),
    )
    form = ParentMessageForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        message = form.save(commit=False)
        message.thread = conversation.thread
        message.sender = request.user
        message.save()
        conversation.thread.updated_at = timezone.now()
        conversation.thread.save(update_fields=("updated_at",))
        return redirect("parent_message_thread", conversation_id=conversation.pk)
    return render(request, "parent_portal/message_thread.html", {
        "conversation": conversation, "thread_messages": conversation.thread.messages.select_related("sender"),
        "form": form, "children": request.parent_accesses,
    })


@feature_required("PARENT_PORTAL_ENABLED")
@role_required_any(*PARENT_MANAGEMENT_ROLES)
def parent_access_activate(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    if request.method == "POST":
        try:
            access = activate_parent_access(
                student=student, verified_by=request.user,
                allow_guardian_mismatch=request.POST.get("confirm_shared_contact") == "yes",
            )
            if access.must_change_password:
                notice = f"Username: {access.user.username}; temporary password: 123 (expires in {settings.PARENT_TEMP_PASSWORD_HOURS} hours)."
            else:
                notice = f"Linked to the existing parent account {access.user.username}; its private password was not changed."
            messages.success(request, f"Parent access activated. {notice}")
        except ParentAccessError as exc:
            messages.error(request, str(exc))
    return redirect("student_details_page", id=student.pk)


@feature_required("PARENT_PORTAL_ENABLED")
@role_required_any(*PARENT_MANAGEMENT_ROLES)
def parent_access_management(request):
    accesses = ParentAccess.objects.select_related("user", "student", "verified_by").order_by(
        "user__username", "student__student_name"
    )
    query = request.GET.get("q", "").strip()
    if query:
        accesses = accesses.filter(
            Q(user__username__icontains=query) | Q(student__student_name__icontains=query)
            | Q(student__reg_no__icontains=query) | Q(student__guardian__icontains=query)
        )
    return render(request, "parent_portal/manage.html", {"accesses": accesses, "query": query})


@feature_required("PARENT_PORTAL_ENABLED")
@role_required_any(*PARENT_MANAGEMENT_ROLES)
def parent_access_update(request, access_id):
    access = get_object_or_404(ParentAccess.objects.select_related("student", "user"), pk=access_id)
    if request.method == "POST":
        form = ParentAccessPermissionsForm(request.POST, instance=access)
        if form.is_valid():
            form.save()
            ParentPortalAudit.objects.create(
                user=access.user, student=access.student, action=ParentPortalAudit.ACTION_ACCESS_CHANGED,
                details={"actor": request.user.pk, "permissions": form.cleaned_data},
            )
            messages.success(request, "Parent portal permissions updated.")
            return redirect("parent_access_management")
    else:
        form = ParentAccessPermissionsForm(instance=access)
    return render(request, "parent_portal/access_form.html", {"access": access, "form": form})


@feature_required("PARENT_PORTAL_ENABLED")
@role_required_any(*PARENT_MANAGEMENT_ROLES)
def parent_access_deactivate(request, access_id):
    if request.method == "POST":
        deactivate_parent_access(access_id=access_id, actor=request.user, reason=request.POST.get("reason", ""))
        messages.success(request, "The selected parent-to-student access was deactivated.")
    return redirect("parent_access_management")


@feature_required("PARENT_PORTAL_ENABLED")
@role_required_any(*PARENT_MANAGEMENT_ROLES)
def parent_password_reset(request, user_id):
    if request.method == "POST":
        try:
            user = reset_parent_password(user_id=user_id, actor=request.user)
            messages.success(
                request, f"Password reset for {user.username}. Temporary password: 123; it expires in "
                f"{settings.PARENT_TEMP_PASSWORD_HOURS} hours.",
            )
        except ParentAccessError as exc:
            messages.error(request, str(exc))
    return redirect("parent_access_management")


@feature_required("PARENT_PORTAL_ENABLED")
def parent_logout(request):
    logout(request)
    return redirect("parent_login")
