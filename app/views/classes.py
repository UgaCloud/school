from django.shortcuts import render, redirect, HttpResponseRedirect
from django.contrib import messages
from django.urls import reverse

from app.constants import *
from app.models.classes import Class, AcademicClass, Stream, AcademicClassStream
from app.forms.classes import ClassForm, AcademicClassForm, StreamForm, AcademicClassStreamForm
import app.selectors.classes as class_selectors
import app.selectors.school_settings as school_settings_selectors

def class_view(request):
    if request.method == "POST":
        class_form = ClassForm(request.POST)
        
        if class_form.is_valid():
            class_form.save()
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
    
    class_form = ClassForm()
    
    context = {
        "form": class_form,
        "classes": class_selectors.get_classes()
    }
    return render(request, "classes/_class.html", context)

def edit_classes(request):
    return render(request)

def stream_view(request):
    if request.method == "POST":
        stream_form = StreamForm(request.POST)
        
        if stream_form.is_valid():
            stream_form.save()
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
    
    stream_form = StreamForm()
    streams = Stream.objects.all()
    
    context = {
        "form": stream_form,
        "streams": streams
    }
    return render(request, "classes/stream.html", context)

def edit_streams(request):
    return render(request)

def delete_stream_view(request, id):
    stream = Stream.objects.get(pk=id)
    
    stream.delete()
    messages.success(request, DELETE_MESSAGE)
    
    return redirect(stream_view)

def academic_class_view(request):
    if request.method == "POST":
        academic_class_form = AcademicClassForm(request.POST)
        
        if academic_class_form.is_valid():
            academic_class_form.save()
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
    
    academic_class_form = AcademicClassForm()
    academic_classes = AcademicClass.objects.all()
    
    context = {
        "form": academic_class_form,
        "academic_years": school_settings_selectors.get_academic_years(),
        "academic_classes": academic_classes,
        "classes": class_selectors.get_classes()
    }
    return render(request, "classes/academic_class.html", context)

def edit_streams(request):
    return render(request)

def delete_class_view(request, id):
    stream = Stream.objects.get(pk=id)
    
    stream.delete()
    messages.success(request, DELETE_MESSAGE)
    
    return redirect(stream_view)

def academic_class_details_view(request, id):
    academic_class = AcademicClass.objects.get(pk=id)
    academic_class_streams = academic_class.class_streams.all()
    
    class_stream_form = AcademicClassStreamForm(initial={"academic_class": academic_class})
    
    
    context = {
        "academic_class": academic_class,
        "class_streams": academic_class_streams,
        "class_stream_form": class_stream_form
    }
    
    return render(request, "classes/academic_class_details.html", context)

def add_class_stream(request):
    class_stream_form = AcademicClassStreamForm(request.POST)
    
    if class_stream_form.is_valid():
        class_stream_form.save()
        
        messages.success(request, SUCCESS_ADD_MESSAGE)
    else:
        messages.error(request, FAILURE_MESSAGE)
        
    return HttpResponseRedirect(reverse(academic_class_details_view, args=[1]))