from django.db import models

from app.constants import BILL_STATUS_CHOICES, PAYMENT_METHODS

class StudentBill(models.Model):

    student = models.ForeignKey("app.Student", on_delete=models.CASCADE, related_name='bills')
    bill_date = models.DateField(auto_now_add=True)
    academic_year = models.ForeignKey("app.AcademicYear", on_delete=models.CASCADE)
    term = models.ForeignKey("app.Term", on_delete=models.CASCADE)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=BILL_STATUS_CHOICES, default="Unpaid")

    @property
    def total_amount(self):
        return self.items.aggregate(total=models.Sum('amount'))['total'] or 0
    
    def __str__(self):
        return f'Bill #{self.id} for {self.student}'

class StudentBillItem(models.Model):
    bill = models.ForeignKey(StudentBill, on_delete=models.CASCADE, related_name='items')
    bill_item = models.ForeignKey("app.BillItem", on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'Item {self.description} for Bill #{self.bill.id}'

class Payment(models.Model):
    bill = models.ForeignKey(StudentBill, on_delete=models.CASCADE, related_name='payments')
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS)
    reference_no = models.CharField(max_length=50)
    recorded_by = models.CharField(max_length=50)

    def __str__(self):
        return f'Payment of {self.amount} for Bill #{self.bill.id} on {self.payment_date}'
    
    