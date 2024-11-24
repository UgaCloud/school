from django.db import models
from django.urls import reverse
from app.constants import MEASUREMENTS,PAYMENT_STATUS

class BankAccount(models.Model):
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50, unique=True)
    account_name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=50)
    balance = models.IntegerField()

    def __str__(self):
        return f'{self.account_name} - {self.bank_name}'


class BankAccount(models.Model):
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50, unique=True)
    account_name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=50)
    balance = models.IntegerField()

    def __str__(self):
        return f'{self.account_name} - {self.bank_name}'

class Vendor(models.Model):
    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.name
    
class Expense(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
class Budget(models.Model):
    academic_year = models.ForeignKey("app.AcademicYear", on_delete=models.CASCADE)
    term = models.ForeignKey("app.Term", on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=[("Open", "Open"), ("Closed", "Closed")])

    class Meta:
        verbose_name = ("budget")
        verbose_name_plural = ("budgets")
        unique_together = ("academic_year", "term")
        ordering = ("-id",)

    def __str__(self):
        return f"Budget for {self.academic_year} - {self.term}"

    def get_absolute_url(self):
        return reverse("budget_detail", kwargs={"pk": self.pk})

class BudgetItem(models.Model):
    budget = models.ForeignKey("app.Budget", on_delete=models.CASCADE, related_name="budget_items")
    department = models.ForeignKey("app.Department", on_delete=models.CASCADE, related_name='budgets')
    expense = models.ForeignKey("app.Expense", on_delete=models.CASCADE, related_name='budgets')
    allocated_amount = models.IntegerField()

    @property
    def amount_spent(self):
        budget_expenditures = self.budget_expenditures.all()
        total = sum(item.amount for item in budget_expenditures)
        
        return total or 0

    @property
    def remaining_amount(self):
        return self.allocated_amount - self.amount_spent

    def __str__(self):
        return f'{self.department} - {self.expense}'

class Expenditure(models.Model):
    budget_item = models.ForeignKey("app.BudgetItem", on_delete=models.CASCADE, related_name='budget_expenditures')
    vendor = models.ForeignKey("app.Vendor", on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    description = models.TextField()
    date_incurred = models.DateField()
    date_recorded = models.DateField(auto_now_add=True)
    approved_by = models.CharField(max_length=100)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='Pending')
    attachment = models.FileField(upload_to='attachments/', blank=True, null=True)
    
    def __str__(self):
        return f'{self.description} '
    
    @property
    def amount(self):
        items = self.items.all()
        total = sum(item.amount for item in items)
        
        return total
        

class ExpenditureItem(models.Model):
    
    expenditure = models.ForeignKey("app.Expenditure", on_delete=models.CASCADE, related_name="items")
    item_name = models.CharField(max_length=100)
    quantity = models.IntegerField()
    units = models.CharField(max_length=50, choices=MEASUREMENTS)
    unit_cost = models.IntegerField()

    class Meta:
        verbose_name = ("expenditureitem")
        verbose_name_plural = ("expenditureitems")

    def __str__(self):
        return self.item_name
    
    @property
    def amount(self):
        return self.quantity * self.unit_cost

    def get_absolute_url(self):
        return reverse("expenditureitem_detail", kwargs={"pk": self.pk})


class IncomeSource(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('Income', 'Income'),
        ('Expense', 'Expense')
    ]
    date = models.DateField()
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    related_income_source = models.ForeignKey("app.IncomeSource", on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f'{self.transaction_type} - {self.description} - {self.amount}'

    @property
    def is_income(self):
        return self.transaction_type == 'Income'

    @property
    def is_expense(self):
        return self.transaction_type == 'Expense'

class CashFlowStatement(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()
    generated_on = models.DateField(auto_now_add=True)

    @property
    def total_income(self):
        return Transaction.objects.filter(transaction_type='Income', date__range=(self.start_date, self.end_date)).aggregate(total=models.Sum('amount'))['total'] or 0

    @property
    def total_expenses(self):
        return Transaction.objects.filter(transaction_type='Expense', date__range=(self.start_date, self.end_date)).aggregate(total=models.Sum('amount'))['total'] or 0

    @property
    def net_cash_flow(self):
        return self.total_income - self.total_expenses

    def __str__(self):
        return f'Cash Flow Statement from {self.start_date} to {self.end_date}'
    
