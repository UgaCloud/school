from django.db import models
from django.urls import reverse

from app.constants import TERMS

class Class(models.Model):
    
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=3)
    section = models.ForeignKey("app.Section", on_delete=models.CASCADE)

    class Meta:
        verbose_name = ("Class")
        verbose_name_plural = ("Classes")

    def __str__(self):
        return self.code

    def get_absolute_url(self):
        return reverse("Class_detail", kwargs={"pk": self.pk})

class Stream(models.Model):
    
    stream = models.CharField(max_length=20, unique=True, default="-")

    class Meta:
        verbose_name = ("stream")
        verbose_name_plural = ("streams")

    def __str__(self):
        return self.stream

    def get_absolute_url(self):
        return reverse("stream_detail", kwargs={"pk": self.pk})

class Term(models.Model):
    
    academic_year = models.ForeignKey("app.AcademicYear", on_delete=models.CASCADE)
    term = models.CharField(max_length=5, choices=TERMS)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=True)

    def __str__(self):
        return f'Term {self.term}'

    class Meta:
        verbose_name = ("Term")
        verbose_name_plural = ("Terms")
        unique_together = ("academic_year", "term")

    def get_absolute_url(self):
        return reverse("Term_detail", kwargs={"pk": self.pk})


class AcademicClass(models.Model):
    
    section = models.ForeignKey("app.Section", on_delete=models.CASCADE)
    Class = models.ForeignKey("app.Class", on_delete=models.CASCADE)
    academic_year = models.ForeignKey("app.AcademicYear", on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    fees_amount = models.IntegerField()

    class Meta:
        verbose_name = ("AcademicClass")
        verbose_name_plural = ("AcademicClasses")
        unique_together = ("Class", "academic_year", "term")

    def __str__(self):
        return f"{self.Class} {self.term} - {self.academic_year}"

    def get_absolute_url(self):
        return reverse("AcademicClass_detail", kwargs={"pk": self.pk})

class AcademicClassStream(models.Model):
    academic_class = models.ForeignKey("app.AcademicClass", on_delete=models.CASCADE, related_name="class_streams")
    stream = models.ForeignKey("app.Stream", on_delete=models.CASCADE)
    class_teacher = models.ForeignKey("app.Staff", on_delete=models.CASCADE)
    

    class Meta:
        verbose_name = "Class Stream"
        verbose_name_plural = "Class Streams"
        unique_together = ("academic_class", "stream")

    def __str__(self):
        return f"{self.academic_class} - {self.stream}"

    def get_absolute_url(self):
        return reverse("ClassStream_detail", kwargs={"pk": self.pk})


class ClassSubjectAllocation(models.Model):
    
    academic_class_stream = models.ForeignKey("app.AcademicClassStream",on_delete=models.CASCADE, related_name="subjects")
    subject = models.ForeignKey("app.Subject", on_delete=models.CASCADE, related_name="subjects")
    subject_teacher = models.ForeignKey("app.Staff", on_delete=models.CASCADE, related_name="subjects")

    class Meta:
        verbose_name = ("classsubjectallocation")
        verbose_name_plural = ("classsubjectallocations")

    def __str__(self):
        return f"{self.academic_class_stream} - {self.subject} - {self.subject_teacher}"

    def get_absolute_url(self):
        return reverse("classsubjectallocation_detail", kwargs={"pk": self.pk})

