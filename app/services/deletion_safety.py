"""Non-destructive guards for setup records with production history."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.attendance import AttendanceSession
from app.models.classes import AcademicClass, AcademicClassStream, Class, Stream, StudentPromotionHistory
from app.models.fees_payment import BillItem, ClassBill, StudentBill, StudentBillItem
from app.models.results import Assessment, AnnualResult, ReportCycleRemark, ReportResults, TermResult
from app.models.students import ClassRegister, Student


@dataclass(frozen=True)
class DeletionBlocker:
    label: str
    count: int


def _nonzero(**counts) -> list[DeletionBlocker]:
    return [
        DeletionBlocker(label=label.replace("_", " "), count=count)
        for label, count in counts.items()
        if count
    ]


def describe_blockers(blockers: list[DeletionBlocker]) -> str:
    return ", ".join(f"{blocker.count} {blocker.label}" for blocker in blockers)


def class_deletion_blockers(class_record: Class) -> list[DeletionBlocker]:
    return _nonzero(
        academic_classes=AcademicClass.objects.filter(Class=class_record).count(),
        student_snapshots=Student.objects.filter(current_class=class_record).count(),
    )


def stream_deletion_blockers(stream: Stream) -> list[DeletionBlocker]:
    return _nonzero(
        academic_class_streams=AcademicClassStream.objects.filter(stream=stream).count(),
        student_snapshots=Student.objects.filter(stream=stream).count(),
        class_registrations=ClassRegister.objects.filter(academic_class_stream__stream=stream).count(),
    )


def academic_class_deletion_blockers(academic_class: AcademicClass) -> list[DeletionBlocker]:
    return _nonzero(
        class_registrations=ClassRegister.objects.filter(
            academic_class_stream__academic_class=academic_class
        ).count(),
        student_bills=StudentBill.objects.filter(academic_class=academic_class).count(),
        assessments=Assessment.objects.filter(academic_class=academic_class).count(),
        attendance_sessions=AttendanceSession.objects.filter(
            class_stream__academic_class=academic_class
        ).count(),
        promotion_history=StudentPromotionHistory.objects.filter(
            source_academic_class=academic_class
        ).count()
        + StudentPromotionHistory.objects.filter(target_academic_class=academic_class).count(),
        report_results=ReportResults.objects.filter(academic_class=academic_class).count(),
        term_results=TermResult.objects.filter(academic_class=academic_class).count(),
        annual_results=AnnualResult.objects.filter(academic_class=academic_class).count(),
        report_remarks=ReportCycleRemark.objects.filter(academic_class=academic_class).count(),
    )


def class_stream_deletion_blockers(class_stream: AcademicClassStream) -> list[DeletionBlocker]:
    return _nonzero(
        class_registrations=ClassRegister.objects.filter(academic_class_stream=class_stream).count(),
        attendance_sessions=AttendanceSession.objects.filter(class_stream=class_stream).count(),
    )


def bill_item_deletion_blockers(bill_item: BillItem) -> list[DeletionBlocker]:
    return _nonzero(
        class_bills=ClassBill.objects.filter(bill_item=bill_item).count(),
        student_bill_items=StudentBillItem.objects.filter(bill_item=bill_item).count(),
    )


def class_bill_deletion_blockers(class_bill: ClassBill) -> list[DeletionBlocker]:
    return _nonzero(
        posted_student_bill_items=StudentBillItem.objects.filter(
            bill__academic_class=class_bill.academic_class,
            bill_item=class_bill.bill_item,
        ).count(),
    )
