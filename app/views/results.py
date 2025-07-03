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
from django.db.models import Avg, Sum, F,Q,Count
from app.utils.utils import calculate_grade_and_points
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404
from io import BytesIO
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
import tempfile
from decimal import Decimal, InvalidOperation




@login_required
def add_results_view(request, assessment_id=None):
    if not assessment_id:
        return redirect('class_assessment_list')

    assessment = get_object_or_404(Assessment, id=assessment_id)
    academic_class = assessment.academic_class

    class_registers = ClassRegister.objects.filter(academic_class_stream__academic_class=academic_class)
    students = [register.student for register in class_registers]

    existing_results = Result.objects.filter(assessment=assessment)
    existing_students = {result.student_id for result in existing_results}
    students_without_results = [student for student in students if student.id not in existing_students]

    current_mode = ResultModeSetting.get_mode()

    if request.method == "POST":
        if "edit_result" in request.POST:
            result_id = request.POST.get("edit_result")
            result = get_object_or_404(Result, id=result_id, assessment=assessment)
            score = request.POST.get(f'score_{result.student.id}')
            try:
                result.score = Decimal(score)
                result.save()
                messages.success(request, f"Result for {result.student} updated successfully!")
            except (ValueError, TypeError, InvalidOperation):
                messages.error(request, f"Invalid score entered for {result.student}.")
            return redirect('add_results', assessment_id=assessment.id)

        elif "add_results" in request.POST:
            with transaction.atomic():
                bulk_results = []
                for student in students_without_results:
                    score = request.POST.get(f'score_{student.id}')
                    if score:
                        try:
                            score = Decimal(score)
                            bulk_results.append(Result(
                                assessment=assessment,
                                student=student,
                                score=score
                            ))
                        except (ValueError, TypeError, InvalidOperation):
                            messages.error(request, f"Invalid score for {student}.")
                            return redirect('add_results', assessment_id=assessment.id)

                Result.objects.bulk_create(bulk_results)
                messages.success(request, "New results added successfully!")
            return redirect('add_results', assessment_id=assessment.id)

    context = {
        'assessment': assessment,
        'students_without_results': students_without_results,
        'existing_results': existing_results,
        'current_mode': current_mode,
    }
    return render(request, 'results/add_results_page.html', context)


@login_required
def edit_results_view(request, assessment_id=None, student_id=None):
    if not assessment_id:
        return redirect('class_assessment_list')

    assessment = get_object_or_404(Assessment, id=assessment_id)
    academic_class = assessment.academic_class
    class_registers = ClassRegister.objects.filter(academic_class_stream__academic_class=academic_class)
    all_students = [register.student for register in class_registers]

    if student_id:
        student = get_object_or_404(Student, id=student_id)
        results = Result.objects.filter(assessment=assessment, student=student)
        form_students = [student]
    else:
        results = Result.objects.filter(assessment=assessment)
        form_students = all_students

    ResultFormSet = modelformset_factory(Result, form=ResultForm, extra=0)

    if request.method == "POST":
        formset = ResultFormSet(request.POST, queryset=results)
        if formset.is_valid():
            with transaction.atomic():
                for form in formset:
                    form.instance.assessment = assessment
                    if student_id:
                        form.instance.student = student
                formset.save()
                messages.success(request, "Results updated successfully!")
                return redirect('add_results', assessment_id=assessment_id)
        else:
            messages.error(request, "There was a problem with your input. Please check the form.")
    else:
        formset = ResultFormSet(queryset=results)

    zipped_forms = zip(formset.forms, form_students)
    current_mode = ResultModeSetting.get_mode()

    context = {
        'assessment': assessment,
        'formset': formset,
        'zipped_forms': zipped_forms,
        'current_mode': current_mode,
    }
    return render(request, 'results/edit_results_page.html', context)








@login_required
def class_assessment_list_view(request):
    if request.user.is_superuser:
        # Admin sees all classes
        classes = Class.objects.all()
    else:
        try:
            # Get the staff account for the logged-in user
            staff_account = StaffAccount.objects.get(user=request.user)

            # Get the AcademicClassStream objects allocated to the teacher
            teacher_allocations = ClassSubjectAllocation.objects.filter(subject_teacher=staff_account.staff)
            allocated_streams = AcademicClassStream.objects.filter(
                id__in=teacher_allocations.values_list('academic_class_stream', flat=True)
            )

            # Get the academic classes from these streams
            allocated_classes = AcademicClass.objects.filter(
                id__in=allocated_streams.values_list('academic_class', flat=True)
            )
            classes = Class.objects.filter(
                id__in=allocated_classes.values_list('Class', flat=True)
            ).distinct()
        except StaffAccount.DoesNotExist:
            classes = Class.objects.none()

    return render(request, 'results/class_assessments.html', {'classes': classes})



#List of Assessments basing on specific academic_class
@login_required
def list_assessments_view(request, class_id):
    academic_class = get_object_or_404(AcademicClass, id=class_id)
    # Get the staff account for the logged-in user
    staff_account = StaffAccount.objects.filter(user=request.user).first()
    if request.user.is_superuser:
        assessments = Assessment.objects.filter(academic_class=academic_class)
    else:
        if staff_account:
            # Get the class subject allocations for the logged-in teacher for the specific class
            teacher_allocations = ClassSubjectAllocation.objects.filter(
                subject_teacher=staff_account.staff,
                academic_class_stream__academic_class=academic_class
            )

            # If the teacher is assigned to any subject in this class, fetch the corresponding assessments
            if teacher_allocations.exists():
                subject_ids = teacher_allocations.values_list('subject', flat=True)
                assessments = Assessment.objects.filter(
                    academic_class=academic_class,
                    subject__in=subject_ids
                )
            else:
                assessments = []
        else:
            assessments = []

    return render(request, 'results/list_assessments.html', {
        'assessments': assessments, 
        'academic_class': academic_class
    })




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







@login_required
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

@login_required
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





def get_grade_and_points(score):
    grading = GradingSystem.objects.filter(min_score__lte=score, max_score__gte=score).first()
    if grading:
        return grading.grade, grading.points
    return "N/A", Decimal('0.00')

def get_current_mode():
    setting = ResultModeSetting.objects.first()
    return setting.mode if setting else "CUMULATIVE"

def get_student_results(class_id=None, student_id=None, academic_year_id=None, term_id=None):
    results = Result.objects.select_related(
        'assessment', 'student', 'assessment__assessment_type',
        'assessment__subject', 'assessment__academic_class',
        'assessment__academic_class__term'
    )

    if class_id:
        results = results.filter(student__current_class__academic_class__id=class_id)

    if student_id:
        results = results.filter(student_id=student_id)

    if academic_year_id:
        results = results.filter(assessment__academic_class__academic_year_id=academic_year_id)

    if term_id:
        results = results.filter(assessment__academic_class__term_id=term_id)

    assessment_types = list(AssessmentType.objects.values_list('name', flat=True))

    student_results = {}

    for result in results:
        student_name = result.student.student_name
        student_id = result.student.id
        subject_name = result.assessment.subject.name
        assessment_type = result.assessment.assessment_type.name.strip()

        if student_name not in student_results:
            student_results[student_name] = {'student_id': student_id}

        if subject_name not in student_results[student_name]:
            student_results[student_name][subject_name] = {
                atype: 0 for atype in assessment_types
            } | {
                'final_score': 0,
                'grade': None,
                'points': 0
            }

        if assessment_type in assessment_types:
            # Use .actual_score which dynamically respects the mode
            student_results[student_name][subject_name][assessment_type] = result.actual_score

    # Final calculations
    for student_name, subjects in student_results.items():
        total_final_score = 0
        total_points = 0

        for subject_name, data in subjects.items():
            if subject_name != 'student_id':
                final_score = sum(data[atype] for atype in assessment_types)
                final_score = min(final_score, 100)  # Cap at 100
                data['final_score'] = int(round(final_score))

                grade, points = get_grade_and_points(data['final_score'])
                data['grade'] = grade
                data['points'] = points

                total_final_score += data['final_score']
                total_points += points

        student_results[student_name]['total_final_score'] = total_final_score
        student_results[student_name]['total_points'] = total_points

    return student_results


@login_required
def result_list(request):
    class_id = request.GET.get('class_id')
    academic_year_id = request.GET.get('academic_year_id')
    term_id = request.GET.get('term_id')

    classes = AcademicClass.objects.all()
    academic_years = AcademicYear.objects.all()
    terms = Term.objects.all()

    student_results = get_student_results(
        class_id=class_id,
        academic_year_id=academic_year_id,
        term_id=term_id
    )
    mode = get_current_mode()

    return render(request, 'results/results_list.html', {
        'student_results': student_results,
        'classes': classes,
        'academic_years': academic_years,
        'terms': terms,
        'selected_class_id': class_id,
        'selected_academic_year_id': academic_year_id,
        'selected_term_id': term_id,
        'mode': mode,
    })


@login_required
def student_report_by_type(request, student_id, assessment_type_id):
    student = get_object_or_404(Student, id=student_id)
    assessment_type = get_object_or_404(AssessmentType, id=assessment_type_id)

    
    current_term = Term.objects.filter(is_current=True).first()

    results = Result.objects.filter(
        student=student,
        assessment__assessment_type=assessment_type
    ).select_related('assessment__subject')

    report_data = {}
    total_score = 0
    total_points = 0

    for result in results:
        subject = result.assessment.subject.name
        score = result.actual_score or 0

        if subject not in report_data:
            report_data[subject] = {'score': score}
        else:
            report_data[subject]['score'] += score

        grade, points = get_grade_and_points(score)
        report_data[subject]['grade'] = grade
        report_data[subject]['points'] = points

        total_score += score
        total_points += points

    school_settings = SchoolSetting.objects.first()
    signatures = Signature.objects.filter(position__in=["HEAD TEACHER", "DIRECTOR OF STUDIES"])

    return render(request, 'results/student_assessment_report.html', {
        'student': student,
        'assessment_type': assessment_type,
        'report_data': report_data,
        'total_score': total_score,
        'total_points': total_points,
        'current_term': current_term,
        'school_setting': school_settings,
        'signatures': signatures,
    })
























@login_required
def student_report_card(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    results = Result.objects.filter(student=student)

    current_term = Term.objects.filter(is_current=True).select_related('academic_year').first()
    assessment_type_names = list(AssessmentType.objects.values_list('name', flat=True))
    mode = get_current_mode()

    report_data = {}
    total_final_score = 0
    total_points = 0

    for result in results:
        assessment = result.assessment
        assessment_type = assessment.assessment_type.name
        subject_name = assessment.subject.name

        if subject_name not in report_data:
            report_data[subject_name] = {
                **{atype: 0 for atype in assessment_type_names},
                'final_score': 0, 'grade': None, 'points': 0
            }

        if assessment_type in assessment_type_names:
            report_data[subject_name][assessment_type] = result.actual_score

    for subject_name, data in report_data.items():
        final_score = sum(data[atype] for atype in assessment_type_names)
        final_score = min(final_score, 100)
        grade, points = get_grade_and_points(final_score)

        data['final_score'] = int(round(final_score))
        data['grade'] = grade
        data['points'] = points

        total_final_score += data['final_score']
        total_points += points

    school_settings = SchoolSetting.objects.first()
    signatures = Signature.objects.filter(position__in=["HEAD TEACHER", "DIRECTOR OF STUDIES"])

    return render(request, 'results/student_report_card.html', {
        'student': student,
        'report_data': report_data,
        'total_final_score': total_final_score,
        'total_points': total_points,
        'assessment_types': assessment_type_names,
        'current_term': current_term,
        'school_setting': school_settings,
        'signatures': signatures,
        'mode': mode,
    })

@login_required
def generate_termly_report_pdf(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    results = Result.objects.filter(student=student)

    current_term = Term.objects.filter(is_current=True).select_related('academic_year').first()

    assessment_type_names = list(AssessmentType.objects.values_list('name', flat=True))

    report_data = {}
    total_final_score = 0
    total_points = 0

    for result in results:
        assessment = result.assessment
        assessment_type = assessment.assessment_type.name
        subject_name = assessment.subject.name

        if subject_name not in report_data:
            report_data[subject_name] = {
                **{atype: 0 for atype in assessment_type_names},
                'final_score': 0,
                'grade': None,
                'points': 0
            }

        if assessment_type in assessment_type_names:
            report_data[subject_name][assessment_type] = result.actual_score

    for subject_name, data in report_data.items():
        final_score = sum(data[atype] for atype in assessment_type_names)
        final_score = min(final_score, 100)
        grade, points = get_grade_and_points(final_score)

        data['final_score'] = int(round(final_score))
        data['grade'] = grade
        data['points'] = points

        total_final_score += data['final_score']
        total_points += data['points']

    html_string = render_to_string('results/student_report_card.html', {
        'student': student,
        'report_data': report_data,
        'total_final_score': total_final_score,
        'total_points': total_points,
        'current_term': current_term,
    })

    # Generate PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{student.student_name}_Termly_Report.pdf"'

    pdf_output = BytesIO()
    pisa_status = pisa.CreatePDF(html_string, dest=pdf_output)

    if pisa_status.err:
        return HttpResponse('We had some errors while generating your PDF', status=400)

    pdf_output.seek(0)
    response.write(pdf_output.read())
    return response
