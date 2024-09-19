from django.forms import ModelForm, DateInput
from crispy_forms.helper import FormHelper
from app.models.results import *
from app.models.results import Result,Assessment,AssessmentType,GradingSystem
from django import forms
from app.models.subjects import *

class ResultForm(forms.ModelForm):
    class Meta:
        model = Result
        fields = ('score',)

class AssesmentTypeForm(ModelForm):
    
    class Meta:
        model = AssessmentType
        fields =("__all__")
        
        
        
class AssessmentForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = '__all__'
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
        }
        
class GradingSystemForm(ModelForm):
    
    class Meta:
        model = GradingSystem
        fields =("__all__")