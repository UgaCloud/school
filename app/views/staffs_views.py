from django.shortcuts import render, redirect, HttpResponseRedirect, HttpResponse,get_object_or_404
from django.contrib import messages
from django.urls import reverse
import csv
from django.db import IntegrityError
from app.selectors.model_selectors import *
from app.constants import *
from app.forms.staff import *
from app.models.staffs import Staff
import app.selectors.staffs as staff_selectors
import app.forms.staff as staff_forms
from django.contrib.auth.decorators import login_required

@login_required
def manage_staff_view(request):
    
    staffs = staff_selectors.get_all_staffs()
    staff_form = staff_forms.StaffForm()
    
    context = {
        "staffs":staffs,
        "staff_form": staff_form
    }
    return render(request, "staff/manage_staff.html", context)

@login_required
def add_staff(request):
    if request.method == "POST":
        staff_form = staff_forms.StaffForm(request.POST, request.FILES)
        
        if staff_form.is_valid():
            staff_form.save()
            
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
    
    return HttpResponseRedirect(reverse(manage_staff_view))

@login_required
def staff_details_view(request, id):
    staff = staff_selectors.get_staff(id)
    
    
    context = {
        "staff": staff,
        
    }
    
    return render(request, "staff/staff_details.html", context)


def edit_staff_details_view(request,id):

    staff_details = get_model_record(Staff,id)
    
    if request.method == "POST":
        staff_detail_form = StaffForm(request.POST, instance=staff_details)
        
        if staff_detail_form.is_valid():
            staff_detail_form.save()
            messages.success(request, SUCCESS_ADD_MESSAGE)
            
            return redirect(staff_details_view , id=id)
        else:
            messages.error(request, FAILURE_MESSAGE)
    
    else:
        staff_detail_form = StaffForm(instance=staff_details)
    
    context = {
        "form": staff_detail_form,
        "staff_details": staff_details,
    }
    
    return render(request, "staff/edit_staff_details.html", context)


def delete_staff_view(request, id):
    staff = staff_selectors.get_staff(id)
    
    staff.delete()
    
    messages.success(request, DELETE_MESSAGE)

    return HttpResponseRedirect(reverse(manage_staff_view))