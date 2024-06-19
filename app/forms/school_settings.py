from django.forms import ModelForm

from app.models.school_settings import *

class SchoolSettingForm(ModelForm):
    class Meta:
        model = SchoolSetting
        fields = ("country","city", "address", "postal","website", "school_name", "mobile",
                  "office_phone_number1", "office_phone_number2", "school_logo", "app_name")
        
class SectionForm(ModelForm):
    
    class Meta:
        model = Section
        fields = ("__all__")

class SignatureForm(ModelForm):
    
    class Meta:
        model = Signature
        fields = ("__all__")
