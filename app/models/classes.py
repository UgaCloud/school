from django.db import models

class Class(models.Model):
    
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=3)

    class Meta:
        verbose_name = ("Class")
        verbose_name_plural = ("Classs")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("Class_detail", kwargs={"pk": self.pk})

class Stream(models.Model):
    
    stream = models.CharField(max_length=10)

    class Meta:
        verbose_name = ("stream")
        verbose_name_plural = ("streams")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("stream_detail", kwargs={"pk": self.pk})

class AcademicClass(models.Model):
    
    _class = models.ForeignKey("app.Class", on_delete=models.CASCADE)
    academic_year = models.CharField(max_length=10)
    term = models.IntegerField()
    fees_amount = models.IntegerField()

    class Meta:
        verbose_name = ("AcademicClass")
        verbose_name_plural = ("AcademicClasss")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("AcademicClass_detail", kwargs={"pk": self.pk})

