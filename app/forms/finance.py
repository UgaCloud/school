from django.forms import ModelForm, HiddenInput, DateInput
from crispy_forms.helper import FormHelper

from app.models.finance import *

class IncomeSourceForm(ModelForm):
    
    class Meta:
        model = IncomeSource
        fields = ("__all__")

class VendorForm(ModelForm):
    
    class Meta:
        model = Vendor
        fields = ("__all__")


class BudgetForm(ModelForm):
    
    class Meta:
        model = Budget
        fields = ("__all__")

class BudgetItemForm(ModelForm):
    
    class Meta:
        model = BudgetItem
        fields = ("__all__")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Helper = FormHelper()
        self.fields["budget"].widget = HiddenInput()

class ExpenseForm(ModelForm):
    
    class Meta:
        model = Expense
        fields = ("__all__")

class ExpenditureForm(ModelForm):
    
    class Meta:
        model = Expenditure
        fields = ("__all__")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Helper = FormHelper()
        self.fields["date_incurred"].widget = DateInput(attrs={
                    "type": "date",
                })
        
class ExpenditureItemForm(ModelForm):
    
    class Meta:
        model = ExpenditureItem
        fields = ("__all__")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Helper = FormHelper()
        self.fields["expenditure"].widget = HiddenInput()


class TransactionForm(ModelForm):
    
    class Meta:
        model = Transaction
        fields = ("__all__")

