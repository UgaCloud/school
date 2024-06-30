from django.shortcuts import render, redirect, HttpResponseRedirect, HttpResponse
from django.contrib import messages
from django.urls import reverse
import csv
from django.db import IntegrityError

from app.constants import *
import app.forms.subjects as subject_forms
import app.selectors.subjects as subject_selectors

def manage_subjects_view(request):
    subject_form = subject_forms.SubjectForm()
    all_subjects = subject_selectors.get_all_subjects()
    
    context = {
        "subject_form": subject_form,
        "subjects": all_subjects
    }
    return render(request, "subjects/manage_subjects.html", context)

def add_subject_view(request):
    subject_form = subject_forms.SubjectForm(request.POST)
    
    if subject_form.is_valid():
        subject_form.save()
        
        messages.success(request, SUCCESS_ADD_MESSAGE)
    else:
        messages.error(request, FAILURE_MESSAGE)
    
    return HttpResponseRedirect(reverse(manage_subjects_view))

def edit_subject_view(request, id):
    subject = subject_selectors.get_subject(id)
    
    subject_form = subject_forms.SubjectForm(request.POST, instance=subject)
    
    if subject_form.is_valid():
        subject_form.save()
        
        messages.success(request, SUCCESS_EDIT_MESSAGE)
    else:
        messages.error(request, FAILURE_MESSAGE)

def delete_subject_view(request, id):
    subject = subject_selectors.get_subject(id)
    
    subject.delete()
    
    messages.success(request, DELETE_MESSAGE)

    return HttpResponseRedirect(reverse(manage_subjects_view))
    