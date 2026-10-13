from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from app.models.classes import AcademicClass, AcademicClassStream, Stream
from app.models.fees_payment import StudentBill
from app.models.students import ClassRegister, Student


@dataclass
class EnrollmentStateResult:
    class_register: ClassRegister
    register_created: bool
    student_bill: StudentBill | None
    bill_created: bool
    snapshot_updated: bool


def ensure_student_academic_state(
    *,
    student: Student,
    academic_class: AcademicClass,
    stream: Stream | None = None,
    academic_class_stream: AcademicClassStream | None = None,
    sync_snapshot: bool = True,
    ensure_bill: bool = True,
) -> EnrollmentStateResult:
    """
    Idempotently align a student's current academic state.

    Production-safety rules:
    - Never deletes registrations, bills, payments, results, or history.
    - Never changes a historical registration.
    - Uses get_or_create for the target ClassRegister and StudentBill.
    - Updates the Student current_* snapshot only when explicitly requested.
    - Bill line creation/update is delegated to the existing idempotent billing
      service so the system retains its current fee rules.
    """
    if academic_class_stream is None:
        if stream is None:
            raise ValueError("A stream or academic_class_stream is required.")
        academic_class_stream = AcademicClassStream.objects.filter(
            academic_class=academic_class,
            stream=stream,
        ).select_related("stream").first()
        if academic_class_stream is None:
            raise ValueError(
                f"No class stream is configured for {academic_class} / {stream}."
            )
    elif academic_class_stream.academic_class_id != academic_class.id:
        raise ValueError("The supplied class stream does not belong to the academic class.")

    with transaction.atomic():
        locked_student = Student.objects.select_for_update().get(pk=student.pk)

        class_register, register_created = ClassRegister.objects.get_or_create(
            academic_class_stream=academic_class_stream,
            student=locked_student,
        )

        snapshot_updated = False
        if sync_snapshot:
            update_fields = []
            if locked_student.current_class_id != academic_class.Class_id:
                locked_student.current_class_id = academic_class.Class_id
                update_fields.append("current_class")
            if locked_student.stream_id != academic_class_stream.stream_id:
                locked_student.stream_id = academic_class_stream.stream_id
                update_fields.append("stream")
            if locked_student.academic_year_id != academic_class.academic_year_id:
                locked_student.academic_year_id = academic_class.academic_year_id
                update_fields.append("academic_year")
            if locked_student.term_id != academic_class.term_id:
                locked_student.term_id = academic_class.term_id
                update_fields.append("term")

            if update_fields:
                locked_student.save(update_fields=update_fields)
                snapshot_updated = True

        student_bill = None
        bill_created = False
        if ensure_bill:
            bill_existed = StudentBill.objects.filter(
                student=locked_student,
                academic_class=academic_class,
            ).exists()

            # Local import deliberately avoids an import cycle: students.py
            # uses this helper for normal registration and bulk registration.
            from app.services.students import create_student_bill

            student_bill = create_student_bill(locked_student, academic_class)
            bill_created = not bill_existed

        return EnrollmentStateResult(
            class_register=class_register,
            register_created=register_created,
            student_bill=student_bill,
            bill_created=bill_created,
            snapshot_updated=snapshot_updated,
        )
