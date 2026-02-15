from django.shortcuts import render, redirect, HttpResponseRedirect, HttpResponse
from django.contrib import messages
from django.urls import reverse
import csv
from django.db import IntegrityError
from app.selectors.model_selectors import *
from app.constants import *
from app.forms.subjects import SubjectForm
from app.models.subjects import Subject
import app.forms.subjects as subject_forms

import app.selectors.subjects as subject_selectors
from django.contrib.auth.decorators import login_required

@login_required
def manage_subjects_view(request):
    staff_account = getattr(request.user, "staff_account", None)
    role_name = staff_account.role.name if staff_account and staff_account.role else None
    active_role = request.session.get("active_role_name")
    is_dos = role_name in {"Director of Studies", "DOS"} or active_role in {"Director of Studies", "DOS"}

    subject_form = subject_forms.SubjectForm()
    all_subjects = subject_selectors.get_all_subjects()
    
    context = {
        "subject_form": subject_form,
        "subjects": all_subjects,
        "is_dos": is_dos,
    }
    return render(request, "subjects/manage_subjects.html", context)

@login_required
def add_subject_view(request):
    staff_account = getattr(request.user, "staff_account", None)
    role_name = staff_account.role.name if staff_account and staff_account.role else None
    active_role = request.session.get("active_role_name")
    is_dos = role_name in {"Director of Studies", "DOS"} or active_role in {"Director of Studies", "DOS"}

    if not is_dos:
        messages.error(request, "Only the Director of Studies can add subjects.")
        return HttpResponseRedirect(reverse(manage_subjects_view))

    subject_form = subject_forms.SubjectForm(request.POST)
    
    if subject_form.is_valid():
        subject_form.save()
        
        messages.success(request, SUCCESS_ADD_MESSAGE)
    else:
        messages.error(request, FAILURE_MESSAGE)
    
    return HttpResponseRedirect(reverse(manage_subjects_view))

@login_required
def edit_subject_view(request,id):
    staff_account = getattr(request.user, "staff_account", None)
    role_name = staff_account.role.name if staff_account and staff_account.role else None
    active_role = request.session.get("active_role_name")
    is_dos = role_name in {"Director of Studies", "DOS"} or active_role in {"Director of Studies", "DOS"}

    if not is_dos:
        messages.error(request, "Only the Director of Studies can edit subjects.")
        return redirect(manage_subjects_view)

    subject = get_model_record(Subject,id)
    
    if request.method == 'POST':
        subject_form = SubjectForm(request.POST, instance=subject)
        if subject_form.is_valid():
            subject_form.save()
            
            messages.success(request, SUCCESS_ADD_MESSAGE)    
        else:
            messages.error(request, FAILURE_MESSAGE)
        return redirect(add_subject_view)
    else:
        subject_form = SubjectForm(instance=subject)
    
    context = {
        "form": subject_form,
        "subject": subject
    }
    
    return render(request, "subjects/edit_subject.html", context)

def delete_subject_view(request, id):
    staff_account = getattr(request.user, "staff_account", None)
    role_name = staff_account.role.name if staff_account and staff_account.role else None
    active_role = request.session.get("active_role_name")
    is_dos = role_name in {"Director of Studies", "DOS"} or active_role in {"Director of Studies", "DOS"}

    if not is_dos:
        messages.error(request, "Only the Director of Studies can delete subjects.")
        return HttpResponseRedirect(reverse(manage_subjects_view))

    subject = subject_selectors.get_subject(id)
    
    subject.delete()
    
    messages.success(request, DELETE_MESSAGE)

    return HttpResponseRedirect(reverse(manage_subjects_view))
    
