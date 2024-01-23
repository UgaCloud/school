from django.forms import ModelForm

from models.fees_payment import FeesPayment

class FeesPaymentForm(ModelForm):
    
    class Meta:
        model = FeesPayment
        fields = ("__all__",)
