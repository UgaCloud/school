from django.db import models
from app.constants import *

class Student(models.Model):
    
    reg_no = models.CharField(max_length=30)
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
    photo = models.ImageField(upload_to="student_photos", null=True, blank=True)

    class Meta:
        verbose_name = ("student")
        verbose_name_plural = ("students")

    def __str__(self):
        return self.student_name

    def get_absolute_url(self):
        return reverse("student_detail", kwargs={"pk": self.pk})

class StudentRegistrationCSV(models.Model):
    file_name = models.FileField(upload_to='media/csvs/')
    uploaded = models.DateTimeField(auto_now_add=True)
    activated = models.BooleanField(default=False)

    def __str__(self):
        return f"File ID: {self.id}"
    
class ClassRegister(models.Model):
    
    academic_class_stream = models.ForeignKey("app.AcademicClassStream", on_delete=models.CASCADE)
    student = models.ForeignKey("app.Student", on_delete=models.CASCADE)
    payment_status = models.CharField(max_length=10, default=0)

    class Meta:
        verbose_name = ("ClassRegister")
        verbose_name_plural = ("ClassRegisters")
        unique_together = ("academic_class_stream", "student")

    def __str__(self):
        return self._class

    def get_absolute_url(self):
        return reverse("ClassRegister_detail", kwargs={"pk": self.pk})
