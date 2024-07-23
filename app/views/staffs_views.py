from django.shortcuts import render, redirect, HttpResponseRedirect, HttpResponse
from django.contrib import messages
from django.urls import reverse
import csv
from django.db import IntegrityError

from app.constants import *
from app.forms import *
import app.selectors.staffs as staff_selectors
import app.forms.staff as staff_forms

def manage_staff_view(request):
    
    staffs = staff_selectors.get_all_staffs()
    staff_form = staff_forms.StaffForm()
    
    context = {
        "staffs":staffs,
        "staff_form": staff_form
    }
    return render(request, "staff/manage_staff.html", context)

def add_staff(request):
    if request.method == "POST":
        staff_form = staff_forms.StaffForm(request.POST, request.FILES)
        
        if staff_form.is_valid():
            staff_form.save()
            
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
    
    return HttpResponseRedirect(reverse(manage_staff_view))

def staff_deitals_view(request, id):
    staff = staff_selectors.get_staff(id)
    
    
    context = {
        "staff": staff,
        
    }
    
    return render(request, "staff/staff_details.html", context)
