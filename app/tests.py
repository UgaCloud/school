from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from app.models.classes import (
    AcademicClass,
    AcademicClassStream,
    Class,
    Stream,
    StudentPromotionHistory,
    Term,
)
from app.models.results import (
    Assessment,
    AssessmentType,
    Result,
    ResultVerificationSetting,
    VerificationCorrectionLog,
    VerificationDiscrepancy,
    VerificationSample,
)
from app.models.school_settings import AcademicYear, SchoolSetting, Section
from app.models.staffs import Staff
from app.models.students import ClassRegister, Student
from app.models.subjects import Subject
from app.services.level_scope import get_level_classes_queryset, get_level_sections_queryset
from app.services.results_sampling import submit_batch_for_verification
from app.services.school_level import get_active_school_level
from core.tenant import register_database_alias, unregister_database_alias


class QuickSetupStudentFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="admin", password="pass12345")
        self.client.force_login(self.user)

        self.year = AcademicYear.objects.create(academic_year="2026", is_current=True)
        self.term = Term.objects.create(
            academic_year=self.year,
            term="1",
            start_date=date(2026, 1, 10),
            end_date=date(2026, 4, 10),
            is_current=True,
        )
        self.section = Section.objects.create(section_name="Secondary")
        self.class_obj = Class.objects.create(name="Senior 1", code="S1", section=self.section)
        self.stream = Stream.objects.create(stream="A")

    def _make_staff(self, first_name, last_name, is_academic_staff):
        return Staff.objects.create(
            first_name=first_name,
            last_name=last_name,
            birth_date=date(1990, 1, 1),
            gender="M",
            address="Address",
            marital_status="U",
            contacts="0700000000",
            email=f"{first_name.lower()}@example.com",
            qualification="Degree",
            nin_no="CFX1234567890A",
            hire_date=date(2020, 1, 1),
            department="Academic",
            salary="1000000.00",
            is_academic_staff=is_academic_staff,
            is_administrator_staff=not is_academic_staff,
            is_support_staff=False,
            staff_status="Active",
            staff_photo=SimpleUploadedFile("staff.jpg", b"fake-image-bytes", content_type="image/jpeg"),
        )

    def test_quick_create_academic_class_creates_record(self):
        response = self.client.post(
            reverse("quick_create_academic_class"),
            {
                "quick_class_id": self.class_obj.id,
                "quick_section_id": self.section.id,
                "quick_fees_amount": "150000",
            },
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            AcademicClass.objects.filter(
                Class=self.class_obj,
                section=self.section,
                academic_year=self.year,
                term=self.term,
            ).exists()
        )

    def test_quick_create_class_stream_requires_existing_academic_class(self):
        teacher = self._make_staff("John", "Teacher", True)

        response = self.client.post(
            reverse("quick_create_class_stream"),
            {
                "quick_stream_class_id": self.class_obj.id,
                "quick_stream_id": self.stream.id,
                "quick_teacher_id": teacher.id,
            },
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(AcademicClassStream.objects.exists())

    def test_quick_create_class_stream_rejects_non_academic_staff(self):
        academic_class = AcademicClass.objects.create(
            Class=self.class_obj,
            section=self.section,
            academic_year=self.year,
            term=self.term,
            fees_amount=120000,
        )
        admin_staff = self._make_staff("Jane", "Admin", False)

        response = self.client.post(
            reverse("quick_create_class_stream"),
            {
                "quick_stream_class_id": self.class_obj.id,
                "quick_stream_id": self.stream.id,
                "quick_teacher_id": admin_staff.id,
            },
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            AcademicClassStream.objects.filter(
                academic_class=academic_class,
                stream=self.stream,
            ).exists()
        )

    def test_quick_create_class_stream_creates_for_academic_staff(self):
        academic_class = AcademicClass.objects.create(
            Class=self.class_obj,
            section=self.section,
            academic_year=self.year,
            term=self.term,
            fees_amount=120000,
        )
        teacher = self._make_staff("Amina", "Tutor", True)

        response = self.client.post(
            reverse("quick_create_class_stream"),
            {
                "quick_stream_class_id": self.class_obj.id,
                "quick_stream_id": self.stream.id,
                "quick_teacher_id": teacher.id,
            },
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            AcademicClassStream.objects.filter(
                academic_class=academic_class,
                stream=self.stream,
                class_teacher=teacher,
            ).exists()
        )

class SecondaryLevelScopeTests(TestCase):
    def setUp(self):
        self.primary_section = Section.objects.create(section_name="Primary")
        self.olevel_section = Section.objects.create(section_name="O-Level")
        self.alevel_section = Section.objects.create(section_name="A-Level")

        Class.objects.create(name="Primary 1", code="P1", section=self.primary_section)
        Class.objects.create(name="Senior 1", code="S1", section=self.olevel_section)
        Class.objects.create(name="Senior 5", code="S5", section=self.alevel_section)

    def test_secondary_mode_includes_both_secondary_sections(self):
        sections = get_level_sections_queryset(active_level=SchoolSetting.EducationLevel.SECONDARY_LOWER)
        self.assertSetEqual(
            set(sections.values_list("section_name", flat=True)),
            {"O-Level", "A-Level"},
        )

    def test_secondary_mode_includes_o_level_and_a_level_classes(self):
        classes = get_level_classes_queryset(active_level=SchoolSetting.EducationLevel.SECONDARY_UPPER)
        self.assertSetEqual(set(classes.values_list("code", flat=True)), {"S1", "S5"})

    def test_primary_mode_excludes_secondary_sections(self):
        sections = get_level_sections_queryset(active_level=SchoolSetting.EducationLevel.PRIMARY)
        self.assertSetEqual(set(sections.values_list("section_name", flat=True)), {"Primary"})


class SchoolLevelActivationTests(TestCase):
    def setUp(self):
        self.school_setting = SchoolSetting.load()
        self.factory = RequestFactory()

    def _build_request(self):
        request = self.factory.get("/")
        SessionMiddleware(lambda req: None).process_request(request)
        request.session.save()
        return request

    def test_secondary_default_is_ignored_when_secondary_is_disabled(self):
        self.school_setting.offers_primary = True
        self.school_setting.offers_secondary_lower = False
        self.school_setting.offers_secondary_upper = False
        self.school_setting.education_level = SchoolSetting.EducationLevel.SECONDARY_LOWER
        self.school_setting.save()

        request = self._build_request()
        active_level = get_active_school_level(request=request, school_setting=self.school_setting)

        self.assertEqual(self.school_setting.get_enabled_levels(), [SchoolSetting.EducationLevel.PRIMARY])
        self.assertEqual(active_level, SchoolSetting.EducationLevel.PRIMARY)
        self.assertEqual(request.session.get("active_school_level"), SchoolSetting.EducationLevel.PRIMARY)

    def test_secondary_school_falls_back_to_o_level_when_primary_is_disabled(self):
        self.school_setting.offers_primary = False
        self.school_setting.offers_secondary_lower = True
        self.school_setting.offers_secondary_upper = True
        self.school_setting.education_level = SchoolSetting.EducationLevel.PRIMARY
        self.school_setting.save()

        request = self._build_request()
        active_level = get_active_school_level(request=request, school_setting=self.school_setting)

        self.assertEqual(
            self.school_setting.get_enabled_levels(),
            [
                SchoolSetting.EducationLevel.SECONDARY_LOWER,
                SchoolSetting.EducationLevel.SECONDARY_UPPER,
            ],
        )
        self.assertEqual(active_level, SchoolSetting.EducationLevel.SECONDARY_LOWER)
        self.assertEqual(request.session.get("active_school_level"), SchoolSetting.EducationLevel.SECONDARY_LOWER)


class ResultVerificationWorkflowTests(TestCase):
    def setUp(self):
        self.submitter = User.objects.create_user(username="submitter", password="pass12345")
        self.verifier = User.objects.create_user(username="verifier", password="pass12345")

        self.year = AcademicYear.objects.create(academic_year="2027", is_current=True)
        self.term = Term.objects.create(
            academic_year=self.year,
            term="1",
            start_date=date(2027, 1, 10),
            end_date=date(2027, 4, 10),
            is_current=True,
        )
        self.section = Section.objects.create(section_name="Verification Secondary")
        self.class_obj = Class.objects.create(name="Senior 2", code="S2", section=self.section)
        self.stream = Stream.objects.create(stream="B")
        self.academic_class = AcademicClass.objects.create(
            section=self.section,
            Class=self.class_obj,
            academic_year=self.year,
            term=self.term,
            fees_amount=100000,
        )

        self.class_teacher = self._make_staff("Class", "Teacher")
        self.class_stream = AcademicClassStream.objects.create(
            academic_class=self.academic_class,
            stream=self.stream,
            class_teacher=self.class_teacher,
        )

        self.subject = Subject.objects.create(
            code="MTH",
            name="Mathematics",
            description="Math",
            credit_hours=4,
            section=self.section,
            type="Core",
        )
        self.assessment_type = AssessmentType.objects.create(name="CAT", weight=Decimal("100.00"))
        self.assessment = Assessment.objects.create(
            academic_class=self.academic_class,
            assessment_type=self.assessment_type,
            subject=self.subject,
            date=date(2027, 2, 10),
            out_of=100,
        )

        self.student_one = self._make_student("Student One", "REG-001")
        self.student_two = self._make_student("Student Two", "REG-002")
        ClassRegister.objects.create(academic_class_stream=self.class_stream, student=self.student_one)
        ClassRegister.objects.create(academic_class_stream=self.class_stream, student=self.student_two)

        self.result_one = Result.objects.create(
            assessment=self.assessment,
            student=self.student_one,
            score=Decimal("55.00"),
            status="DRAFT",
        )
        self.result_two = Result.objects.create(
            assessment=self.assessment,
            student=self.student_two,
            score=Decimal("70.00"),
            status="DRAFT",
        )

        ResultVerificationSetting.objects.create(
            sample_percent=Decimal("100.00"),
            tolerance_marks=Decimal("1.00"),
        )

    def _make_staff(self, first_name, last_name):
        return Staff.objects.create(
            first_name=first_name,
            last_name=last_name,
            birth_date=date(1990, 1, 1),
            gender="M",
            address="Address",
            marital_status="U",
            contacts="0700000000",
            email=f"{first_name.lower()}.{last_name.lower()}@example.com",
            qualification="Degree",
            nin_no="CFX1234567890A",
            hire_date=date(2020, 1, 1),
            department="Academic",
            salary="1000000.00",
            is_academic_staff=True,
            is_administrator_staff=False,
            is_support_staff=False,
            staff_status="Active",
            staff_photo=SimpleUploadedFile("staff.jpg", b"fake-image-bytes", content_type="image/jpeg"),
        )

    def _make_student(self, name, reg_no):
        return Student.objects.create(
            reg_no=reg_no,
            student_name=name,
            gender="M",
            birthdate=date(2012, 1, 1),
            nationality="Ugandan",
            religion="Muslim",
            address="Address",
            guardian="Guardian",
            relationship="Parent",
            contact="0700000000",
            academic_year=self.year,
            current_class=self.class_obj,
            stream=self.stream,
            term=self.term,
        )

    def _set_active_role(self, role_name):
        session = self.client.session
        session["active_role_name"] = role_name
        session.save()

    def _submit_pending_batch(self, user):
        batch, sample_count, ok = submit_batch_for_verification(self.assessment, user)
        self.assertTrue(ok)
        self.assertEqual(batch.status, "PENDING")
        self.assertEqual(sample_count, 2)
        return batch

    def _queue_url(self):
        return reverse("verification_queue", args=[self.assessment.id])

    def _sample_map(self, batch):
        return {
            sample.result_id: sample
            for sample in VerificationSample.objects.filter(result__batch=batch).select_related("result")
        }

    def test_cannot_finalize_with_partial_sampled_checks(self):
        batch = self._submit_pending_batch(self.submitter)
        samples = self._sample_map(batch)
        self.client.force_login(self.verifier)
        self._set_active_role("Director of Studies")

        response = self.client.post(
            self._queue_url(),
            {
                "finalize_verification": "1",
                f"dos_mark_{self.result_one.id}": "55",
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        batch.refresh_from_db()
        self.assertEqual(batch.status, "PENDING")
        self.assertEqual(
            VerificationSample.objects.filter(result__batch=batch, checked_at__isnull=True).count(),
            1,
        )
        self.assertEqual(samples[self.result_two.id].matched, None)

    def test_cannot_verify_with_out_of_range_verifier_marks(self):
        batch = self._submit_pending_batch(self.submitter)
        self.client.force_login(self.verifier)
        self._set_active_role("Director of Studies")

        response = self.client.post(
            self._queue_url(),
            {
                "finalize_verification": "1",
                f"dos_mark_{self.result_one.id}": "101",
                f"dos_mark_{self.result_two.id}": "80",
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        batch.refresh_from_db()
        self.assertEqual(batch.status, "PENDING")
        self.assertEqual(
            VerificationSample.objects.filter(result__batch=batch, checked_at__isnull=True).count(),
            2,
        )

    def test_submitter_cannot_verify_own_batch(self):
        batch = self._submit_pending_batch(self.submitter)
        self.client.force_login(self.submitter)
        self._set_active_role("Admin")

        response = self.client.post(
            self._queue_url(),
            {
                "finalize_verification": "1",
                f"dos_mark_{self.result_one.id}": "55",
                f"dos_mark_{self.result_two.id}": "70",
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        batch.refresh_from_db()
        self.assertEqual(batch.status, "PENDING")
        self.assertEqual(
            VerificationSample.objects.filter(result__batch=batch, checked_at__isnull=True).count(),
            2,
        )

    def test_mismatch_requires_reason(self):
        batch = self._submit_pending_batch(self.submitter)
        self.client.force_login(self.verifier)
        self._set_active_role("Director of Studies")

        response = self.client.post(
            self._queue_url(),
            {
                "finalize_verification": "1",
                f"dos_mark_{self.result_one.id}": "60",
                f"dos_mark_{self.result_two.id}": "70",
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        batch.refresh_from_db()
        self.assertEqual(batch.status, "PENDING")
        self.assertEqual(
            VerificationSample.objects.filter(result__batch=batch, checked_at__isnull=True).count(),
            0,
        )

    def test_correction_creates_log_and_updates_discrepancy(self):
        batch = self._submit_pending_batch(self.submitter)

        self.client.force_login(self.verifier)
        self._set_active_role("Director of Studies")
        verify_response = self.client.post(
            self._queue_url(),
            {
                "finalize_verification": "1",
                f"dos_mark_{self.result_one.id}": "60",
                f"dos_mark_{self.result_two.id}": "70",
                "rejection_reason": "Mismatch on sampled script.",
            },
            follow=False,
        )
        self.assertEqual(verify_response.status_code, 302)

        batch.refresh_from_db()
        self.assertEqual(batch.status, "FLAGGED")
        discrepancy = VerificationDiscrepancy.objects.get(batch=batch, result=self.result_one)
        self.assertEqual(discrepancy.corrected_mark, None)

        self.client.force_login(self.submitter)
        self._set_active_role("Teacher")
        correction_response = self.client.post(
            reverse("add_results", args=[self.assessment.id]),
            {
                "save_draft": "1",
                f"score_{self.student_one.id}": "60",
                f"remark_{self.student_one.id}": "Rechecked and updated from script.",
            },
            follow=False,
        )
        self.assertEqual(correction_response.status_code, 302)

        batch.refresh_from_db()
        self.assertEqual(batch.status, "DRAFT")

        correction_log = VerificationCorrectionLog.objects.filter(batch=batch, result=self.result_one).first()
        self.assertIsNotNone(correction_log)
        self.assertEqual(correction_log.old_mark, Decimal("55.00"))
        self.assertEqual(correction_log.new_mark, Decimal("60.00"))

        discrepancy.refresh_from_db()
        self.assertEqual(discrepancy.corrected_mark, Decimal("60.00"))
        self.assertIn("Corrected by", discrepancy.action_taken)

    def test_duplicate_result_creation_blocked(self):
        with self.assertRaises(IntegrityError):
            Result.objects.create(
                assessment=self.assessment,
                student=self.student_one,
                score=Decimal("80.00"),
                status="DRAFT",
            )


class AcademicClassPromotionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="promotion_admin", password="pass12345")
        self.client.force_login(self.user)

        self.section = Section.objects.create(section_name="Secondary")

        self.year_2026 = AcademicYear.objects.create(academic_year="2026")
        self.year_2027 = AcademicYear.objects.create(academic_year="2027")
        self.term_2026 = Term.objects.create(
            academic_year=self.year_2026,
            term="1",
            start_date=date(2026, 1, 10),
            end_date=date(2026, 4, 10),
            is_current=False,
        )
        self.term_2027 = Term.objects.create(
            academic_year=self.year_2027,
            term="1",
            start_date=date(2027, 1, 10),
            end_date=date(2027, 4, 10),
            is_current=True,
        )

        self.s1 = Class.objects.create(name="Senior 1", code="S1", section=self.section)
        self.s2 = Class.objects.create(name="Senior 2", code="S2", section=self.section)
        self.teacher = self._make_staff("Promotion", "Teacher")
        self.stream_a = Stream.objects.create(stream="A")
        self.stream_b = Stream.objects.create(stream="B")

        self.source_class = AcademicClass.objects.create(
            section=self.section,
            Class=self.s1,
            academic_year=self.year_2026,
            term=self.term_2026,
            fees_amount=100000,
        )
        self.target_class = AcademicClass.objects.create(
            section=self.section,
            Class=self.s2,
            academic_year=self.year_2027,
            term=self.term_2027,
            fees_amount=120000,
        )

        self.source_stream_a = AcademicClassStream.objects.get(
            academic_class=self.source_class,
            stream=self.stream_a,
        )
        self.source_stream_b = AcademicClassStream.objects.get(
            academic_class=self.source_class,
            stream=self.stream_b,
        )
        self.target_stream_a = AcademicClassStream.objects.get(
            academic_class=self.target_class,
            stream=self.stream_a,
        )
        self.target_stream_b = AcademicClassStream.objects.get(
            academic_class=self.target_class,
            stream=self.stream_b,
        )

        self.student_active_a = self._make_student(
            name="Active A",
            stream=self.stream_a,
            reg_no="REG-A",
            is_active=True,
        )
        self.student_active_b = self._make_student(
            name="Active B",
            stream=self.stream_b,
            reg_no="REG-B",
            is_active=True,
        )
        self.student_inactive_a = self._make_student(
            name="Inactive A",
            stream=self.stream_a,
            reg_no="REG-C",
            is_active=False,
        )

        ClassRegister.objects.create(
            academic_class_stream=self.source_stream_a,
            student=self.student_active_a,
        )
        ClassRegister.objects.create(
            academic_class_stream=self.source_stream_b,
            student=self.student_active_b,
        )
        ClassRegister.objects.create(
            academic_class_stream=self.source_stream_a,
            student=self.student_inactive_a,
        )

    def _make_staff(self, first_name, last_name):
        return Staff.objects.create(
            first_name=first_name,
            last_name=last_name,
            birth_date=date(1990, 1, 1),
            gender="M",
            address="Address",
            marital_status="U",
            contacts="0700000000",
            email=f"{first_name.lower()}.{last_name.lower()}@example.com",
            qualification="Degree",
            nin_no="CFX1234567890A",
            hire_date=date(2020, 1, 1),
            department="Academic",
            salary="1000000.00",
            is_academic_staff=True,
            is_administrator_staff=False,
            is_support_staff=False,
            staff_status="Active",
            staff_photo=SimpleUploadedFile("staff.jpg", b"fake-image-bytes", content_type="image/jpeg"),
        )

    def _make_student(self, *, name, stream, reg_no, is_active):
        return Student.objects.create(
            reg_no=reg_no,
            student_name=name,
            gender="M",
            birthdate=date(2012, 1, 1),
            nationality="Ugandan",
            religion="Muslim",
            address="Address",
            guardian="Guardian",
            relationship="Parent",
            contact="0700000000",
            academic_year=self.year_2026,
            current_class=self.s1,
            stream=stream,
            term=self.term_2026,
            is_active=is_active,
        )

    def _set_active_role(self, role_name):
        session = self.client.session
        session["active_role_name"] = role_name
        session.save()

    def _promotion_url(self):
        return reverse("promote_academic_class_students", args=[self.source_class.id])

    def _post_promotion(self, data):
        return self.client.post(
            self._promotion_url(),
            data,
            follow=False,
            HTTP_HOST="localhost",
        )

    def test_promotion_workflow_page_renders_for_admin_role(self):
        self._set_active_role("Admin")
        response = self.client.get(
            reverse("student_promotion_workflow"),
            {
                "source_academic_class_id": self.source_class.id,
                "tab": "conditional",
            },
            HTTP_HOST="localhost",
            follow=False,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Student Promotion")
        self.assertContains(response, self.student_active_a.student_name)

    def test_promotion_workflow_page_renders_for_director_of_studies_role(self):
        self._set_active_role("Director of Studies")
        response = self.client.get(
            reverse("student_promotion_workflow"),
            {
                "source_academic_class_id": self.source_class.id,
                "tab": "eligible",
            },
            HTTP_HOST="localhost",
            follow=False,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Student Promotion")
        self.assertContains(response, self.student_active_b.student_name)

    def test_head_teacher_role_cannot_access_promotion_workflow(self):
        self._set_active_role("Head Teacher")
        response = self.client.get(
            reverse("student_promotion_workflow"),
            {
                "source_academic_class_id": self.source_class.id,
                "tab": "eligible",
            },
            HTTP_HOST="localhost",
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("academic_class_page"))

    def test_promote_students_creates_target_registers_and_updates_snapshots(self):
        self._set_active_role("Admin")
        response = self._post_promotion(
            {
                "target_academic_class": self.target_class.id,
                "active_students_only": "on",
            },
        )
        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            ClassRegister.objects.filter(
                academic_class_stream=self.target_stream_a,
                student=self.student_active_a,
            ).exists()
        )
        self.assertTrue(
            ClassRegister.objects.filter(
                academic_class_stream=self.target_stream_b,
                student=self.student_active_b,
            ).exists()
        )
        self.assertFalse(
            ClassRegister.objects.filter(
                academic_class_stream=self.target_stream_a,
                student=self.student_inactive_a,
            ).exists()
        )

        self.student_active_a.refresh_from_db()
        self.student_active_b.refresh_from_db()
        self.assertEqual(self.student_active_a.current_class_id, self.s2.id)
        self.assertEqual(self.student_active_b.current_class_id, self.s2.id)
        self.assertEqual(self.student_active_a.academic_year_id, self.year_2027.id)
        self.assertEqual(self.student_active_b.academic_year_id, self.year_2027.id)
        self.assertEqual(self.student_active_a.term_id, self.term_2027.id)
        self.assertEqual(self.student_active_b.term_id, self.term_2027.id)

        self.student_inactive_a.refresh_from_db()
        self.assertEqual(self.student_inactive_a.current_class_id, self.s1.id)
        self.assertEqual(self.student_inactive_a.academic_year_id, self.year_2026.id)

        history = StudentPromotionHistory.objects.get()
        self.assertEqual(history.promoted_by_id, self.user.id)
        self.assertEqual(history.source_academic_class_id, self.source_class.id)
        self.assertEqual(history.target_academic_class_id, self.target_class.id)
        self.assertTrue(history.active_students_only)
        self.assertEqual(history.total_candidates, 2)
        self.assertEqual(history.promoted_count, 2)
        self.assertEqual(history.already_registered_count, 0)
        self.assertEqual(history.skipped_inactive_count, 1)
        self.assertEqual(history.updated_student_snapshots, 2)
        self.assertEqual(history.missing_stream_names, [])

    def test_submitter_role_without_permission_cannot_promote(self):
        self._set_active_role("Teacher")
        response = self._post_promotion(
            {
                "target_academic_class": self.target_class.id,
                "active_students_only": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            ClassRegister.objects.filter(
                academic_class_stream__academic_class=self.target_class
            ).count(),
            0,
        )
        self.assertEqual(StudentPromotionHistory.objects.count(), 0)

    def test_head_teacher_role_without_permission_cannot_promote(self):
        self._set_active_role("Head Teacher")
        response = self._post_promotion(
            {
                "target_academic_class": self.target_class.id,
                "active_students_only": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            ClassRegister.objects.filter(
                academic_class_stream__academic_class=self.target_class
            ).count(),
            0,
        )
        self.assertEqual(StudentPromotionHistory.objects.count(), 0)

    def test_promotion_stops_when_target_stream_is_missing(self):
        self.target_stream_b.delete()
        self._set_active_role("Admin")
        response = self._post_promotion(
            {
                "target_academic_class": self.target_class.id,
                "active_students_only": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            ClassRegister.objects.filter(
                academic_class_stream__academic_class=self.target_class
            ).count(),
            0,
        )

        self.student_active_a.refresh_from_db()
        self.assertEqual(self.student_active_a.current_class_id, self.s1.id)

        history = StudentPromotionHistory.objects.get()
        self.assertEqual(history.promoted_by_id, self.user.id)
        self.assertEqual(history.promoted_count, 0)
        self.assertEqual(history.total_candidates, 2)
        self.assertEqual(history.skipped_inactive_count, 1)
        self.assertEqual(history.missing_stream_names, ["B"])

    def test_promotion_can_be_scoped_to_one_source_stream(self):
        self._set_active_role("Admin")
        response = self._post_promotion(
            {
                "target_academic_class": self.target_class.id,
                "source_stream": self.source_stream_a.id,
                "active_students_only": "on",
            },
        )
        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            ClassRegister.objects.filter(
                academic_class_stream=self.target_stream_a,
                student=self.student_active_a,
            ).exists()
        )
        self.assertFalse(
            ClassRegister.objects.filter(
                academic_class_stream=self.target_stream_b,
                student=self.student_active_b,
            ).exists()
        )

        history = StudentPromotionHistory.objects.get()
        self.assertEqual(history.source_stream_id, self.source_stream_a.id)
        self.assertEqual(history.total_candidates, 1)
        self.assertEqual(history.promoted_count, 1)


@override_settings(
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
)
class RuntimeDatabaseAliasConfigTests(SimpleTestCase):
    def tearDown(self):
        unregister_database_alias("tenant_runtime_test")
        unregister_database_alias("tenant_runtime_test_2")
        super().tearDown()

    def test_register_database_alias_adds_backend_defaults(self):
        register_database_alias(
            "tenant_runtime_test",
            {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            },
        )

        alias_config = settings.DATABASES["tenant_runtime_test"]
        self.assertIn("TIME_ZONE", alias_config)
        self.assertIn("OPTIONS", alias_config)
        self.assertIn("TEST", alias_config)
        self.assertEqual(alias_config["TIME_ZONE"], None)
        self.assertEqual(alias_config["OPTIONS"], {})
        self.assertEqual(alias_config["TEST"]["MIGRATE"], True)

    def test_register_database_alias_preserves_explicit_values(self):
        register_database_alias(
            "tenant_runtime_test_2",
            {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
                "TIME_ZONE": "UTC",
                "OPTIONS": {"timeout": 20},
                "TEST": {"MIRROR": "default"},
            },
        )

        alias_config = settings.DATABASES["tenant_runtime_test_2"]
        self.assertEqual(alias_config["TIME_ZONE"], "UTC")
        self.assertEqual(alias_config["OPTIONS"], {"timeout": 20})
        self.assertEqual(alias_config["TEST"]["MIRROR"], "default")
        self.assertEqual(alias_config["TEST"]["MIGRATE"], True)
