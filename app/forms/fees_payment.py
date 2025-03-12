from django.forms import ModelForm, HiddenInput, DateInput
from crispy_forms.helper import FormHelper
from app.models.fees_payment import BillItem, StudentBillItem, Payment,ClassBill

class BillItemForm(ModelForm):
    
    class Meta:
        model = BillItem
        fields = ("__all__")


class StudentBillItemForm(ModelForm):
    
    class Meta:
        model = StudentBillItem
        fields = ("bill", "bill_item", "description", "amount")
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Helper = FormHelper()
        self.fields["bill"].widget = HiddenInput()



class ClassBillForm(ModelForm):
    class Meta:
        model = ClassBill
        fields = ['bill_item','amount']


class PaymentForm(ModelForm):
    
    class Meta:
        model = Payment
        fields = ("__all__")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Helper = FormHelper()
        self.fields["bill"].widget = HiddenInput()
        self.fields["payment_date"].widget = DateInput(attrs={
                    "type": "date",
                })
