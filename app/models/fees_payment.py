from django.db import models

class FeesPayment(models.Model):
    
    payment_date = models.DateField(auto_now_add=False)
    student = models.ForeignKey("app.Student", verbose_name=(""), on_delete=models.CASCADE)
    _class = models.ForeignKey("app.AcademicClass", verbose_name=(""), on_delete=models.CASCADE)
    payment_mode = models.CharField(max_length=50)
    reference_no = models.CharField(max_length=50)
    recorded_by = models.CharField(max_length=50)

    class Meta:
        verbose_name = ("FeesPayment")
        verbose_name_plural = ("FeesPayments")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("FeesPayment_detail", kwargs={"pk": self.pk})
