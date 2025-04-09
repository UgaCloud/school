from django.shortcuts import render, redirect, HttpResponseRedirect,get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse
import logging
logger = logging.getLogger(__name__)
from app.constants import *
from app.models.students  import Student
from app.models.classes import Class, AcademicClass, Stream, AcademicClassStream,ClassSubjectAllocation
from app.forms.classes import ClassForm, AcademicClassForm, StreamForm, AcademicClassStreamForm,ClassSubjectAllocationForm
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
    # Get search parameters from GET request
    class_filter = request.GET.get('class', '').strip()
    year_filter = request.GET.get('year', '').strip()

    if request.user.is_superuser:
        academic_classes = AcademicClass.objects.all()
    else:
        try:
            staff_account = StaffAccount.objects.get(user=request.user)
            staff_member = staff_account.staff
        except StaffAccount.DoesNotExist:
            messages.error(request, "You do not have the necessary permissions to view this page.")
            return redirect('dashboard')

        academic_classes = AcademicClass.objects.filter(
            id__in=AcademicClassStream.objects.filter(
                id__in=ClassSubjectAllocation.objects.filter(subject_teacher=staff_member)
                .values_list("academic_class_stream_id", flat=True)
            ).values_list("academic_class_id", flat=True)
        ).distinct()

    # Apply filters if search parameters are provided
    if class_filter:
        academic_classes = academic_classes.filter(Class__code__icontains=class_filter)  # Adjust this field as necessary
    # Group by Section and Class
    grouped_classes = []
    sorted_classes = sorted(academic_classes, key=attrgetter('section', 'Class.code'))
    
    for key, group in groupby(sorted_classes, key=attrgetter('section', 'Class.code')):
        class_list = list(group)
        grouped_classes.append({
            "section": key[0],
            "class": key[1],
            "entries": class_list
        })

    context = {
        "grouped_classes": grouped_classes,
        "form": AcademicClassForm(),
        "academic_years": school_settings_selectors.get_academic_years(),
        "classes": class_selectors.get_classes()
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

    context = {
        "academic_class": academic_class,
        "class_streams": academic_class_streams,
        "class_stream_form": class_stream_form,
        "class_register": class_register,
        "bill_item_form": bill_item_form,
        "class_teachers": class_teachers,  
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
    class_stream_form = AcademicClassStreamForm(request.POST)
    
    if class_stream_form.is_valid():
        class_stream_form.save()
        
        messages.success(request, SUCCESS_ADD_MESSAGE)
    else:
        messages.error(request, FAILURE_MESSAGE)
        
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
    academic_classes = AcademicClass.objects.all()
    class_filter = request.GET.get('class')
    academic_year_filter = request.GET.get('academic_year')
    term_filter = request.GET.get('term')

    if class_filter:
        academic_classes = academic_classes.filter(Class__id=class_filter)  
    if academic_year_filter:
        academic_classes = academic_classes.filter(academic_year__id=academic_year_filter)  
    if term_filter:
        academic_classes = academic_classes.filter(term__id=term_filter) 

    class_options = Class.objects.all()
    academic_year_options = AcademicYear.objects.all()
    term_options = Term.objects.all()

    context = {
        "academic_classes": academic_classes,
        "class_options": class_options,
        "academic_year_options": academic_year_options,
        "term_options": term_options,
        "class_filter": class_filter,
        "academic_year_filter": academic_year_filter,
        "term_filter": term_filter,
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
            
            students_in_class = Student.objects.filter(current_class=academic_class.Class)  
            
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

            # Update the StudentBillItems for all students in the academic class
            students_in_class = Student.objects.filter(current_class=academic_class.Class)

            for student in students_in_class:
                student_bill, created = StudentBill.objects.get_or_create(
                    student=student,
                    academic_class=academic_class,
                    status="Unpaid",
                )

                
                if updated_class_bill.bill_item.item_name != "School Fees":
                    student_bill_item, created = StudentBillItem.objects.get_or_create(
                        bill=student_bill,
                        bill_item=updated_class_bill.bill_item,
                        description=updated_class_bill.bill_item.description,
                    )

                    student_bill_item.amount = updated_class_bill.amount 
                    student_bill_item.save()

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
    
    # Filter allocations based on the logged-in staff member
    allocations = ClassSubjectAllocation.objects.filter(subject_teacher=staff_member)
    
    context = {
        'allocations': allocations
    }
    return render(request, 'classes/classsubjectallocation_list.html', context)

@login_required
def add_class_subject_allocation(request):
    if request.method == "POST":
        form = ClassSubjectAllocationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, SUCCESS_ADD_MESSAGE)
            return redirect(add_class_subject_allocation)
    else:
        form = ClassSubjectAllocationForm()
    allocations = ClassSubjectAllocation.objects.all()
    context={
        'form':form,
        'allocations':allocations
    }
    return render(request, 'classes/classsubjectallocation_form.html', context)

@login_required
def edit_subject_allocation_view(request,id):
    allocation = get_model_record(ClassSubjectAllocation,id)
    if request.method =="POST":
            form = ClassSubjectAllocationForm(request.POST,instance=allocation)
            if form.is_valid():
                form.save()
                messages.success(request,SUCCESS_ADD_MESSAGE)
                return HttpResponseRedirect(reverse(add_class_subject_allocation))
            else:
                messages.error(request, FAILURE_MESSAGE)
    form= ClassSubjectAllocationForm(instance=allocation)
    
    context={
        "form":form,
        "allocation":allocation
        
    }
    return render (request,"classes/edit_class_allocation.html",context)

 



def delete_class_subject_allocation(request, id):
    allocation = ClassSubjectAllocation.objects.get( pk=id)
    
    allocation.delete()
    messages.success(request, DELETE_MESSAGE)
    return redirect(add_class_subject_allocation)
    
    