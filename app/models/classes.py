from django.db import models

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
    
    stream = models.CharField(max_length=10, unique=True, default="-")

    class Meta:
        verbose_name = ("stream")
        verbose_name_plural = ("streams")

    def __str__(self):
        return self.stream

    def get_absolute_url(self):
        return reverse("stream_detail", kwargs={"pk": self.pk})

class AcademicClass(models.Model):
    
    section = models.ForeignKey("app.Section", on_delete=models.CASCADE)
    Class = models.ForeignKey("app.Class", on_delete=models.CASCADE)
    academic_year = models.ForeignKey("app.AcademicYear", on_delete=models.CASCADE)
    term = models.IntegerField()
    fees_amount = models.IntegerField()

    class Meta:
        verbose_name = ("AcademicClass")
        verbose_name_plural = ("AcademicClasses")
        unique_together = ("Class", "academic_year", "term")

    def __str__(self):
        return f"{self.Class}"

    def get_absolute_url(self):
        return reverse("AcademicClass_detail", kwargs={"pk": self.pk})

class AcademicClassStream(models.Model):
    
    academic_class = models.ForeignKey("app.AcademicClass", on_delete=models.CASCADE, related_name="class_streams")
    stream = models.ForeignKey("app.Stream", on_delete=models.CASCADE)
    class_teacher = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        verbose_name = ("ClassStream")
        verbose_name_plural = ("ClassStreams")
        unique_together = ("academic_class", "stream")

    def __str__(self):
        return f"{self.academic_class.Class} - {self.stream}"

    def get_absolute_url(self):
        return reverse("ClassStream_detail", kwargs={"pk": self.pk})

