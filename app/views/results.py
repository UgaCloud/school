from django.shortcuts import render, redirect, HttpResponseRedirect,get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.forms import modelformset_factory
from app.constants import *
from app.models.results import AssessmentType,AnnualResult,Assessment,GradingSystem,Result
from app.forms.results import AssesmentTypeForm,GradingSystemForm,ResultForm,AssessmentForm
from app.selectors.model_selectors import *
from app.models import *
from app.selectors.model_selectors import *
from django.db import transaction
from django.contrib.auth.decorators import login_required






# Add Results View
@login_required
def add_results_view(request, assessment_id=None):
    if assessment_id is None:
        return redirect('class_assessment_list')
    assessment = Assessment.objects.get(id=assessment_id)
    academic_class = assessment.academic_class
    class_registers = ClassRegister.objects.filter(academic_class_stream__academic_class=academic_class)
    students = [class_register.student for class_register in class_registers]
    ResultFormSet = modelformset_factory(Result, form=ResultForm, extra=len(students))

    if request.method == "POST":
       with transaction.atomic():
        formset = ResultFormSet(request.POST)
        if formset.is_valid():
            for i, form in enumerate(formset):
                form.instance.assessment = assessment
                form.instance.student_id = students[i].id
            formset.save()
            messages.success(request, SUCCESS_BULK_ADD_MESSAGE)
            return redirect('list_assessments', class_id=academic_class.id)  
        else:
            messages.error(request, FAILURE_MESSAGE)
    else:
        formset = ResultFormSet(queryset=Result.objects.filter(assessment=assessment))

    zipped_forms = list(zip(formset.forms, students))

    context = {
        'assessment': assessment,
        'formset': formset,
        'zipped_forms': zipped_forms,
    }
    return render(request, 'results/add_results_page.html', context)

#Edit Results view
@login_required
def edit_results_view(request, assessment_id=None, student_id=None):
    if assessment_id is None:
        return redirect(list_assessments_view)
    assessment = Assessment.objects.get(id=assessment_id)
    academic_class = assessment.academic_class
    class_registers = ClassRegister.objects.filter(academic_class_stream__academic_class=academic_class)
    students = [class_register.student for class_register in class_registers]

    if student_id is not None:
        student = get_object_or_404(Student, id=student_id)
        results = Result.objects.filter(assessment=assessment, student=student)
    else:
        results = Result.objects.filter(assessment=assessment)

    ResultFormSet = modelformset_factory(Result, form=ResultForm, extra=0)

    if request.method == "POST":
        with transaction.atomic():
            formset = ResultFormSet(request.POST)
            if formset.is_valid():
                for form in formset:
                    form.instance.assessment = assessment
                    if student_id is not None:
                        form.instance.student = student
                formset.save()
                messages.success(request, SUCCESS_EDIT_MESSAGE)
                return redirect('add_results', assessment_id=assessment_id) 
            else:
                messages.error(request, FAILURE_MESSAGE)
    else:
        formset = ResultFormSet(queryset=results)

    if student_id is not None:
        zipped_forms = list(zip(formset.forms, [student]))
    else:
        zipped_forms = list(zip(formset.forms, students))

    context = {
        'assessment': assessment,
        'formset': formset,
        'zipped_forms': zipped_forms,
    }
    return render(request, 'results/edit_results_page.html', context)

@login_required
def class_assessment_list_view(request):
    classes =Class.objects.all()
    return render(request,'results/class_assessments.html',{'classes':classes})

#List of Assessments basing on specific academic_class
@login_required
def list_assessments_view(request, class_id):
    academic_class = AcademicClass.objects.get(id=class_id)
    print(academic_class)
    assessments = Assessment.objects.filter(academic_class=academic_class)
    return render(request, 'results/list_assessments.html', {'assessments': assessments, 'class_id': class_id})

#Grading System
@login_required
def grading_system_view(request):
    if request.method == "POST":
        grading_form = GradingSystemForm(request.POST)
        if grading_form.is_valid():
            grading_form.save()
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)

    
    grading_form = GradingSystemForm()

    grading_systems = GradingSystem.objects.all()  

    context = {
        'grading_form': grading_form,  
        'grading_systems': grading_systems,  
    }

    return render(request, 'results/grading_system.html', context)


#Edit grading system
@login_required
def edit_grading_system_view(request, id):
    grading_system = get_model_record(GradingSystem,id)

    if request.method == "POST":
        grading_form = GradingSystemForm(request.POST, instance=grading_system)
        
        if grading_form.is_valid():
            grading_form.save()
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
        return redirect(grading_system_view)

    else:
        grading_form = GradingSystemForm(instance=grading_system)
    
    context = {
        "grading_form": grading_form,
        "grading_system": grading_system
    }
    
    return render(request, 'results/edit_grading_system.html', context)

@login_required
def delete_grading_system_view(request, id):
    grading_system = GradingSystem.objects.get(pk=id)
    
    grading_system.delete()
    messages.success(request, DELETE_MESSAGE)
    return redirect(grading_system_view)

@login_required
def assessment_list_view(request):
    assessments = Assessment.objects.all()
    context = {
        'assessments': assessments,
    }
    return render(request, 'results/assessment_list.html', context)

@login_required
def add_assessment_view(request):
    if request.method == "POST":
        form = AssessmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,SUCCESS_ADD_MESSAGE)
            
              
    
    form = AssessmentForm()
    assessment = Assessment.objects.all()
    
    context = {
        'form': form,
        'assessments':assessment,
    }
    return render(request,'results/add_assessment.html',context)

@login_required
def edit_assessment(request, id):
    assessment = get_model_record(Assessment,id)
    if request.method == "POST":
        form = AssessmentForm(request.POST, instance=assessment)
        if form.is_valid():
            form.save()
            messages.success(request,SUCCESS_ADD_MESSAGE)
            return redirect(add_assessment_view)
            
        else:
            messages.error(request,FAILURE_MESSAGE)
        
    else:
        form = AssessmentForm(instance=assessment)
    
    context = {
        'form': form,
        'assessment':assessment
    }
    return render(request, 'results/edit_assessment.html', context)

@login_required
def delete_assessment_view(request,id):
    assessment = get_model_record(Assessment,id)
    assessment.delete()
    messages.success(request, DELETE_MESSAGE)
    return HttpResponseRedirect(reverse(add_assessment_view))

















def assesment_type_view(request):
    if request.method == "POST":
        assesment_type_form = AssesmentTypeForm(request.POST)
        
        if assesment_type_form.is_valid():
            assesment_type_form.save()
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
         
            messages.error(request,FAILURE_MESSAGE)
    
    assesment_type_form = AssesmentTypeForm()
    
    assesment_type = AssessmentType.objects.all()
    
    context = {
        "form": assesment_type_form,
        "assesment_type": assesment_type
    }
    
    return render(request, "results/assesment_type.html", context)

def edit_assesment_type(request,id):
    assesment_type = get_model_record(AssessmentType,id)
    if request.method =="POST":
       assesment_type_form = AssesmentTypeForm(request.POST,instance=assesment_type)
       if assesment_type_form.is_valid():
           assesment_type_form.save().save()
           messages.success(request,SUCCESS_ADD_MESSAGE)
           return redirect(assesment_type_view)
       else:
           messages.error(request,FAILURE_MESSAGE)
           
    else:
        assesment_type_form = AssesmentTypeForm(instance=assesment_type)
    context={
        "form":assesment_type_form,
        "assesment_type":assesment_type
    } 
    return render(request,"results/edit_assesment_type.html",context)

def delete_assesment_view(request, id):
    assesment_type = AssessmentType.objects.get(pk=id)
    
    assesment_type.delete()
    messages.success(request, DELETE_MESSAGE)
    
    return redirect(assesment_type_view)