from collections import Counter

from django.core.management.base import BaseCommand

from app.models.students import Student
from app.services.credit_integrity import get_credit_source_summaries


class Command(BaseCommand):
    help = (
        "Read-only audit of overpayment credits. It never creates, updates, "
        "deletes, or applies credit rows."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--student",
            help="Limit to one student by registration number or numeric database ID.",
        )

    def handle(self, *args, **options):
        students = Student.objects.all().order_by("student_name", "reg_no")
        student_filter = (options.get("student") or "").strip()
        if student_filter:
            students = students.filter(pk=int(student_filter)) if student_filter.isdigit() else students.filter(reg_no=student_filter)

        counts = Counter()
        reviewed = 0
        for student in students.iterator():
            reviewed += 1
            summaries = get_credit_source_summaries(student, include_overpayment_bills=True)
            for summary in summaries:
                if not (
                    summary.actual_overpayment
                    or summary.applied_amount
                    or summary.positive_credit_total
                ):
                    continue

                source_label = f"bill #{summary.original_bill.id}"
                if summary.applied_amount > summary.actual_overpayment:
                    counts["applied_exceeds_overpayment"] += 1
                    self._issue(
                        student,
                        "APPLIED_CREDIT_EXCEEDS_OVERPAYMENT",
                        f"{source_label}: applied {summary.applied_amount} exceeds actual overpayment {summary.actual_overpayment}.",
                    )
                if summary.actual_overpayment > 0 and summary.positive_credit_total <= 0:
                    counts["missing_positive_credit"] += 1
                    self._issue(
                        student,
                        "OVERPAYMENT_WITHOUT_CREDIT",
                        f"{source_label}: overpayment {summary.actual_overpayment} has no positive credit record.",
                    )
                if (
                    summary.positive_credit_total > summary.available_amount
                    or summary.positive_credit_rows > 1
                ):
                    counts["stale_or_duplicate_positive"] += 1
                    self._issue(
                        student,
                        "STALE_OR_DUPLICATE_POSITIVE_CREDIT",
                        f"{source_label}: positive rows total {summary.positive_credit_total}; derived remaining credit is {summary.available_amount}.",
                    )
                if summary.legacy_available_total != summary.available_amount:
                    counts["inconsistent_remaining"] += 1
                    self._issue(
                        student,
                        "INCONSISTENT_REMAINING_CREDIT",
                        f"{source_label}: legacy available {summary.legacy_available_total}; derived remaining {summary.available_amount}.",
                    )

        self.stdout.write(self.style.MIGRATE_HEADING("Student credit audit"))
        self.stdout.write("Mode: DRY RUN (no database rows were changed)")
        self.stdout.write(f"Students reviewed: {reviewed}")
        self.stdout.write(f"Applied credit exceeds overpayment: {counts['applied_exceeds_overpayment']}")
        self.stdout.write(f"Overpayments without a positive credit: {counts['missing_positive_credit']}")
        self.stdout.write(f"Stale or duplicate positive credits: {counts['stale_or_duplicate_positive']}")
        self.stdout.write(f"Inconsistent remaining-credit calculations: {counts['inconsistent_remaining']}")

    def _issue(self, student, code, detail):
        self.stdout.write(f"[{code}] {student.reg_no or student.pk} | {student.student_name} | {detail}")
