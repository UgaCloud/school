from django.db import models
from datetime import date

from app.constants import PAYMENT_STATUS

class Expense(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Vendor(models.Model):
    name = models.CharField(max_length=100)
    contact_information = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.name

class Expenditure(models.Model):
    department = models.ForeignKey("app.Department", on_delete=models.CASCADE, related_name='expenses')
    expense = models.ForeignKey("app.Expense", on_delete=models.CASCADE, related_name='expenses')
    vendor = models.ForeignKey("app.Vendor", on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    description = models.TextField()
    amount = models.IntegerField()
    date_incurred = models.DateField()
    date_recorded = models.DateField(auto_now_add=True)
    approved_by = models.CharField(max_length=100)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='Pending')
    receipt = models.FileField(upload_to='receipts/', blank=True, null=True)

    def __str__(self):
        return f'{self.description} - {self.amount}'

class Budget(models.Model):
    department = models.ForeignKey("app.Department", on_delete=models.CASCADE, related_name='budgets')
    category = models.ForeignKey("app.Expense", on_delete=models.CASCADE, related_name='budgets')
    allocated_amount = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()

    @property
    def amount_spent(self):
        expenses = Expenditure.objects.filter(department=self.department, expense=self.expense, date_incurred__range=(self.start_date, self.end_date))
        return expenses.aggregate(total=models.Sum('amount'))['total'] or 0

    @property
    def remaining_amount(self):
        return self.allocated_amount - self.amount_spent

    def __str__(self):
        return f'{self.department} - {self.category} Budget for {self.start_date} to {self.end_date}'
