from django import forms
from django.utils import timezone

from app.models.attendance import AttendanceStatus
from app.models.timetables import TimeSlot


class AttendanceSessionForm(forms.Form):
    date = forms.DateField(initial=timezone.now().date())
    time_slot = forms.ModelChoiceField(
        queryset=TimeSlot.objects.all(), required=False, empty_label="-- Select Time Slot --"
    )


class AttendanceMarkForm(forms.Form):
    status = forms.ChoiceField(choices=AttendanceStatus.choices)
    remarks = forms.CharField(required=False)
