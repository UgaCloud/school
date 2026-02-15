from app.models.school_settings import SchoolSetting
from app.models.results import ResultVerificationNotification, ResultBatch, Assessment, Result
from app.models.classes import AcademicClassStream, ClassSubjectAllocation, Term
from app.models.students import ClassRegister
from app.models.communications import Announcement, Event, AnnouncementTarget, MessageThread, Message
from app.models.accounts import StaffAccount
from app.selectors.school_settings import get_current_academic_year
from django.db.models import Count, F, Q, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.dateparse import parse_datetime
import logging

logger = logging.getLogger(__name__)


def school_settings(request):
    
    school_settings = SchoolSetting.load()  # Use SingletonModel's `load()` method to get the instance

    active_role = None
    staff_account = None
    try:
        if getattr(request, "user", None) and request.user.is_authenticated:
            staff_account = getattr(request.user, "staff_account", None)
            # Prefer session active role
            active_role = request.session.get("active_role_name")
            if not active_role:
                # Fallback to current StaffAccount role name when available
                if staff_account and getattr(staff_account, "role", None):
                    active_role = staff_account.role.name
    except Exception:
        active_role = None

    pending_verification_count = 0
    pending_verification_notifications = []
    pending_teacher_assessment_count = 0
    pending_teacher_assessment_notifications = []
    pending_teacher_mark_count = 0
    pending_teacher_mark_notifications = []
    comm_notifications = []
    comm_unread_count = 0
    comm_unread_breakdown = {
        "announcements": 0,
        "events": 0,
        "messages": 0,
    }

    if getattr(request, "user", None) and request.user.is_authenticated:
        is_dos_user = False
        is_teacher_user = False
        role_name = None
        if staff_account and getattr(staff_account, "role", None):
            role_name = staff_account.role.name
        if role_name in {"Director of Studies", "DOS"}:
            is_dos_user = True
        elif active_role in {"Director of Studies", "DOS"}:
            is_dos_user = True
        elif staff_account and getattr(staff_account, "staff", None):
            if staff_account.staff.roles.filter(name__in=["Director of Studies", "DOS"]).exists():
                is_dos_user = True
        logger.info(
            "verification context: user_id=%s role_name=%s active_role=%s is_dos_user=%s",
            getattr(request.user, "id", None),
            role_name,
            active_role,
            is_dos_user,
        )

        if role_name in {"Teacher", "Class Teacher"} or active_role in {"Teacher", "Class Teacher"}:
            is_teacher_user = True

        if is_dos_user:
            pending_batches = ResultBatch.objects.filter(status="PENDING").select_related("assessment")
            logger.info(
                "verification context: pending_batches=%s",
                list(pending_batches.values_list("id", flat=True)),
            )
            for batch in pending_batches:
                notification_defaults = {
                    "title": "Results submitted for verification",
                    "message": f"{batch.assessment} has been submitted for verification.",
                }
                existing = ResultVerificationNotification.objects.filter(
                    recipient=request.user,
                    batch=batch,
                )
                if existing.exists():
                    existing.update(**notification_defaults)
                else:
                    ResultVerificationNotification.objects.create(
                        recipient=request.user,
                        batch=batch,
                        **notification_defaults,
                    )

            ResultVerificationNotification.objects.filter(
                recipient=request.user,
                batch__status__in=["VERIFIED", "FLAGGED"],
                read=False,
            ).update(read=True, read_at=timezone.now())

        if is_teacher_user and staff_account and getattr(staff_account, "staff", None):
            current_year = get_current_academic_year()
            current_term = Term.objects.filter(is_current=True).first()
            if current_year and current_term:
                allocations = ClassSubjectAllocation.objects.filter(
                    subject_teacher=staff_account.staff,
                    academic_class_stream__academic_class__academic_year=current_year,
                    academic_class_stream__academic_class__term=current_term,
                ).select_related("academic_class_stream__academic_class", "subject")

                subject_ids = list(allocations.values_list("subject_id", flat=True).distinct())
                class_ids = list(
                    allocations.values_list("academic_class_stream__academic_class_id", flat=True).distinct()
                )

                if subject_ids and class_ids:
                    assessments_qs = Assessment.objects.filter(
                        academic_class_id__in=class_ids,
                        subject_id__in=subject_ids,
                        academic_class__academic_year=current_year,
                        academic_class__term=current_term,
                    ).select_related("academic_class", "subject", "assessment_type").order_by("-date")

                    pending_teacher_assessment_count = assessments_qs.count()
                    pending_teacher_assessment_notifications = list(assessments_qs[:5])

                    pending_marks_qs = assessments_qs.filter(
                        result_batch__status="DRAFT"
                    ).annotate(
                        total_students=Count("academic_class__class_streams__classregister", distinct=True),
                        total_results=Count("results", distinct=True),
                    ).filter(
                        total_results__lt=F("total_students")
                    )
                    pending_teacher_mark_count = pending_marks_qs.count()
                    pending_teacher_mark_notifications = list(pending_marks_qs[:5])

        notifications_qs = ResultVerificationNotification.objects.filter(
            recipient=request.user,
            read=False
        ).select_related("batch", "batch__assessment").order_by("-created_at")
        pending_verification_count = notifications_qs.count()
        pending_verification_notifications = list(notifications_qs[:10])

        now = timezone.now()
        user_role = active_role or role_name
        if user_role in {"Admin", "Head Teacher", "Head master"}:
            audience = None
        elif user_role == "Director of Studies":
            audience = ["all", "dos"]
        elif user_role == "Bursar":
            audience = ["all", "bursar"]
        elif user_role == "Class Teacher":
            audience = ["all", "class_teacher", "teachers"]
        elif user_role == "Teacher":
            audience = ["all", "teachers"]
        else:
            audience = ["all"]

        last_comm_seen_raw = request.COOKIES.get("comm_seen_at") or request.session.get("last_comm_seen_at")
        last_comm_seen = parse_datetime(last_comm_seen_raw) if last_comm_seen_raw else None

        announcement_targets = AnnouncementTarget.objects.filter(
            staff=getattr(staff_account, "staff", None),
            announcement__is_active=True,
            announcement__starts_at__lte=now,
        ).filter(
            Q(announcement__ends_at__isnull=True) | Q(announcement__ends_at__gte=now)
        ).select_related("announcement")

        targeted_announcements = Announcement.objects.filter(
            targets__in=announcement_targets
        )

        announcement_qs = Announcement.objects.filter(
            is_active=True,
            starts_at__lte=now,
        ).filter(
            Q(ends_at__isnull=True) | Q(ends_at__gte=now)
        )
        if audience is not None:
            announcement_qs = announcement_qs.filter(audience__in=audience)
        announcement_qs = announcement_qs | targeted_announcements
        announcement_qs = announcement_qs.distinct()

        event_qs = Event.objects.filter(
            is_active=True,
            start_datetime__gte=now,
        )
        if audience is not None:
            event_qs = event_qs.filter(audience__in=audience)

        if user_role == "Class Teacher" and staff_account and getattr(staff_account, "staff", None):
            class_stream_ids = list(
                AcademicClassStream.objects.filter(
                    class_teacher=staff_account.staff
                ).values_list("id", flat=True)
            )
            if class_stream_ids:
                class_stream_teacher_ids = ClassSubjectAllocation.objects.filter(
                    academic_class_stream_id__in=class_stream_ids
                ).values_list("subject_teacher_id", flat=True)
                targeted_teacher_ids = set(class_stream_teacher_ids)
                targeted_teacher_ids.add(staff_account.staff.id)
                if targeted_teacher_ids:
                    targeted_teacher_accounts = StaffAccount.objects.filter(
                        staff_id__in=targeted_teacher_ids
                    ).values_list("user_id", flat=True)
                    if targeted_teacher_accounts:
                        announcement_qs = announcement_qs.filter(
                            created_by_id__in=list(targeted_teacher_accounts)
                        )

        latest_message_subquery = Message.objects.filter(
            thread=OuterRef("pk")
        ).order_by("-created_at").values("created_at")[:1]
        latest_sender_subquery = Message.objects.filter(
            thread=OuterRef("pk")
        ).order_by("-created_at").values("sender_id")[:1]

        message_threads = MessageThread.objects.filter(
            participants=request.user
        ).annotate(
            latest_message_at=Subquery(latest_message_subquery),
            latest_sender_id=Subquery(latest_sender_subquery),
            latest_activity_at=Coalesce("latest_message_at", "updated_at"),
        ).order_by("-latest_activity_at")

        comm_notifications = {
            "announcements": announcement_qs.order_by("-starts_at")[:5],
            "events": event_qs.order_by("start_datetime")[:5],
            "messages": message_threads[:5],
        }

        if last_comm_seen:
            announcement_unread = announcement_qs.filter(created_at__gt=last_comm_seen).count()
            event_unread = event_qs.filter(created_at__gt=last_comm_seen).count()
            message_unread = message_threads.filter(
                latest_activity_at__gt=last_comm_seen
            ).exclude(latest_sender_id=request.user.id).count()
            comm_unread_count = announcement_unread + event_unread + message_unread
        else:
            announcement_unread = announcement_qs.count()
            event_unread = event_qs.count()
            message_unread = message_threads.exclude(latest_sender_id=request.user.id).count()
            comm_unread_count = announcement_unread + event_unread + message_unread

        comm_unread_breakdown = {
            "announcements": announcement_unread,
            "events": event_unread,
            "messages": message_unread,
        }

    return {
        'school_settings': school_settings,
        'active_role': active_role,
        'pending_verification_count': pending_verification_count,
        'pending_verification_notifications': pending_verification_notifications,
        'pending_teacher_assessment_count': pending_teacher_assessment_count,
        'pending_teacher_assessment_notifications': pending_teacher_assessment_notifications,
        'pending_teacher_mark_count': pending_teacher_mark_count,
        'pending_teacher_mark_notifications': pending_teacher_mark_notifications,
        'comm_notifications': comm_notifications,
        'comm_unread_count': comm_unread_count,
        'comm_unread_breakdown': comm_unread_breakdown,
    }
