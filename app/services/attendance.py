from django.db import transaction
from django.utils import timezone

from app.models.attendance import AttendanceSession, AttendanceRecord, AttendanceStatus
from app.models.students import ClassRegister


def get_or_create_session(class_stream, subject, teacher, date, time_slot, academic_year, term):
    session, _ = AttendanceSession.objects.get_or_create(
        class_stream=class_stream,
        subject=subject,
        teacher=teacher,
        date=date,
        time_slot=time_slot,
        defaults={"academic_year": academic_year, "term": term},
    )
    return session


@transaction.atomic
def initialize_session_records(session):
    students = (
        ClassRegister.objects.filter(academic_class_stream=session.class_stream)
        .select_related("student")
        .values_list("student", flat=True)
    )
    existing = set(
        AttendanceRecord.objects.filter(session=session).values_list("student_id", flat=True)
    )
    new_records = [
        AttendanceRecord(
            session=session,
            student_id=student_id,
            status=AttendanceStatus.PRESENT,
        )
        for student_id in students
        if student_id not in existing
    ]
    if new_records:
        AttendanceRecord.objects.bulk_create(new_records)


@transaction.atomic
def save_attendance_records(session, payload, captured_by):
    for student_id, row in payload.items():
        status = row.get("status") or AttendanceStatus.PRESENT
        remarks = row.get("remarks") or ""
        AttendanceRecord.objects.update_or_create(
            session=session,
            student_id=int(student_id),
            defaults={
                "status": status,
                "remarks": remarks,
                "captured_by": captured_by,
                "captured_at": timezone.now(),
            },
        )
