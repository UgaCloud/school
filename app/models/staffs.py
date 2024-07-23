from django.db import models
from app.constants import GENDERS, EMPLOYEE_STATUS, TYPE_CHOICES, MARITAL_STATUS

class Staff(models.Model):
    
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)
    birth_date = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDERS)
    address = models.TextField()
    marital_status = models.CharField(max_length=1, choices=MARITAL_STATUS)
    contacts = models.CharField(max_length=20)
    email = models.EmailField(max_length=254)
    qualification = models.CharField(max_length=100)
    hire_date = models.DateField()
    department = models.CharField(max_length=30,choices=TYPE_CHOICES)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    staff_status = models.CharField(max_length=20, choices=EMPLOYEE_STATUS, default="Active")
    staff_photo = models.ImageField(upload_to="Staff/Profile_pics", height_field=None, width_field=None, max_length=None)


    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    class Meta:
        verbose_name = ("Staff")
        verbose_name_plural = ("Staffs")
        ordering = ("-id",)

    def get_absolute_url(self):
        return reverse("Staff_detail", kwargs={"pk": self.pk})

class BankDetail(models.Model):
    
    staff = models.OneToOneField("app.Staff", on_delete=models.CASCADE)
    bank_name = models.CharField(max_length=50)
    branch_name = models.CharField(max_length=50)
    account_no = models.CharField(max_length=50)
    account_name = models.CharField(max_length=50)

    class Meta:
        verbose_name = ("bankdetail")
        verbose_name_plural = ("bankdetails")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("bankdetail_detail", kwargs={"pk": self.pk})

class StaffDocument(models.Model):
    
    staff = models.ForeignKey("app.Staff", on_delete=models.CASCADE)
    document_type = models.CharField(max_length=50)
    file = models.FileField(upload_to="Staff/Documents", max_length=100)

    class Meta:
        verbose_name = ("StaffDocument")
        verbose_name_plural = ("StaffDocuments")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("StaffDocument_detail", kwargs={"pk": self.pk})

