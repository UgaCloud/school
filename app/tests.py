from datetime import date

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from app.models.classes import AcademicClass, AcademicClassStream, Class, Stream, Term
from app.models.school_settings import AcademicYear, Section
from app.models.staffs import Staff


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
