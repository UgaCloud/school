from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from django.urls import reverse

from app.models import (
    AcademicClass, AcademicClassStream, AcademicYear, AdmissionApplication, AdmissionCycle,
    BillItem, Class, ClassBill, ClassRegister, LibraryBook, LibraryCopy, LibraryFine, LibraryLoan, LibraryPolicy, Payment,
    ParentAccess, Section, Staff, Stream, Student, StudentBill, StudentBillItem, Term,
)
from app.services.admissions import EnrollmentError, enroll_application
from app.services.library import CirculationError, issue_copy, mark_loan_lost, resolve_fine, return_loan
from app.services.parent_portal import ParentAccessError, activate_parent_access, deactivate_parent_access, reset_parent_password
from app.services.fees_ledger import build_ledger_rows, get_ledger_filter_options


class ExpansionModuleFoundationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser("admin", "admin@example.com", "safe-password")
        cls.year = AcademicYear.objects.create(academic_year="2026", is_current=True)
        cls.term = Term.objects.create(
            academic_year=cls.year, term="1", start_date=date(2026, 1, 1), end_date=date(2026, 4, 1), is_current=True,
        )
        cls.section = Section.objects.create(section_name="Primary")
        cls.school_class = Class.objects.create(name="Primary One", code="P1", section=cls.section)
        cls.stream = Stream.objects.create(stream="Blue")
        cls.staff = Staff.objects.create(
            first_name="Test", last_name="Teacher", birth_date=date(1990, 1, 1), gender="M",
            address="School", marital_status="S", contacts="0700000000", email="teacher@example.com",
            qualification="Diploma", hire_date=date(2020, 1, 1), department="Academic", salary=1,
            staff_status="Active", staff_photo="Staff/Profile_pics/test.jpg",
        )
        cls.academic_class = AcademicClass.objects.create(
            section=cls.section, Class=cls.school_class, academic_year=cls.year, term=cls.term, fees_amount=0,
        )
        cls.class_stream = AcademicClassStream.objects.create(
            academic_class=cls.academic_class, stream=cls.stream, class_teacher=cls.staff,
        )

    def make_student(self, name="Child One", contact="0772000000"):
        return Student.objects.create(
            student_name=name, gender="M", birthdate=date(2018, 1, 1), nationality="Ugandan",
            religion="Muslim", address="Kampala", guardian="Parent One", relationship="Parent",
            contact=contact, academic_year=self.year, current_class=self.school_class,
            stream=self.stream, term=self.term,
        )

    def test_parent_activation_uses_existing_guardian_contact_and_forces_change(self):
        student = self.make_student()
        access = activate_parent_access(student=student, verified_by=self.admin)
        self.assertEqual(access.user.username, "0772000000")
        self.assertTrue(access.user.check_password("123"))
        self.assertTrue(access.must_change_password)
        self.assertTrue(access.temporary_password_expires_at > timezone.now())

    @override_settings(PARENT_PORTAL_ENABLED=True)
    def test_parent_must_change_temporary_password_before_dashboard(self):
        access = activate_parent_access(student=self.make_student(), verified_by=self.admin)
        response = self.client.post("/parent/login/", {"phone": "0772000000", "password": "123"})
        self.assertRedirects(response, "/parent/change-temporary-password/")
        self.assertRedirects(self.client.get("/parent/"), "/parent/change-temporary-password/")
        response = self.client.post(
            "/parent/change-temporary-password/",
            {"password": "new-private-password", "confirm_password": "new-private-password"},
        )
        self.assertRedirects(response, "/parent/")
        access.refresh_from_db()
        self.assertFalse(access.must_change_password)
        self.assertEqual(self.client.get("/parent/").status_code, 200)
        self.client.logout()
        staff_login = self.client.post("/", {"username": "0772000000", "password": "new-private-password"})
        self.assertEqual(staff_login.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_sibling_link_reuses_parent_without_resetting_private_password(self):
        first = activate_parent_access(student=self.make_student(), verified_by=self.admin)
        first.user.set_password("private-password")
        first.user.save(update_fields=("password",))
        first.must_change_password = False
        first.temporary_password_expires_at = None
        first.save(update_fields=("must_change_password", "temporary_password_expires_at"))
        second = activate_parent_access(
            student=self.make_student(name="Child Two", contact="0772 000 000"), verified_by=self.admin,
        )
        second.user.refresh_from_db()
        self.assertEqual(first.user_id, second.user_id)
        self.assertTrue(second.user.check_password("private-password"))
        self.assertFalse(second.must_change_password)

    def test_parent_activation_rejects_unrelated_user_and_supports_lifecycle(self):
        User.objects.create_user("0700999000", password="existing-private-password")
        with self.assertRaises(ParentAccessError):
            activate_parent_access(
                student=self.make_student(contact="0700999000"), verified_by=self.admin,
            )

        access = activate_parent_access(student=self.make_student(contact="0700888000"), verified_by=self.admin)
        deactivate_parent_access(access_id=access.pk, actor=self.admin, reason="Guardian requested closure")
        access.refresh_from_db()
        access.user.refresh_from_db()
        self.assertFalse(access.is_active)
        self.assertFalse(access.user.is_active)
        access = activate_parent_access(student=access.student, verified_by=self.admin)
        reset_parent_password(user_id=access.user_id, actor=self.admin)
        access.refresh_from_db()
        self.assertTrue(access.must_change_password)
        self.assertTrue(access.user.check_password("123"))

    def test_library_copy_cannot_be_issued_twice_and_return_is_idempotent(self):
        student = self.make_student()
        book = LibraryBook.objects.create(title="Mathematics")
        copy = LibraryCopy.objects.create(book=book, accession_number="LIB-1", barcode="LIB-1")
        loan = issue_copy(copy_id=copy.pk, actor=self.admin, student_id=student.pk)
        with self.assertRaises(CirculationError):
            issue_copy(copy_id=copy.pk, actor=self.admin, student_id=student.pk)
        first_returned_at = return_loan(loan_id=loan.pk, actor=self.admin).returned_at
        self.assertEqual(return_loan(loan_id=loan.pk, actor=self.admin).returned_at, first_returned_at)

    def test_library_overdue_damage_loss_and_fine_resolution_are_audited_workflows(self):
        student = self.make_student(contact="0700777000")
        LibraryPolicy.objects.create(borrower_type="student", loan_days=14, daily_fine=100)
        book = LibraryBook.objects.create(title="Science")
        copy = LibraryCopy.objects.create(book=book, accession_number="SCI-1", barcode="SCI-1", acquisition_cost=5000)
        loan = issue_copy(copy_id=copy.pk, actor=self.admin, student_id=student.pk)
        loan.due_at = timezone.now() - timedelta(days=2)
        loan.save(update_fields=("due_at",))
        return_loan(loan_id=loan.pk, actor=self.admin, condition="damaged", damage_amount=750, notes="Torn cover")
        reasons = set(loan.fines.values_list("reason", flat=True))
        self.assertEqual(reasons, {LibraryFine.REASON_OVERDUE, LibraryFine.REASON_DAMAGED})
        outstanding = loan.fines.get(reason=LibraryFine.REASON_DAMAGED)
        resolve_fine(fine_id=outstanding.pk, actor=self.admin, resolution=LibraryFine.STATUS_WAIVED)
        outstanding.refresh_from_db()
        self.assertEqual(outstanding.status, LibraryFine.STATUS_WAIVED)

        lost_copy = LibraryCopy.objects.create(book=book, accession_number="SCI-2", barcode="SCI-2", acquisition_cost=5000)
        with self.assertRaises(CirculationError):
            issue_copy(copy_id=lost_copy.pk, actor=self.admin, student_id=student.pk)
        for fine in loan.fines.filter(status=LibraryFine.STATUS_OUTSTANDING):
            resolve_fine(fine_id=fine.pk, actor=self.admin, resolution=LibraryFine.STATUS_PAID)
        lost_loan = issue_copy(copy_id=lost_copy.pk, actor=self.admin, student_id=student.pk)
        mark_loan_lost(loan_id=lost_loan.pk, actor=self.admin, amount=5000, notes="Not recovered")
        lost_copy.refresh_from_db()
        self.assertEqual(lost_copy.status, LibraryCopy.STATUS_LOST)
        self.assertEqual(lost_loan.fines.get(reason=LibraryFine.REASON_LOST).amount, 5000)

    def test_admission_enrollment_creates_existing_student_and_register(self):
        cycle = AdmissionCycle.objects.create(
            name="Main intake", academic_year=self.year, opens_on=date(2026, 1, 1), closes_on=date(2026, 12, 1), is_active=True,
        )
        application = AdmissionApplication.objects.create(
            cycle=cycle, student_name="New Student", gender="F", birthdate=date(2018, 2, 1),
            nationality="Ugandan", religion="Muslim", address="Kampala", applying_class=self.school_class,
            preferred_stream=self.stream, guardian="New Parent", relationship="Mother", contact="0788000000",
            status=AdmissionApplication.STATUS_ACCEPTED, created_by=self.admin,
        )
        student = enroll_application(application_id=application.pk, actor=self.admin)
        application.refresh_from_db()
        self.assertEqual(application.enrolled_student, student)
        self.assertEqual(application.status, AdmissionApplication.STATUS_ENROLLED)
        self.assertTrue(ClassRegister.objects.filter(student=student, academic_class_stream=self.class_stream).exists())
        self.assertTrue(StudentBill.objects.filter(student=student, academic_class=self.academic_class).exists())
        self.assertEqual(enroll_application(application_id=application.pk, actor=self.admin), student)

    def test_public_admission_submission_duplicate_protection_and_private_tracking(self):
        cycle = AdmissionCycle.objects.create(
            name="Online intake", academic_year=self.year,
            opens_on=timezone.localdate() - timedelta(days=1),
            closes_on=timezone.localdate() + timedelta(days=30), is_active=True,
        )
        payload = {
            "cycle": cycle.pk, "student_name": "Online Learner", "gender": "F",
            "birthdate": "2018-03-04", "nationality": "Ugandan", "religion": "Muslim",
            "address": "Kampala", "applying_class": self.school_class.pk,
            "preferred_stream": self.stream.pk, "previous_school": "Previous School",
            "guardian": "Online Parent", "relationship": "Mother", "contact": "0777 555 444",
            "privacy_consent": "on", "website": "",
        }
        response = self.client.post(reverse("public_admission_apply"), payload, REMOTE_ADDR="10.1.1.1")
        self.assertEqual(response.status_code, 200)
        application = AdmissionApplication.objects.get(student_name="Online Learner")
        self.assertEqual(application.status, AdmissionApplication.STATUS_SUBMITTED)
        self.assertEqual(application.source, AdmissionApplication.SOURCE_PUBLIC)
        self.assertIsNotNone(application.privacy_consent_at)
        self.assertContains(response, application.application_number)

        duplicate = self.client.post(reverse("public_admission_apply"), payload, REMOTE_ADDR="10.1.1.1")
        self.assertContains(duplicate, "already exists")
        self.assertEqual(AdmissionApplication.objects.filter(student_name="Online Learner").count(), 1)

        wrong = self.client.post(
            reverse("public_admission_track"),
            {"application_number": application.application_number, "contact": "000000"},
            REMOTE_ADDR="10.1.1.2",
        )
        self.assertContains(wrong, "could not be verified")
        self.assertNotContains(wrong, "Online Learner")
        correct = self.client.post(
            reverse("public_admission_track"),
            {"application_number": application.application_number, "contact": "0777555444"},
            REMOTE_ADDR="10.1.1.2",
        )
        self.assertContains(correct, "Online Learner")
        self.assertContains(correct, "Submitted")

    def _create_finance_rows(self, student, prefix):
        tuition = BillItem.objects.get_or_create(
            item_name="School Fees",
            defaults={"category": "Tuition", "bill_duration": "Termly", "description": "Tuition"},
        )[0]
        transport = BillItem.objects.get_or_create(
            item_name="Transport",
            defaults={"category": "Transport", "bill_duration": "Termly", "description": "Transport"},
        )[0]
        bill, _ = StudentBill.objects.get_or_create(student=student, academic_class=self.academic_class)
        bill.items.all().delete()
        bill.payments.all().delete()
        StudentBillItem.objects.create(
            bill=bill, bill_item=tuition, description="School Fees", amount=1000, fee_category="Tuition",
        )
        StudentBillItem.objects.create(
            bill=bill, bill_item=transport, description="Transport", amount=200, fee_category="Transport",
        )
        Payment.objects.create(
            bill=bill, payment_date=date(2026, 2, 1), amount=500, payment_method="Cash",
            fee_category="Tuition", reference_no=f"{prefix}-T", recorded_by="admin",
        )
        Payment.objects.create(
            bill=bill, payment_date=date(2026, 2, 2), amount=100, payment_method="Cash",
            fee_category="Transport", reference_no=f"{prefix}-O", recorded_by="admin",
        )
        return bill

    def test_operational_ledger_excludes_inactive_but_individual_history_can_include_it(self):
        active = self.make_student(name="Active Child", contact="0700000001")
        inactive = self.make_student(name="Inactive Child", contact="0700000002")
        inactive.is_active = False
        inactive.save(update_fields=("is_active",))
        self._create_finance_rows(active, "ACTIVE")
        self._create_finance_rows(inactive, "INACTIVE")

        operational = build_ledger_rows()
        self.assertEqual(operational["student_count"], 1)
        self.assertEqual(operational["total_charged"], 1200)
        self.assertEqual(list(get_ledger_filter_options()["students"]), [active])

        historical = build_ledger_rows(student_id=str(inactive.pk), include_inactive=True)
        self.assertEqual(historical["student_count"], 1)
        self.assertEqual(historical["total_charged"], 1200)

    def test_student_directory_defaults_to_all_and_searches_multiple_terms_and_guardian(self):
        active = self.make_student(name="Amina Nakato", contact="0772 123 456")
        active.guardian = "Sarah Namusoke"
        active.save(update_fields=("guardian",))
        inactive = self.make_student(name="Inactive Learner", contact="0700123456")
        inactive.is_active = False
        inactive.save(update_fields=("is_active",))
        self.client.force_login(self.admin)

        response = self.client.get(reverse("student_page"))
        self.assertEqual(response.context["status"], "all")
        self.assertEqual(response.context["students"].paginator.count, 2)

        response = self.client.get(reverse("student_page"), {"q": "Amina Naka", "status": "all"})
        self.assertEqual(list(response.context["students"].object_list), [active])
        response = self.client.get(reverse("student_page"), {"q": "Sarah Namu", "status": "all"})
        self.assertEqual(list(response.context["students"].object_list), [active])
        response = self.client.get(reverse("student_page"), {"q": "0772 123", "status": "all"})
        self.assertEqual(list(response.context["students"].object_list), [active])

    def test_fee_status_and_financial_summary_exclude_inactive_and_do_not_double_count_templates(self):
        active = self.make_student(name="Active Child", contact="0700000011")
        inactive = self.make_student(name="Inactive Child", contact="0700000012")
        inactive.is_active = False
        inactive.save(update_fields=("is_active",))
        self._create_finance_rows(active, "ACTIVE2")
        self._create_finance_rows(inactive, "INACTIVE2")
        transport = BillItem.objects.get(item_name="Transport")
        ClassBill.objects.create(academic_class=self.academic_class, bill_item=transport, amount=200)

        self.client.force_login(self.admin)
        status_response = self.client.get(reverse("fees_status"), {"year": self.year.pk, "term": self.term.pk})
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.context["all_student_fees_count"], 1)
        self.assertEqual(status_response.context["total_fees"], 1200)

        report_response = self.client.get(
            reverse("financial_summary_report"),
            {"academic_year": self.year.pk, "term": self.term.pk},
        )
        self.assertEqual(report_response.status_code, 200)
        self.assertEqual(report_response.context["total_school_fees_billed"], 1000)
        self.assertEqual(report_response.context["debug_info"]["total_other_fees_billed_global"], 200)
        self.assertEqual(report_response.context["total_school_fees_collected"], 500)
        self.assertEqual(report_response.context["total_other_fees_collected"], 100)

    def test_bulk_class_billing_is_rerunnable_and_uses_active_period_registrations(self):
        active = self.make_student(name="Registered Active", contact="0700000021")
        inactive = self.make_student(name="Registered Inactive", contact="0700000022")
        inactive.is_active = False
        inactive.save(update_fields=("is_active",))
        ClassRegister.objects.create(academic_class_stream=self.class_stream, student=active)
        ClassRegister.objects.create(academic_class_stream=self.class_stream, student=inactive)
        self._create_finance_rows(active, "BULK-A")
        self._create_finance_rows(inactive, "BULK-I")
        transport = BillItem.objects.get(item_name="Transport")
        self.client.force_login(self.admin)

        endpoint = reverse("bulk_create_class_bills")
        payload = {"selected_classes": [str(self.school_class.pk)], "bill_item": transport.pk, "amount": "300"}
        self.assertEqual(self.client.post(endpoint, payload).status_code, 302)
        active_item = StudentBillItem.objects.get(
            bill__student=active, bill__academic_class=self.academic_class, bill_item=transport,
        )
        inactive_item = StudentBillItem.objects.get(
            bill__student=inactive, bill__academic_class=self.academic_class, bill_item=transport,
        )
        self.assertEqual(active_item.amount, 300)
        # Existing historical inactive charge is not rewritten by current billing.
        self.assertEqual(inactive_item.amount, 200)

        payload["amount"] = "400"
        self.assertEqual(self.client.post(endpoint, payload).status_code, 302)
        active_item.refresh_from_db()
        inactive_item.refresh_from_db()
        self.assertEqual(active_item.amount, 400)
        self.assertEqual(inactive_item.amount, 200)
