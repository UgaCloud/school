from django.forms import ModelForm, DateInput
from crispy_forms.helper import FormHelper

from app.models.staffs import Staff

class StaffForm(ModelForm):
    
    class Meta:
        model = Staff
        fields = ("__all__")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.Helper = FormHelper()
        self.fields["birth_date"].widget = DateInput(attrs={
                    "type": "date"})
        self.fields["hire_date"].widget = DateInput(attrs={
                    "type": "date"})
        
