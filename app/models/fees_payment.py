from django.db import models
from django.urls import reverse
from django.utils import timezone
from app.constants import *
from django.db.models import Sum


class BillItem(models.Model):
    
    item_name = models.CharField(max_length=50)
    category = models.CharField(max_length=50, choices=BILL_CATEGORY_CHOICES)
    bill_duration = models.CharField(max_length=50, choices=BILL_DURATION_CHOICES)
    description = models.TextField()

    class Meta:
        verbose_name = ("billitem")
        verbose_name_plural = ("billitems")

    def __str__(self):
        return self.item_name

    def get_absolute_url(self):
        return reverse("billitem_detail", kwargs={"pk": self.pk})

class StudentBill(models.Model):

    student = models.ForeignKey("app.Student", on_delete=models.CASCADE, related_name='bills')
    bill_date = models.DateField(auto_now_add=True)
    academic_class = models.ForeignKey("app.AcademicClass", on_delete=models.CASCADE)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=BILL_STATUS_CHOICES, default="Unpaid")

    @property
    def total_amount(self):
        return self.items.aggregate(total=models.Sum('amount'))['total'] or 0
    
    @property
    def amount_paid(self):
        return self.payments.aggregate(total=models.Sum('amount'))['total'] or 0
    
    @property
    def balance(self):
        # Calculate balance considering applied credits
        applied_credits = self.applied_credits.filter(amount__lt=0).aggregate(total=Sum('amount'))['total'] or 0
        # applied_credits will be negative, so we add it (which subtracts from balance)
        return self.total_amount - self.amount_paid + applied_credits

    @property
    def available_credits(self):
        """Get total available credits for this student that haven't been applied"""
        
        return self.student.credits.filter(is_applied=False).aggregate(total=Sum('amount'))['total'] or 0

    def apply_credit(self, credit_amount):
        """Apply credit to this bill"""
        if credit_amount <= 0:
            return 0

        # Get available credits for this student
        available_credits = self.available_credits
        if available_credits <= 0:
            return 0

        # Apply the minimum of available credit and needed amount
        credit_to_apply = min(credit_amount, available_credits)

        # Find and update credits (apply oldest first)
        credits = self.student.credits.filter(is_applied=False).order_by('created_date')
        applied_amount = 0

        for credit in credits:
            if applied_amount >= credit_to_apply:
                break

            remaining_needed = credit_to_apply - applied_amount
            amount_from_this_credit = min(remaining_needed, credit.amount)

            # Create a new credit record for the applied portion
            StudentCredit.objects.create(
                student=self.student,
                amount=-amount_from_this_credit,  # Negative to show it's applied
                description=f'Applied to bill #{self.id}',
                is_applied=True,
                applied_date=timezone.now().date(),
                original_bill=credit.original_bill,
                applied_to_bill=self
            )

            applied_amount += amount_from_this_credit

            # Mark original credit as applied if fully used
            if amount_from_this_credit >= credit.amount:
                credit.is_applied = True
                credit.applied_date = timezone.now().date()
                credit.applied_to_bill = self
                credit.save()

        return applied_amount
    
    def __str__(self):
        return f'Bill #{self.id} for {self.student}'

class StudentBillItem(models.Model):
    bill = models.ForeignKey(StudentBill, on_delete=models.CASCADE, related_name='items')
    bill_item = models.ForeignKey("app.BillItem", on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'Item {self.description} for Bill #{self.bill.id}'
    
class ClassBill(models.Model):
    academic_class = models.ForeignKey("app.AcademicClass", on_delete=models.CASCADE, related_name='class_bills')
    bill_item = models.ForeignKey("app.BillItem", on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('academic_class', 'bill_item') 

class Payment(models.Model):
    bill = models.ForeignKey(StudentBill, on_delete=models.CASCADE, related_name='payments')
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS)
    reference_no = models.CharField(max_length=50,unique=True)
    recorded_by = models.CharField(max_length=50)

    def __str__(self):
        return f'Payment of {self.amount} for Bill #{self.bill.id} on {self.payment_date}'
class StudentCredit(models.Model):
    student = models.ForeignKey("app.Student", on_delete=models.CASCADE, related_name='credits')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.CharField(max_length=255)
    created_date = models.DateField(auto_now_add=True)
    applied_date = models.DateField(null=True, blank=True)
    is_applied = models.BooleanField(default=False)
    original_bill = models.ForeignKey(StudentBill, on_delete=models.CASCADE, related_name='generated_credits')
    applied_to_bill = models.ForeignKey(StudentBill, on_delete=models.SET_NULL, null=True, blank=True, related_name='applied_credits')

    def __str__(self):
        return f'Credit of {self.amount} for {self.student.student_name}'

    class Meta:
        ordering = ['-created_date']

    