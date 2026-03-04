"""Attendance service for the admin control-tower dashboard."""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from app.models.attendance import AttendanceRecord, AttendanceSession, AttendanceStatus
from app.services.level_scope import (
    get_level_academic_classes_queryset,
    get_level_class_streams_queryset,
)
from app.services.school_level import get_active_school_level

PRESENT_LIKE_STATUSES = [AttendanceStatus.PRESENT, AttendanceStatus.LATE]


def _attendance_rate(queryset) -> float:
    total = queryset.count()
    if not total:
        return 0
    present_like = queryset.filter(status__in=PRESENT_LIKE_STATUSES).count()
    return round((present_like / total) * 100, 1)


def get_attendance_context(request, scope):
    """Attendance health, submission gaps, and chronic absenteeism."""
    current_year = scope.get("current_year")
    current_term = scope.get("current_term")
    active_level = get_active_school_level(request)
    today = timezone.localdate()
    week_start = today - timedelta(days=6)

    attendance_today_rate = 0
    attendance_week_rate = 0
    class_submission_rows = []
    class_attendance_rows = []
    chronic_absentee_rows = []
    weekly_trend_rows = []
    teachers_absent_today = 0
    classes_not_submitted_count = 0
    total_teachers = 0
    total_class_streams = 0

    if current_year and current_term:
        term_scoped_academic_classes = get_level_academic_classes_queryset(
            active_level=active_level
        ).filter(
            academic_year=current_year,
            term=current_term,
        )
        attendance_scope = AttendanceRecord.objects.filter(
            session__academic_year=current_year,
            session__term=current_term,
            session__class_stream__academic_class__in=term_scoped_academic_classes,
        )
        attendance_today_rate = _attendance_rate(attendance_scope.filter(session__date=today))
        attendance_week_rate = _attendance_rate(
            attendance_scope.filter(session__date__range=(week_start, today))
        )

        class_stream_scope = get_level_class_streams_queryset(
            active_level=active_level
        ).filter(
            academic_class__in=term_scoped_academic_classes
        ).select_related("academic_class__Class", "stream")
        submitted_stream_ids = set(
            AttendanceSession.objects.filter(
                academic_year=current_year,
                term=current_term,
                date=today,
                class_stream__academic_class__in=term_scoped_academic_classes,
            )
            .values_list("class_stream_id", flat=True)
            .distinct()
        )

        for class_stream in class_stream_scope:
            submitted = class_stream.id in submitted_stream_ids
            class_submission_rows.append(
                {
                    "class_name": class_stream.academic_class.Class.name,
                    "stream_name": class_stream.stream.stream,
                    "submitted": submitted,
                }
            )
        class_submission_rows = sorted(
            class_submission_rows,
            key=lambda row: (
                row["class_name"],
                row["stream_name"],
            ),
        )
        classes_not_submitted_count = len(
            [row for row in class_submission_rows if not row["submitted"]]
        )

        total_class_streams = class_stream_scope.count()
        total_teachers = class_stream_scope.values("class_teacher_id").distinct().count()
        teachers_submitted_today = (
            AttendanceSession.objects.filter(
                academic_year=current_year,
                term=current_term,
                date=today,
                class_stream__academic_class__in=term_scoped_academic_classes,
            )
            .values("teacher_id")
            .distinct()
            .count()
        )
        teachers_absent_today = max(total_teachers - teachers_submitted_today, 0)

        class_attendance_agg = list(
            attendance_scope.values(
                "session__class_stream__academic_class__Class__name",
                "session__class_stream__stream__stream",
            )
            .annotate(
                total=Count("id"),
                present_like=Count("id", filter=Q(status__in=PRESENT_LIKE_STATUSES)),
            )
            .order_by("session__class_stream__academic_class__Class__name")
        )
        for row in class_attendance_agg:
            total = row["total"] or 0
            present_like = row["present_like"] or 0
            class_attendance_rows.append(
                {
                    "class_name": row["session__class_stream__academic_class__Class__name"]
                    or "Unknown",
                    "stream_name": row["session__class_stream__stream__stream"] or "-",
                    "total": total,
                    "present_like": present_like,
                    "rate": round((present_like / total) * 100, 1) if total else 0,
                }
            )

        student_attendance = (
            attendance_scope.values(
                "student_id",
                "student__student_name",
                "student__reg_no",
                "student__current_class__name",
            )
            .annotate(
                total_sessions=Count("id"),
                present_sessions=Count("id", filter=Q(status__in=PRESENT_LIKE_STATUSES)),
            )
            .order_by("student__student_name")
        )
        for row in student_attendance:
            total_sessions = row["total_sessions"] or 0
            present_sessions = row["present_sessions"] or 0
            if not total_sessions:
                continue
            rate = round((present_sessions / total_sessions) * 100, 1)
            if total_sessions >= 5 and rate < 75:
                chronic_absentee_rows.append(
                    {
                        "student_name": row["student__student_name"] or "Unknown",
                        "reg_no": row["student__reg_no"] or "-",
                        "class_name": row["student__current_class__name"] or "-",
                        "rate": rate,
                        "total_sessions": total_sessions,
                    }
                )
        chronic_absentee_rows = sorted(chronic_absentee_rows, key=lambda row: row["rate"])[:10]

        raw_weekly = list(
            attendance_scope.filter(session__date__range=(week_start, today))
            .values("session__date")
            .annotate(
                total=Count("id"),
                present_like=Count("id", filter=Q(status__in=PRESENT_LIKE_STATUSES)),
            )
            .order_by("session__date")
        )
        weekly_map = {
            row["session__date"]: {
                "total": row["total"] or 0,
                "present_like": row["present_like"] or 0,
            }
            for row in raw_weekly
        }
        cursor = week_start
        while cursor <= today:
            item = weekly_map.get(cursor, {"total": 0, "present_like": 0})
            total = item["total"]
            present_like = item["present_like"]
            weekly_trend_rows.append(
                {
                    "label": cursor.strftime("%a"),
                    "date": cursor,
                    "rate": round((present_like / total) * 100, 1) if total else 0,
                }
            )
            cursor = cursor + timedelta(days=1)

    return {
        "attendance_today_rate": attendance_today_rate,
        "attendance_week_rate": attendance_week_rate,
        "attendance_teachers_absent_today": teachers_absent_today,
        "attendance_total_teachers": total_teachers,
        "attendance_classes_not_submitted_count": classes_not_submitted_count,
        "attendance_total_class_streams": total_class_streams,
        "attendance_class_submission_rows": class_submission_rows,
        "attendance_class_rows": class_attendance_rows,
        "attendance_chronic_absentee_rows": chronic_absentee_rows,
        "attendance_weekly_trend_rows": weekly_trend_rows,
    }
