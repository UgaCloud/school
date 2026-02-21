from django.shortcuts import render, redirect, HttpResponseRedirect,get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse
from django.db.models import Q
from django.db import IntegrityError
import logging
logger = logging.getLogger(__name__)
from app.constants import *
from app.models.students  import Student
from app.models.classes import Class, AcademicClass, Stream, AcademicClassStream,ClassSubjectAllocation
from app.forms.classes import ClassForm, AcademicClassForm, StreamForm, AcademicClassStreamForm,ClassSubjectAllocationForm
from app.models.students import ClassRegister
from app.forms.fees_payment import StudentBillItemForm,ClassBillForm
from app.selectors.model_selectors import *
import app.selectors.classes as class_selectors
import app.selectors.school_settings as school_settings_selectors
import app.selectors.fees_selectors as fees_selectors
from app.services.students import create_class_bill_item
from django.contrib.auth.decorators import login_required
from app.decorators.decorators import *
from app.models.accounts import *
from app.models.fees_payment import *
from app.models.school_settings import *
from app.models.classes import *
from itertools import groupby
from operator import attrgetter

@login_required
def class_view(request):
    active_role = request.session.get("active_role_name")
    staff_account = StaffAccount.objects.filter(user=request.user).select_related("staff", "role").first()
    role_name = staff_account.role.name if staff_account and staff_account.role else None
    is_class_teacher = (active_role == "Class Teacher" or role_name == "Class Teacher")

    if is_class_teacher:
        class_form = ClassForm()
        classes_qs = Class.objects.none()
        if staff_account and staff_account.staff:
            assigned_class_ids = AcademicClassStream.objects.filter(
                class_teacher=staff_account.staff
            ).values_list("academic_class__Class_id", flat=True).distinct()
            classes_qs = Class.objects.filter(id__in=assigned_class_ids).order_by("name")
        context = {
            "form": class_form,
            "classes": classes_qs,
        }
        return render(request, "classes/_class.html", context)

    if request.method == "POST":
        class_form = ClassForm(request.POST)
        
        if class_form.is_valid():
            class_form.save()
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
    
    class_form = ClassForm()
    classe = Class.objects.all()
    
    context = {
        "form": class_form,
        "classes": class_selectors.get_classes()
    }
    return render(request, "classes/_class.html", context)

@login_required
def edit_classe_view(request, id):
    classe = get_model_record(Class,id)
    
    if request.method == "POST":
        class_form = ClassForm(request.POST, instance= classe)
        
        if class_form.is_valid():
            class_form.save()
            messages.success(request, SUCCESS_ADD_MESSAGE)
            return redirect(class_view)  
        else:
            messages.error(request, FAILURE_MESSAGE)
    
    else:
        class_form = ClassForm(instance=classe)
    
    context = {
        "form":class_form,
        "classe":classe
    }
    
    return render(request, "classes/edit_class.html", context)


def delete_class_view(request, id):
    classe = Class.objects.get(pk=id)
    
    classe.delete()
    messages.success(request, DELETE_MESSAGE)
    
    return redirect(class_view)

@login_required
def stream_view(request):
    staff_account = getattr(request.user, "staff_account", None)
    role_name = staff_account.role.name if staff_account and staff_account.role else None
    active_role = request.session.get("active_role_name")
    is_dos = role_name in {"Director of Studies", "DOS"} or active_role in {"Director of Studies", "DOS"}
    is_admin = role_name in {"Admin", "Head master"} or active_role in {"Admin", "Head master"}

    if request.method == "POST" and not is_dos:
        messages.error(request, "Only the Director of Studies can add streams.")
        return redirect(stream_view)

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
        "streams": streams,
        "is_dos": is_dos,
    }
    return render(request, "classes/stream.html", context)


@login_required
def edit_stream(request,id):
    stream = get_model_record(Stream,id)
    if request.method =="POST":
        stream_form =StreamForm(request.POST,instance=stream)
        
        if stream_form.is_valid():
            stream_form.save()

            messages.success(request, SUCCESS_ADD_MESSAGE)
            return redirect(stream_view)
        else:
            messages.error(request, FAILURE_MESSAGE)
    
            
    stream_form =StreamForm(instance=stream)
    
    context ={
        "form":stream_form,
        "stream":stream
    }
    
    return render(request, "classes/edit_stream.html",context)

def delete_stream_view(request, id):
    try:
        stream = Stream.objects.get(pk=id)
        
        stream.delete()
        messages.success(request, DELETE_MESSAGE)
        
        return redirect(stream_view)
    except:
        logger.critical("Failed Delete record")


@login_required
def academic_class_view(request):
    if request.method == "POST":
        academic_class_form = AcademicClassForm(request.POST)
        if academic_class_form.is_valid():
            academic_class_form.save()
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)

    academic_class_form = AcademicClassForm()

    staff_account = getattr(request.user, "staff_account", None)
    role_name = staff_account.role.name if staff_account and staff_account.role else None
    active_role = request.session.get("active_role_name")
    is_class_teacher = (active_role == "Class Teacher" or role_name == "Class Teacher")

    # Get base queryset based on user role
    if is_class_teacher:
        if staff_account and staff_account.staff:
            base_queryset = AcademicClass.objects.filter(
                id__in=AcademicClassStream.objects.filter(
                    class_teacher=staff_account.staff
                ).values_list("academic_class_id", flat=True)
            ).distinct()
        else:
            base_queryset = AcademicClass.objects.none()
    elif role_name == "Admin":
        base_queryset = AcademicClass.objects.all()
    elif role_name == "Teacher":
        if staff_account and staff_account.staff:
            base_queryset = AcademicClass.objects.filter(
                id__in=ClassSubjectAllocation.objects.filter(
                    subject_teacher=staff_account.staff
                ).values_list("academic_class_stream__academic_class_id", flat=True)
            ).distinct()
        else:
            base_queryset = AcademicClass.objects.none()
    else:
        base_queryset = AcademicClass.objects.none()

    academic_year_filter = request.GET.get('academic_year')
    term_filter = request.GET.get('term')
    class_filter = request.GET.get('class')
    section_filter = request.GET.get('section')

    academic_classes = base_queryset.select_related('Class', 'academic_year', 'term')

    if academic_year_filter and academic_year_filter != '':
        academic_classes = academic_classes.filter(academic_year_id=academic_year_filter)

    if term_filter and term_filter != '':
        academic_classes = academic_classes.filter(term_id=term_filter)

    if class_filter and class_filter != '':
        academic_classes = academic_classes.filter(Class_id=class_filter)

    if section_filter and section_filter != '':
        academic_classes = academic_classes.filter(section=section_filter)

    total_classes = academic_classes.count()
    distinct_terms = academic_classes.values_list('term', flat=True).distinct().count() if academic_classes.exists() else 0
    distinct_sections = academic_classes.values_list('section', flat=True).distinct().count() if academic_classes.exists() else 0
    academic_years_count = school_settings_selectors.get_academic_years().count()

    sections_list = []
    if academic_classes.exists():
        section_ids = academic_classes.values_list('section', flat=True).distinct()
        sections_list = Section.objects.filter(id__in=section_ids)

    all_academic_years = school_settings_selectors.get_academic_years()
    all_classes = class_selectors.get_classes()
    all_terms = []  

    # Get terms for the selected academic year or all terms
    if academic_year_filter and academic_year_filter != '':
        try:
            selected_year = all_academic_years.get(id=academic_year_filter)
            all_terms = selected_year.term_set.all()
        except:
            all_terms = []
    else:
        # Get all terms from all years
        all_terms = Term.objects.all()

    context = {
        "form": academic_class_form,
        "academic_years": all_academic_years,
        "academic_classes": academic_classes,
        "classes": all_classes,
        "all_terms": all_terms,
        # Statistics
        "total_classes": total_classes,
        "distinct_terms": distinct_terms,
        "distinct_sections": distinct_sections,
        "academic_years_count": academic_years_count,
        "sections_list": sections_list,
        # Current filter values
        "current_academic_year": academic_year_filter,
        "current_term": term_filter,
        "current_class": class_filter,
        "current_section": section_filter,
    }

    return render(request, "classes/academic_class.html", context)




@login_required
def edit_academic_class_view(request, class_id):
    academic_class = get_model_record(AcademicClass,class_id)

    if request.method == "POST":
        academic_class_form = AcademicClassForm(request.POST, instance=academic_class)
        
        if academic_class_form.is_valid():
            academic_class_form.save()
            messages.success(request,SUCCESS_ADD_MESSAGE)
            return redirect("academic_class_view")  
        else:
            messages.error(request,FAILURE_MESSAGE)
    else:
        academic_class_form = AcademicClassForm(instance=academic_class)

    context = {
        "form": academic_class_form,
        "academic_class": academic_class,
    }
    return render(request, "classes/edit_academic_class.html", context)



def delete_academic_class_view(request, id):
    academic_class = AcademicClass.objects.get(id=id)
    
    academic_class.delete()
    messages.success(request, DELETE_MESSAGE)
    
    return redirect(academic_class_view)

@login_required
def academic_class_details_view(request, id):
    academic_class = AcademicClass.objects.get(pk=id)
    academic_class_streams = class_selectors.get_academic_class_streams(academic_class)

    class_register = class_selectors.get_academic_class_register(academic_class)


    class_teachers = AcademicClassStream.objects.filter(academic_class=academic_class).select_related('class_teacher')

    class_stream_form = AcademicClassStreamForm(initial={"academic_class": academic_class})
    bill_item_form = StudentBillItemForm()

    # Calculate student statistics
    total_students = 0
    male_students = 0
    female_students = 0

    # Get all students in this academic class through class register
    for stream in academic_class_streams:
        stream_students = ClassRegister.objects.filter(academic_class_stream=stream).select_related('student')
        for class_reg in stream_students:
            total_students += 1
            if hasattr(class_reg.student, 'gender') and class_reg.student.gender:
                gender_value = str(class_reg.student.gender).strip()
                if gender_value.lower() in ['male', 'm']:
                    male_students += 1
                elif gender_value.lower() in ['female', 'f']:
                    female_students += 1

    # Calculate percentages
    male_percentage = (male_students / total_students * 100) if total_students > 0 else 0
    female_percentage = (female_students / total_students * 100) if total_students > 0 else 0


    context = {
        "academic_class": academic_class,
        "class_streams": academic_class_streams,
        "class_stream_form": class_stream_form,
        "class_register": class_register,
        "bill_item_form": bill_item_form,
        "class_teachers": class_teachers,
        # Student statistics
        "total_students": total_students,
        "male_students": male_students,
        "female_students": female_students,
        "male_percentage": round(male_percentage, 1),
        "female_percentage": round(female_percentage, 1),
        # Class metrics removed as requested
    }

    return render(request, "classes/academic_class_details.html", context)


@login_required
def edit_academic_class_details_view(request,id):
    academic_class = get_model_record(AcademicClass,id)
    if request.method =="POST":
        form = AcademicClassForm(request.POST,instance=academic_class)
        
        if form.is_valid():
            form.save()
            messages.success(request,SUCCESS_ADD_MESSAGE)
            return redirect(academic_class_view)
        else:
            messages.error(request, FAILURE_MESSAGE)
            
    form = AcademicClassForm(instance=academic_class)
    
    context ={
        "form": form,
        "academic_class": academic_class
        
    }
    return  render(request,"classes/edit_academic_class_details.html",context)

@login_required
def add_class_stream(request, id):
    academic_class = AcademicClass.objects.get(pk=id)
    staff_account = getattr(request.user, "staff_account", None)
    role_name = staff_account.role.name if staff_account and staff_account.role else None
    active_role = request.session.get("active_role_name")
    if role_name == "Class Teacher" or active_role == "Class Teacher":
        messages.error(request, "You are not allowed to add class streams.")
        return HttpResponseRedirect(reverse(academic_class_details_view, args=[academic_class.id]))
    form = AcademicClassStreamForm(request.POST)

    if form.is_valid():
        cs = form.save(commit=False)
        cs.academic_class = academic_class
        cs.save()
        messages.success(request, SUCCESS_ADD_MESSAGE)
    else:
        # Surface validation errors so the user knows what to fix
        messages.error(request, FAILURE_MESSAGE)
        try:
            err_txt = form.errors.as_text()
            if err_txt:
                messages.error(request, err_txt)
        except Exception:
            pass

    return HttpResponseRedirect(reverse(academic_class_details_view, args=[academic_class.id]))

@login_required
def edit_class_stream(request, id):
    class_stream = get_model_record(AcademicClassStream,id)
    
    if request.method == "POST":
        form = AcademicClassStreamForm(request.POST, instance=class_stream)
        if form.is_valid():
            form.save()
            messages.success(request, "Class Stream updated successfully!")
            return redirect(reverse("academic_class_details_page", args=[class_stream.academic_class.id]))

        else:
            messages.error(request, FAILURE_MESSAGE)
    else:
        form = AcademicClassStreamForm(instance=class_stream)
    
    return render(request, "classes/edit_class_stream.html", {"form": form, "class_stream": class_stream})


def delete_class_stream(request, id):
    class_stream = get_model_record(AcademicClassStream,id)
    academic_class_id = class_stream.academic_class.id
    class_stream.delete()
    
    messages.success(request,DELETE_MESSAGE)
    return redirect(reverse("academic_class_details_page", args=[class_stream.academic_class.id]))


@login_required
def class_bill_list_view(request):
    academic_classes = AcademicClass.objects.select_related('Class', 'academic_year', 'term', 'section')

    class_filter = request.GET.get('class')
    academic_year_filter = request.GET.get('academic_year')
    term_filter = request.GET.get('term')
    status_filter = request.GET.get('status', 'all')

    # Convert 'all' to None for proper filtering
    if class_filter == 'all':
        class_filter = None
    if academic_year_filter == 'all':
        academic_year_filter = None
    if term_filter == 'all':
        term_filter = None

    # Apply filters
    if class_filter:
        academic_classes = academic_classes.filter(Class__id=class_filter)
    if academic_year_filter:
        academic_classes = academic_classes.filter(academic_year__id=academic_year_filter)
    if term_filter:
        academic_classes = academic_classes.filter(term__id=term_filter)

    # Get filter options
    class_options = Class.objects.all()
    academic_year_options = AcademicYear.objects.all()
    term_options = Term.objects.all()

    # Calculate bill statistics for each academic class
    academic_classes_with_stats = []
    total_billed_amount = 0
    total_collected_amount = 0
    total_outstanding_amount = 0

    for academic_class in academic_classes:
        # Get all bills for this class
        class_bills = ClassBill.objects.filter(academic_class=academic_class).select_related('bill_item')

        # Get all active students
        students_in_class = Student.objects.filter(current_class=academic_class.Class, is_active=True)
        total_students = students_in_class.count()


        # Calculate total billed amount including both ClassBills and individual StudentBillItems
        total_billed = 0

        # Add ClassBill amounts (standard class-wide bills)
        class_bill_total = sum(bill.amount for bill in class_bills)
        total_billed += class_bill_total * total_students

        # Add individual StudentBillItem amounts (custom student-specific bills)
        for student in students_in_class:
            student_bill_items = StudentBillItem.objects.filter(
                bill__student=student,
                bill__academic_class=academic_class
            ).select_related('bill_item')

            for item in student_bill_items:
                # Only add if it's not already included in the ClassBill calculation
                # (to avoid double-counting standard class bills)
                if not class_bills.filter(bill_item=item.bill_item).exists():
                    total_billed += item.amount

        # Calculate collection stats
        total_class_billed = total_billed
        total_class_collected = 0
        total_class_outstanding = 0

        for student in students_in_class:
            student_bills = StudentBill.objects.filter(
                student=student,
                academic_class=academic_class
            ).select_related('student')

            for student_bill in student_bills:
                total_class_collected += student_bill.amount_paid
                total_class_outstanding += student_bill.balance

        # Calculate collection rate
        collection_rate = (total_class_collected / total_class_billed * 100) if total_class_billed > 0 else 0

        # Add statistics to academic class
        academic_class.stats = {
            'total_bills': class_bills.count(),
            'total_billed': total_billed,
            'total_students': total_students,
            'class_billed': total_class_billed,
            'class_collected': total_class_collected,
            'class_outstanding': total_class_outstanding,
            'collection_rate': round(collection_rate, 1),
            'bills': class_bills
        }

        academic_classes_with_stats.append(academic_class)

        # Accumulate totals
        total_billed_amount += total_class_billed
        total_collected_amount += total_class_collected
        total_outstanding_amount += total_class_outstanding

    # Calculate overall collection rate
    overall_collection_rate = (total_collected_amount / total_billed_amount * 100) if total_billed_amount > 0 else 0

    # Calculate total students from all classes
    total_students = sum(academic_class.stats['total_students'] for academic_class in academic_classes_with_stats)

    # Debug total calculation
    context = {
        "academic_classes": academic_classes_with_stats,
        "class_options": class_options,
        "academic_year_options": academic_year_options,
        "term_options": term_options,
        "class_filter": class_filter if class_filter else 'all',
        "academic_year_filter": academic_year_filter if academic_year_filter else 'all',
        "term_filter": term_filter if term_filter else 'all',
        "status_filter": status_filter,
        # Summary statistics
        "total_classes": len(academic_classes_with_stats),
        "total_students": total_students,
        "total_billed_amount": total_billed_amount,
        "total_collected_amount": total_collected_amount,
        "total_outstanding_amount": total_outstanding_amount,
        "overall_collection_rate": round(overall_collection_rate, 1),
        # Current filters for URL building
        "current_filters": {
            'class': class_filter,
            'academic_year': academic_year_filter,
            'term': term_filter,
            'status': status_filter
        }
    }

    return render(request, "fees/class_bill_list.html", context)



@login_required
def add_class_bill_item_view(request, id):
    academic_class = class_selectors.get_academic_class(id)
    class_bills = ClassBill.objects.filter(academic_class=academic_class)

    if request.method == "POST":
        form = ClassBillForm(request.POST)
        if form.is_valid():
            
            class_bill = form.save(commit=False)
            class_bill.academic_class = academic_class 
            class_bill.save()
            
            students_in_class = Student.objects.filter(current_class=academic_class.Class, is_active=True)
            
            for student in students_in_class:
                # Checking  if there's already an existing StudentBill for the student $ academic class
                student_bill, created = StudentBill.objects.get_or_create(
                    student=student,
                    academic_class=academic_class,
                    status="Unpaid",  
                )
                                                
                if class_bill.bill_item.item_name != "School Fees":
                    StudentBillItem.objects.create(
                        bill=student_bill,
                        bill_item=class_bill.bill_item,
                        description=class_bill.bill_item.description,  
                        amount=class_bill.amount  
                    )                                
                student_bill.save()

            messages.success(request, SUCCESS_ADD_MESSAGE)
            return redirect("class_bill_list")  
        else:
            messages.error(request, FAILURE_MESSAGE)
    else:
        
        form = ClassBillForm()

    context = {
        "academic_class": academic_class,
        "bill_item_form": form,
        "class_bills": class_bills,
        "academic_year": academic_class.academic_year,
        "term": academic_class.term,
    }
    return render(request, "fees/class_bill_items.html", context)



@login_required
def edit_class_bill_item_view(request, id):
    class_bill = get_object_or_404(ClassBill, id=id)
    academic_class = class_bill.academic_class  # Retrieve related AcademicClass

    if request.method == "POST":
        form = ClassBillForm(request.POST, instance=class_bill)
        if form.is_valid():
            updated_class_bill = form.save()  

            # Update the StudentBillItems for all active students in the academic class
            students_in_class = Student.objects.filter(current_class=academic_class.Class, is_active=True)

            for student in students_in_class:
                student_bill, created = StudentBill.objects.get_or_create(
                    student=student,
                    academic_class=academic_class,
                    status="Unpaid",
                )

                
                if updated_class_bill.bill_item.item_name != "School Fees":
                    # Ensure a single StudentBillItem per (bill, bill_item); clean up duplicates if any
                    qs = StudentBillItem.objects.filter(
                        bill=student_bill,
                        bill_item=updated_class_bill.bill_item
                    ).order_by('id')
                    if qs.exists():
                        student_bill_item = qs.first()
                        # Remove duplicates if present
                        if qs.count() > 1:
                            qs.exclude(pk=student_bill_item.pk).delete()
                        # Update fields to reflect the current class bill configuration
                        student_bill_item.description = updated_class_bill.bill_item.description
                        student_bill_item.amount = updated_class_bill.amount
                        student_bill_item.save()
                    else:
                        StudentBillItem.objects.create(
                            bill=student_bill,
                            bill_item=updated_class_bill.bill_item,
                            description=updated_class_bill.bill_item.description,
                            amount=updated_class_bill.amount
                        )

                student_bill.save()

            messages.success(request, SUCCESS_EDIT_MESSAGE)
            return redirect("class_bill_list")  
        else:
            messages.error(request, FAILURE_MESSAGE)
    else:
        form = ClassBillForm(instance=class_bill)

    context = {
        "class_bill": class_bill,
        "bill_item_form": form,
    }
    return render(request, "fees/edit_class_bill_item.html", context)


@login_required
def delete_class_bill_item_view(request, id):
    class_bill = get_object_or_404(ClassBill, id=id)
    StudentBillItem.objects.filter(
        bill__academic_class=class_bill.academic_class,
        bill_item=class_bill.bill_item
    ).delete()
    class_bill.delete()
    messages.success(request, DELETE_MESSAGE)
    return redirect("class_bill_list")

 

@login_required
def class_subject_allocation_list(request):
    # Get the logged-in user's staff account
    try:
        staff_account = StaffAccount.objects.get(user=request.user)
        staff_member = staff_account.staff
    except StaffAccount.DoesNotExist:
        messages.error(request, "You do not have the necessary permissions to view this page.")
        return redirect('dashboard')

    active_role = request.session.get("active_role_name")
    role_name = staff_account.role.name if staff_account and staff_account.role else None
    effective_role = active_role or role_name

    if effective_role == "Class Teacher":
        allocations = ClassSubjectAllocation.objects.filter(
            Q(academic_class_stream__class_teacher=staff_member)
            | Q(subject_teacher=staff_member)
        )
    else:
        allocations = ClassSubjectAllocation.objects.filter(subject_teacher=staff_member)
    
    context = {
        'allocations': allocations
    }
    return render(request, 'classes/classsubjectallocation_list.html', context)

@login_required
def add_class_subject_allocation(request):
    staff_account = getattr(request.user, "staff_account", None)
    role_name = staff_account.role.name if staff_account and staff_account.role else None
    active_role = request.session.get("active_role_name")
    effective_role = active_role or role_name
    is_class_teacher = effective_role == "Class Teacher"
    is_dos = effective_role in {"Director of Studies", "DOS"}
    is_admin = effective_role in {"Admin", "Head master"}

    if not (is_dos or is_admin):
        messages.error(request, "Only Admin or the Director of Studies can manage subject allocations.")
        return redirect("class_subject_allocation_page")

    if is_class_teacher and staff_account and staff_account.staff:
        class_stream_ids = AcademicClassStream.objects.filter(
            class_teacher=staff_account.staff
        ).values_list("id", flat=True)
        allocations = ClassSubjectAllocation.objects.filter(
            academic_class_stream_id__in=class_stream_ids
        )
    else:
        allocations = ClassSubjectAllocation.objects.all()

    if request.method == "POST":
        form = ClassSubjectAllocationForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                _, created = ClassSubjectAllocation.objects.update_or_create(
                    academic_class_stream=data["academic_class_stream"],
                    subject=data["subject"],
                    defaults={"subject_teacher": data["subject_teacher"]},
                )
                if created:
                    messages.success(request, SUCCESS_ADD_MESSAGE)
                else:
                    messages.success(request, "Allocation already existed. Teacher was updated.")
            except IntegrityError:
                messages.error(request, "This class stream and subject allocation already exists.")
            return redirect("subject_allocation_page")
        messages.error(request, FAILURE_MESSAGE)
    else:
        form = ClassSubjectAllocationForm()
    context={
        'form':form,
        'allocations':allocations,
        'is_dos': is_dos,
        'is_admin': is_admin,
        'is_class_teacher': is_class_teacher,
    }
    return render(request, 'classes/classsubjectallocation_form.html', context)

@login_required
def edit_subject_allocation_view(request,id):
    staff_account = getattr(request.user, "staff_account", None)
    role_name = staff_account.role.name if staff_account and staff_account.role else None
    active_role = request.session.get("active_role_name")
    effective_role = active_role or role_name
    is_dos = effective_role in {"Director of Studies", "DOS"}
    is_admin = effective_role in {"Admin", "Head master"}

    if not (is_dos or is_admin):
        messages.error(request, "Only Admin or the Director of Studies can manage subject allocations.")
        return redirect("class_subject_allocation_page")

    allocation = get_model_record(ClassSubjectAllocation,id)
    if request.method =="POST":
            form = ClassSubjectAllocationForm(request.POST,instance=allocation)
            if form.is_valid():
                try:
                    form.save()
                    messages.success(request,SUCCESS_ADD_MESSAGE)
                    return HttpResponseRedirect(reverse(add_class_subject_allocation))
                except IntegrityError:
                    messages.error(request, "Another allocation already uses this class stream and subject.")
            else:
                messages.error(request, FAILURE_MESSAGE)
    form= ClassSubjectAllocationForm(instance=allocation)
    
    context={
        "form":form,
        "allocation":allocation
        
    }
    return render (request,"classes/edit_class_allocation.html",context)

 



def delete_class_subject_allocation(request, id):
    staff_account = getattr(request.user, "staff_account", None)
    role_name = staff_account.role.name if staff_account and staff_account.role else None
    active_role = request.session.get("active_role_name")
    effective_role = active_role or role_name
    is_dos = effective_role in {"Director of Studies", "DOS"}
    is_admin = effective_role in {"Admin", "Head master"}

    if not (is_dos or is_admin):
        messages.error(request, "Only Admin or the Director of Studies can manage subject allocations.")
        return redirect("class_subject_allocation_page")

    allocation = ClassSubjectAllocation.objects.get( pk=id)
    
    allocation.delete()
    messages.success(request, DELETE_MESSAGE)
    return redirect(add_class_subject_allocation)


@login_required
def copy_allocations_from_previous_term(request):
    """Copy subject allocations from the previous term to the current term."""
    staff_account = getattr(request.user, "staff_account", None)
    role_name = staff_account.role.name if staff_account and staff_account.role else None
    active_role = request.session.get("active_role_name")
    effective_role = active_role or role_name
    is_dos = effective_role in {"Director of Studies", "DOS"}
    is_admin = effective_role in {"Admin", "Head master"}

    if not (is_dos or is_admin):
        messages.error(request, "Only Admin or the Director of Studies can copy allocations.")
        return redirect("class_subject_allocation_page")

    try:
        # Get current academic year and term
        from app.selectors.school_settings import get_current_academic_year
        from app.models.classes import Term
        
        current_year = get_current_academic_year()
        current_term = Term.objects.filter(is_current=True).first()

        if not current_year or not current_term:
            messages.error(request, "No current academic year or term set.")
            return redirect("subject_allocation_page")

        # Find the previous term
        if current_term.term == "1":
            # Term 1 -> look for previous year's Term 3
            # Get previous year by subtracting 1 from the year string
            try:
                prev_year_num = int(current_year.academic_year) - 1
                previous_year = AcademicYear.objects.filter(
                    academic_year=str(prev_year_num)
                ).first()
            except:
                previous_year = None
            previous_term = Term.objects.filter(term="3").first()
        else:
            # Same year, previous term number
            previous_year = current_year
            prev_term_num = str(int(current_term.term) - 1)
            previous_term = Term.objects.filter(term=prev_term_num).first()

        if not previous_term:
            messages.error(request, "Could not determine previous term.")
            return redirect("subject_allocation_page")

        # Get all class streams for the current term
        current_class_streams = AcademicClassStream.objects.filter(
            academic_class__academic_year=current_year,
            academic_class__term=current_term
        )

        # Get allocations from previous term
        previous_class_streams = AcademicClassStream.objects.filter(
            academic_class__academic_year=previous_year,
            academic_class__term=previous_term
        )

        # Create a mapping from (class, stream, subject) -> teacher from previous term
        previous_allocations = ClassSubjectAllocation.objects.filter(
            academic_class_stream__in=previous_class_streams
        ).select_related('subject', 'subject_teacher', 'academic_class_stream__stream', 'academic_class_stream__academic_class__Class')

        # Build mapping: (class_id, stream_id, subject_id) -> subject_teacher
        allocation_map = {}
        for alloc in previous_allocations:
            key = (
                alloc.academic_class_stream.academic_class.Class.id,
                alloc.academic_class_stream.stream.id,
                alloc.subject.id
            )
            allocation_map[key] = alloc.subject_teacher

        # Now create allocations for current term based on previous allocations
        created_count = 0
        skipped_count = 0
        errors = []

        for current_stream in current_class_streams:
            for alloc in previous_allocations.filter(
                academic_class_stream__academic_class__Class=current_stream.academic_class.Class,
                academic_class_stream__stream=current_stream.stream
            ):
                try:
                    _, created = ClassSubjectAllocation.objects.get_or_create(
                        academic_class_stream=current_stream,
                        subject=alloc.subject,
                        defaults={"subject_teacher": alloc.subject_teacher},
                    )
                    if created:
                        created_count += 1
                    else:
                        skipped_count += 1
                except Exception as e:
                    # Skip if duplicate (IntegrityError) or other error
                    if 'Duplicate entry' in str(e) or 'UNIQUE constraint' in str(e):
                        skipped_count += 1
                    else:
                        errors.append(str(e))

        messages.success(request, f"Successfully copied {created_count} allocations. {skipped_count} already existed.")
        if errors:
            messages.warning(request, f"Some errors occurred: {', '.join(errors[:3])}")
    except Exception as e:
        logger.error(f"Error copying allocations: {str(e)}")
        messages.error(request, f"Error copying allocations: {str(e)}")

    return redirect("subject_allocation_page")
    



@login_required
def bulk_create_class_bills(request):
    """
    Bulk create class bills for multiple classes at once
    """
    if request.method == "POST":
        # Get selected classes and bill item
        selected_classes = request.POST.getlist('selected_classes')
        bill_item_id = request.POST.get('bill_item')
        amount = request.POST.get('amount')

        if not selected_classes:
            messages.error(request, "Please select at least one class.")
            return redirect('bulk_create_class_bills')

        if not bill_item_id or not amount:
            messages.error(request, "Please provide bill item and amount.")
            return redirect('bulk_create_class_bills')

        try:
            bill_item = BillItem.objects.get(id=bill_item_id)
            amount = float(amount)

            # Get current academic year and term
            current_year = AcademicYear.objects.filter(is_current=True).first()
            current_term = Term.objects.filter(is_current=True).first()

            if not current_year or not current_term:
                messages.error(request, "No current academic year or term found.")
                return redirect('bulk_create_class_bills')

            bills_created = 0
            students_affected = 0
            total_amount = 0

            for class_id in selected_classes:
                try:
                    academic_class = AcademicClass.objects.get(
                        Class__id=class_id,
                        academic_year=current_year,
                        term=current_term
                    )

                    # Create class bill
                    class_bill, created = ClassBill.objects.get_or_create(
                        academic_class=academic_class,
                        bill_item=bill_item,
                        defaults={'amount': amount}
                    )

                    if created:
                        bills_created += 1

                        # Create student bill items
                        students_in_class = Student.objects.filter(current_class__id=class_id, is_active=True)
                        for student in students_in_class:
                            student_bill, _ = StudentBill.objects.get_or_create(
                                student=student,
                                academic_class=academic_class,
                                defaults={'status': 'Unpaid'}
                            )

                            if bill_item.item_name != "School Fees":
                                # Ensure a single StudentBillItem per (bill, bill_item); clean up duplicates if any
                                qs = StudentBillItem.objects.filter(
                                    bill=student_bill,
                                    bill_item=bill_item
                                ).order_by('id')
                                if qs.exists():
                                    student_bill_item = qs.first()
                                    # Remove duplicates if present
                                    if qs.count() > 1:
                                        qs.exclude(pk=student_bill_item.pk).delete()
                                    # Update to current values
                                    student_bill_item.description = bill_item.description
                                    student_bill_item.amount = amount
                                    student_bill_item.save()
                                else:
                                    StudentBillItem.objects.create(
                                        bill=student_bill,
                                        bill_item=bill_item,
                                        description=bill_item.description,
                                        amount=amount
                                    )

                            students_affected += 1

                        total_amount += amount * students_in_class.count()

                except AcademicClass.DoesNotExist:
                    messages.warning(request, f"Academic class not found for class ID {class_id}")
                    continue

            if bills_created > 0:
                success_msg = (
                    f"✅ Bulk bill creation completed!<br>"
                    f"• Bills created: {bills_created}<br>"
                    f"• Students affected: {students_affected}<br>"
                    f"• Total billing amount: UGX {total_amount:,.0f}"
                )
                messages.success(request, success_msg)
            else:
                messages.warning(request, "No new bills were created. They may already exist.")

        except BillItem.DoesNotExist:
            messages.error(request, "Selected bill item not found.")
        except ValueError:
            messages.error(request, "Invalid amount provided.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

        return redirect('class_bill_list')

    # GET request - show form
    # Get current academic year and term
    current_year = AcademicYear.objects.filter(is_current=True).first()
    current_term = Term.objects.filter(is_current=True).first()

    available_classes = []
    if current_year and current_term:
        academic_classes = AcademicClass.objects.filter(
            academic_year=current_year,
            term=current_term
        ).select_related('Class')

        for ac in academic_classes:
            # Check if class already has bills
            existing_bills = ClassBill.objects.filter(academic_class=ac).count()

            # Get actual active student count for this class
            student_count = Student.objects.filter(current_class=ac.Class, is_active=True).count()

            available_classes.append({
                'id': ac.Class.id,
                'name': str(ac.Class),
                'existing_bills': existing_bills,
                'academic_class': ac,
                'student_count': student_count
            })

    bill_items = BillItem.objects.all()

    context = {
        'available_classes': available_classes,
        'bill_items': bill_items,
        'current_year': current_year,
        'current_term': current_term,
    }

    return render(request, 'fees/bulk_create_bills.html', context)
    
    
