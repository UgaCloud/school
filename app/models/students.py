from django.db import models
from django.urls import reverse
from django.utils import timezone
from app.constants import GENDERS, NATIONALITIES, RELIGIONS, DOCUMENT_TYPES

class Student(models.Model):
    reg_no = models.CharField(max_length=30, unique=True)
    student_name = models.CharField(max_length=50)
    gender = models.CharField(max_length=2, choices=GENDERS)
    birthdate = models.DateField(auto_now=False)
    nationality = models.CharField(max_length=30, choices=NATIONALITIES)
    religion = models.CharField(max_length=30, choices=RELIGIONS)
    address = models.CharField(max_length=150)
    guardian = models.CharField(max_length=50, verbose_name="Guardian Name")
    relationship = models.CharField(max_length=50)
    contact = models.CharField(max_length=50, verbose_name="Guardian Contact")
    academic_year = models.ForeignKey("app.AcademicYear", verbose_name=("Entry Year"), on_delete=models.CASCADE)
    current_class = models.ForeignKey("app.Class", verbose_name="Current Class", on_delete=models.CASCADE)
    stream = models.ForeignKey("app.Stream", on_delete=models.CASCADE)
    term = models.ForeignKey("app.Term", on_delete=models.CASCADE)
    photo = models.ImageField(upload_to="student_photos", null=True, blank=True, default="student_photos/default.jpg")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = ("student")
        verbose_name_plural = ("students")

    def __str__(self):
        return self.student_name

    def get_absolute_url(self):
        return reverse("student_detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
       
        is_new = self.pk is None
        needs_generation = is_new or not self.reg_no

        if not needs_generation and self.reg_no:
            if Student.objects.filter(reg_no=self.reg_no).exclude(pk=self.pk).exists():
                needs_generation = True

        if needs_generation:
            self.reg_no = self._build_unique_reg_no()

        super().save(*args, **kwargs)

    def _build_unique_reg_no(self) -> str:
        try:
            year_str = str(self.academic_year.academic_year)
            if not year_str or not year_str.isdigit():
                year_str = str(timezone.now().year)
        except Exception:
            year_str = str(timezone.now().year)

        prefix = f"STD{year_str}-"

        # Find the maximum numeric suffix for this prefix
        existing = Student.objects.filter(reg_no__startswith=prefix).values_list('reg_no', flat=True)
        max_seq = 0
        for rn in existing:
            try:
                # Accept formats like 'STD2025-172' -> '172'
                suffix = rn.split('-', 1)[1]
                num = int(''.join(ch for ch in suffix if ch.isdigit()))
                if num > max_seq:
                    max_seq = num
            except Exception:
                continue

        next_seq = max_seq + 1
        candidate = f"{prefix}{next_seq}"
        # Ensure uniqueness even under race conditions
        while Student.objects.filter(reg_no=candidate).exists():
            next_seq += 1
            candidate = f"{prefix}{next_seq}"
        return candidate

class StudentRegistrationCSV(models.Model):
    file_name = models.FileField(upload_to='media/csvs/')
    uploaded = models.DateTimeField(auto_now_add=True)
    activated = models.BooleanField(default=False)

    def __str__(self):
        return f"File ID: {self.id}"
    
class StudentDocument(models.Model):
    student = models.ForeignKey("app.Student", on_delete=models.CASCADE, related_name='documents')
    bill = models.ForeignKey("app.StudentBill", on_delete=models.CASCADE, null=True, blank=True, related_name='documents')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='student_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = ("Student Document")
        verbose_name_plural = ("Student Documents")
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.document_type} - {self.student.student_name}"

    def get_absolute_url(self):
        return reverse("student_document_detail", kwargs={"pk": self.pk})


class ClassRegister(models.Model):

    academic_class_stream = models.ForeignKey("app.AcademicClassStream", on_delete=models.CASCADE)
    student = models.ForeignKey("app.Student", on_delete=models.CASCADE)
    payment_status = models.CharField(max_length=10, default=0)

    class Meta:
        verbose_name = ("ClassRegister")
        verbose_name_plural = ("ClassRegisters")
        unique_together = ("academic_class_stream", "student")

    def __str__(self):
       return f"{self.academic_class_stream} - {self.student}"

    def get_absolute_url(self):
        return reverse("ClassRegister_detail", kwargs={"pk": self.pk})
