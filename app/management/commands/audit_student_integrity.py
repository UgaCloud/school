from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from app.models.classes import AcademicClassStream, Term
from app.models.fees_payment import StudentBill
from app.models.school_settings import AcademicYear
from app.models.students import ClassRegister, Student
from app.services.enrollment_integrity import ensure_student_academic_state


class Command(BaseCommand):
    help = (
        "Audit active learner enrollment consistency for one academic period. "
        "Read-only by default. Use --repair-safe only after reviewing the dry run."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            help="Academic year label (for example 2026) or database ID. Defaults to current year.",
        )
        parser.add_argument(
            "--term",
            help="Term value (for example 1/2/3) or database ID. Defaults to current term in the selected year.",
        )
        parser.add_argument(
            "--student",
            help="Limit to one student by registration number or numeric database ID.",
        )
        parser.add_argument(
            "--repair-safe",
            action="store_true",
            help=(
                "Repair only deterministic cases with exactly one registration in the selected period: "
                "synchronise the Student current snapshot and create a missing bill. "
                "Never deletes or rewrites historical records."
            ),
        )

    def handle(self, *args, **options):
        year = self._resolve_year(options.get("year"))
        term = self._resolve_term(year, options.get("term"))
        student_filter = (options.get("student") or "").strip()
        repair_safe = bool(options.get("repair_safe"))

        students = Student.objects.filter(is_active=True).order_by("student_name", "reg_no")
        if student_filter:
            if student_filter.isdigit():
                students = students.filter(pk=int(student_filter))
            else:
                students = students.filter(reg_no=student_filter)

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Student integrity audit: {year.academic_year} / Term {term.term}"
            )
        )
        self.stdout.write(
            self.style.WARNING(
                "Mode: SAFE REPAIR" if repair_safe else "Mode: DRY RUN (no database writes)"
            )
        )

        counts = Counter()
        reviewed = 0

        for student in students.iterator():
            reviewed += 1
            registers = list(
                ClassRegister.objects.filter(
                    student=student,
                    academic_class_stream__academic_class__academic_year=year,
                    academic_class_stream__academic_class__term=term,
                )
                .select_related(
                    "academic_class_stream",
                    "academic_class_stream__stream",
                    "academic_class_stream__academic_class",
                    "academic_class_stream__academic_class__Class",
                )
                .order_by("id")
            )

            if not registers:
                counts["missing_register"] += 1
                self._issue(
                    student,
                    "MISSING_REGISTER",
                    "No ClassRegister exists for the selected academic period.",
                )
                continue

            if len(registers) > 1:
                counts["multiple_registers"] += 1
                labels = ", ".join(
                    f"{row.academic_class_stream.academic_class.Class} / "
                    f"{row.academic_class_stream.stream}"
                    for row in registers
                )
                self._issue(
                    student,
                    "MULTIPLE_REGISTERS",
                    f"More than one registration exists: {labels}. Manual review required.",
                )
                continue

            register = registers[0]
            class_stream = register.academic_class_stream
            academic_class = class_stream.academic_class

            snapshot_mismatches = []
            if student.current_class_id != academic_class.Class_id:
                snapshot_mismatches.append("class")
            if student.stream_id != class_stream.stream_id:
                snapshot_mismatches.append("stream")
            if student.academic_year_id != academic_class.academic_year_id:
                snapshot_mismatches.append("academic year")
            if student.term_id != academic_class.term_id:
                snapshot_mismatches.append("term")

            bill_exists = StudentBill.objects.filter(
                student=student,
                academic_class=academic_class,
            ).exists()

            if snapshot_mismatches:
                counts["snapshot_mismatch"] += 1
                self._issue(
                    student,
                    "SNAPSHOT_MISMATCH",
                    "Student current snapshot differs from the single current registration: "
                    + ", ".join(snapshot_mismatches),
                )

            if not bill_exists:
                counts["missing_bill"] += 1
                self._issue(
                    student,
                    "MISSING_BILL",
                    f"Registered in {academic_class} but no StudentBill exists for that class/period.",
                )

            if not snapshot_mismatches and bill_exists:
                counts["healthy"] += 1

            if repair_safe and (snapshot_mismatches or not bill_exists):
                # This branch is intentionally reachable only when exactly one
                # registration exists for the selected period, making the target
                # state deterministic. No historical row is deleted or moved.
                with transaction.atomic():
                    result = ensure_student_academic_state(
                        student=student,
                        academic_class=academic_class,
                        academic_class_stream=class_stream,
                        sync_snapshot=True,
                        ensure_bill=True,
                    )
                if result.snapshot_updated:
                    counts["repaired_snapshot"] += 1
                if result.bill_created:
                    counts["repaired_bill"] += 1
                counts["safe_repairs"] += 1

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Audit summary"))
        self.stdout.write(f"Active students reviewed: {reviewed}")
        self.stdout.write(f"Healthy: {counts['healthy']}")
        self.stdout.write(f"Missing current registration: {counts['missing_register']}")
        self.stdout.write(f"Multiple current registrations: {counts['multiple_registers']}")
        self.stdout.write(f"Snapshot mismatches: {counts['snapshot_mismatch']}")
        self.stdout.write(f"Missing current-period bills: {counts['missing_bill']}")

        if repair_safe:
            self.stdout.write(f"Safe cases processed: {counts['safe_repairs']}")
            self.stdout.write(f"Snapshots synchronised: {counts['repaired_snapshot']}")
            self.stdout.write(f"Missing bills created: {counts['repaired_bill']}")
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "Dry run complete. No database rows were changed. "
                    "Review the issues before considering --repair-safe."
                )
            )

    def _resolve_year(self, raw):
        if raw:
            raw = str(raw).strip()
            qs = AcademicYear.objects.all()
            year = qs.filter(academic_year=raw).first()
            if year is None and raw.isdigit():
                year = qs.filter(pk=int(raw)).first()
        else:
            year = AcademicYear.objects.filter(is_current=True).first()

        if year is None:
            raise CommandError("Could not resolve an academic year.")
        return year

    def _resolve_term(self, year, raw):
        if raw:
            raw = str(raw).strip()
            qs = Term.objects.filter(academic_year=year)
            term = qs.filter(term=raw).first()
            if term is None and raw.isdigit():
                term = qs.filter(pk=int(raw)).first()
        else:
            term = Term.objects.filter(academic_year=year, is_current=True).first()

        if term is None:
            raise CommandError(
                f"Could not resolve a term for academic year {year.academic_year}."
            )
        return term

    def _issue(self, student, code, detail):
        self.stdout.write(
            f"[{code}] {student.reg_no or student.pk} | {student.student_name} | {detail}"
        )
