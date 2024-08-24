from django.shortcuts import render, redirect, HttpResponseRedirect
from django.contrib import messages

# Create your views here.
from django.urls import reverse

from app.constants import *

from app.models.school_settings import SchoolSetting, Currency, Section, AcademicYear
import app.selectors.school_settings as school_settings_selectors
import app.services.school_settings as school_settings_services
import app.forms.school_settings as school_settings_forms


def settings_page(request):
    all_currencies = school_settings_selectors.get_all_currencies()
    school_settings = SchoolSetting.load()
    school_sections = school_settings_selectors.get_sections()
    signatures = school_settings_selectors.get_signatures()
    departments = school_settings_selectors.get_all_departments()
    
    school_settings_form = school_settings_forms.SchoolSettingForm(instance=school_settings)
    sections_form = school_settings_forms.SectionForm()
    signature_form = school_settings_forms.SignatureForm()
    department_form = school_settings_forms.DepartmentForm()
    
    context = {
        "currencies": all_currencies,
        "school_settings": school_settings,
        "school_sections": school_sections,
        "school_settings_form": school_settings_form,
        "sections_form": sections_form,
        "signatures": signatures,
        "signature_form": signature_form,
        "departments": departments,
        "department_form": department_form
    }
    return render(request, 'school_settings/settings_page.html', context)

def update_school_settings(request):
    school_settings = SchoolSetting.load()
    count = SchoolSetting.objects.count()
    
    if request.method == 'POST':
        school_settings_form = school_settings_forms.SchoolSettingForm(request.POST, request.FILES, instance=school_settings)
        
        if school_settings_form.is_valid():
            school_settings_form.save()
            messages.success(request, SUCCESS_EDIT_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
    
    return HttpResponseRedirect(reverse('settings_page'))
    

def add_currency(request):
    if request.POST:
        code = request.POST.get('code')
        desc = request.POST.get('desc')
        cost = request.POST.get('cost')

        school_settings_services.create_currency(code, desc, cost)
        messages.success(request, SUCCESS_ADD_MESSAGE)

        return HttpResponseRedirect(reverse('settings_page'))
    messages.error(request, 'You sent a get request')
    return HttpResponseRedirect(reverse('settings_page'))


def edit_currency_page(request, currency_id):
    currency = school_settings_selectors.get_currency(currency_id)
    if request.POST:
        code = request.POST.get('code')
        desc = request.POST.get('desc')
        cost = request.POST.get('cost')
        school_settings_services.update_currency(currency, code, desc, cost)
        messages.success(request, SUCCESS_EDIT_MESSAGE)
        return HttpResponseRedirect(reverse('settings_page'))
    context = {
        "currency": currency
    }
    return render(request, 'settings/edit_currency.html', context)


def delete_currency(request, currency_id):
    currency = school_settings_selectors.get_currency(currency_id)
    currency.delete()
    messages.success(request, DELETE_MESSAGE)
    return HttpResponseRedirect(reverse('settings_page'))

def school_section_view(request):
    
    if request.method == "POST":
        section_form = school_settings_forms.SectionForm(request.POST)
        
        if section_form.is_valid():
            section_form.save()
            
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
    
    return HttpResponseRedirect(reverse('settings_page'))

def edit_section_view(request, id):
    section = school_settings_selectors.get_section(id)
    
    if request.method == "POST":
        section_form = school_settings_forms.SectionForm(request.POST, request.FILES, instance=section)
        
        if section_form.is_valid():
            section_form.save()
            
            messages.success(request, SUCCESS_EDIT_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
    return HttpResponseRedirect(reverse("settings_page"))

def delete_section_view(request, id):
    section = school_settings_selectors.get_section(id)
    
    section.delete()
    
    messages.success(request, DELETE_MESSAGE)
    return HttpResponseRedirect(reverse("settings_page"))
       
def add_signature_view(request):
    if request.method == "POST":
        signature_form = school_settings_forms.SignatureForm(request.POST, request.FILES)
        
        if signature_form.is_valid():
            signature_form.save()
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
    return HttpResponseRedirect(reverse("settings_page"))

def edit_signature_view(request, id):
    signature = school_settings_selectors.get_signature(id)
    
    if request.method == "POST":
        signature_form = school_settings_forms.SignatureForm(request.POST, request.FILES, instance=signature)
        
        if signature_form.is_valid():
            signature_form.save()
            
            messages.success(request, SUCCESS_EDIT_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
    return HttpResponseRedirect(reverse("settings_page"))

def delete_signature_view(request, id):
    signature = school_settings_selectors.get_signature(id)
    
    signature.delete()
    
    messages.success(request, DELETE_MESSAGE)
    
    return HttpResponseRedirect(reverse("settings_page"))

def add_department_view(request):
    
    if request.method == "POST":
        form = school_settings_forms.DepartmentForm(request.POST)
        
        if form.is_valid():
            form.save()
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
            
    return HttpResponseRedirect(reverse("settings_page"))

def edit_department_view(request):
    department = school_settings_selectors.get_department(id)
    
    if request.method == "POST":
        department_form = school_settings_forms.DepartmentForm(request.POST, request.FILES, instance=department)
        
        if department_form.is_valid():
            department_form.save()
            
            messages.success(request, SUCCESS_EDIT_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
    return HttpResponseRedirect(reverse("settings_page"))  

def delete_department_view(request, id):
    department = school_settings_selectors.get_department(id)
    
    department.delete()
    
    messages.success(request, DELETE_MESSAGE)        
