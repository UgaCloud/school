from django.db import models
from django.utils import timezone

from app.models.classes import AcademicClassStream, Term
from app.models.school_settings import AcademicYear
from app.models.students import Student
from app.models.subjects import Subject
from app.models.staffs import Staff
from app.models.timetables import TimeSlot


class AttendanceStatus(models.TextChoices):
    PRESENT = "present", "Present"
    LATE = "late", "Late"
    ABSENT = "absent", "Absent"
    EXCUSED = "excused", "Excused"


class AttendanceSession(models.Model):
    class_stream = models.ForeignKey(
        AcademicClassStream, on_delete=models.CASCADE, related_name="attendance_sessions"
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="attendance_sessions")
    teacher = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="attendance_sessions")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.SET_NULL, null=True, blank=True)
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("class_stream", "subject", "date", "time_slot")
        ordering = ("-date", "class_stream")

    def __str__(self):
        return f"{self.class_stream} - {self.subject} - {self.date}"


class AttendanceRecord(models.Model):
    session = models.ForeignKey(
        AttendanceSession, on_delete=models.CASCADE, related_name="records"
    )
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="attendance_records")
    status = models.CharField(
        max_length=20, choices=AttendanceStatus.choices, default=AttendanceStatus.PRESENT
    )
    remarks = models.CharField(max_length=255, blank=True)
    captured_by = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True)
    captured_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("session", "student")
        ordering = ("student",)

    def __str__(self):
        return f"{self.student} - {self.session} - {self.status}"
