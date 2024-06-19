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
    entry_year = models.IntegerField()
    _class = models.ForeignKey("app.Class", verbose_name="Current Class", on_delete=models.CASCADE)
    photo = models.ImageField(upload_to="student_photos")

    class Meta:
        verbose_name = ("student")
        verbose_name_plural = ("students")

    def __str__(self):
        return self.student_name

    def get_absolute_url(self):
        return reverse("student_detail", kwargs={"pk": self.pk})

class ClassRegister(models.Model):
    
    _class = models.ForeignKey("app.AcademicClassStream", on_delete=models.CASCADE)
    student = models.ForeignKey("app.Student", on_delete=models.CASCADE)
    payment_status = models.CharField(max_length=10)

    class Meta:
        verbose_name = ("ClassRegister")
        verbose_name_plural = ("ClassRegisters")

    def __str__(self):
        return self._class

    def get_absolute_url(self):
        return reverse("ClassRegister_detail", kwargs={"pk": self.pk})
