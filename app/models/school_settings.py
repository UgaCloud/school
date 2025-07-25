from django.db import models
from django.urls import reverse
from AbstractModels.singleton import SingletonModel
from app.constants import *

class Currency(models.Model):
    code = models.CharField(max_length=10, unique=True, default="UGX")
    desc = models.CharField(max_length=20, default="Ugandan Shillings")
    cost = models.CharField(max_length=20, default="1")

    def __str__(self):
        return self.code


class SchoolSetting(SingletonModel):
    COUNTRIES = (
        ("UG", "Uganda"),
        ("KE", "Kenya"),
        ("TZ", "Tanzania"),
        ("RD", "Rwanda"),
        ("BD", "Burundi"),
        ("SD", "South Sudan")
    )
    country = models.CharField(max_length=40, choices=COUNTRIES, default="Uganda")
    city = models.CharField(max_length=40, default="Kampala")
    address = models.CharField(max_length=50, default="None")
    postal = models.CharField(max_length=50, default="None")
    website = models.CharField(max_length=50, default="None")
    school_name = models.CharField(max_length=50, default="None")
    school_motto = models.CharField(max_length=150, default="None")
    mobile = models.CharField(max_length=20, blank=True, null=True)
    office_phone_number1 = models.CharField(max_length=20, blank=True, null=True)
    office_phone_number2 = models.CharField(max_length=40, blank=True, null=True)
    school_logo = models.ImageField(upload_to="logo", height_field=None, width_field=None, max_length=None)
    app_name = models.CharField(max_length=20, default="E-School")
    
   


class AcademicYear(models.Model):
    
    academic_year = models.CharField(max_length=10, unique=True)
    is_current = models.BooleanField(default=True)

    class Meta:
        verbose_name = ("AcademicYear")
        verbose_name_plural = ("AcademicYears")

    def __str__(self):
        return self.academic_year

    def get_absolute_url(self):
        return reverse("AcademicYear_detail", kwargs={"pk": self.pk})


class Section(models.Model):
    
    section_name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = ("section")
        verbose_name_plural = ("sections")

    def __str__(self):
        return self.section_name

    def get_absolute_url(self):
        return reverse("section_detail", kwargs={"pk": self.pk})

class Signature(models.Model):
    
    position = models.CharField(max_length=25,choices=POSITION_SIGNATURE_CHOICES)
    signature = models.ImageField(upload_to="signatures", height_field=None, width_field=None, max_length=None)

    class Meta:
        verbose_name = ("Signature")
        verbose_name_plural = ("Signatures")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("Signature_detail", kwargs={"pk": self.pk})

class Department(models.Model):
    name = models.CharField(max_length=100,choices=TYPE_CHOICES)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name