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


def manage_subjects_view(request):
    subject_form = subject_forms.SubjectForm()
    all_subjects = subject_selectors.get_all_subjects()
    
    context = {
        "subject_form": subject_form,
        "subjects": all_subjects
    }
    return render(request, "subjects/manage_subjects.html", context)

@login_required
def add_subject_view(request):
    subject_form = subject_forms.SubjectForm(request.POST)
    
    if subject_form.is_valid():
        subject_form.save()
        
        messages.success(request, SUCCESS_ADD_MESSAGE)
    else:
        messages.error(request, FAILURE_MESSAGE)
    
    return HttpResponseRedirect(reverse(manage_subjects_view))


def edit_subject_view(request,id):
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
    subject = subject_selectors.get_subject(id)
    
    subject.delete()
    
    messages.success(request, DELETE_MESSAGE)

    return HttpResponseRedirect(reverse(manage_subjects_view))
    