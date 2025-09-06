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
    if request.method == "POST":
        academic_class_form = AcademicClassForm(request.POST)
        if academic_class_form.is_valid():
            academic_class_form.save()
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)

    academic_class_form = AcademicClassForm()

    # Safely get StaffAccount and Role
    staff_account = getattr(request.user, "staff_account", None)
    role_name = staff_account.role.name if staff_account and staff_account.role else None

    if role_name == "Admin":
        academic_classes = AcademicClass.objects.all()
    elif role_name == "Teacher":
        if staff_account.staff:
            academic_classes = AcademicClass.objects.filter(
                id__in=ClassSubjectAllocation.objects.filter(
                    subject_teacher=staff_account.staff
                ).values_list("academic_class_stream__academic_class_id", flat=True)
            ).distinct()
        else:
            academic_classes = AcademicClass.objects.none()
    else:
        academic_classes = AcademicClass.objects.none()

    context = {
        "form": academic_class_form,
        "academic_years": school_settings_selectors.get_academic_years(),
        "academic_classes": academic_classes,
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
    # Enhanced filtering with better defaults
    academic_classes = AcademicClass.objects.select_related('Class', 'academic_year', 'term', 'section')

    # Get filter parameters
    class_filter = request.GET.get('class')
    academic_year_filter = request.GET.get('academic_year')
    term_filter = request.GET.get('term')
    status_filter = request.GET.get('status', 'all')

    # Apply filters
    if class_filter and class_filter != 'all':
        academic_classes = academic_classes.filter(Class__id=class_filter)
    if academic_year_filter and academic_year_filter != 'all':
        academic_classes = academic_classes.filter(academic_year__id=academic_year_filter)
    if term_filter and term_filter != 'all':
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

        # Get all students in this class - use the most reliable method
        students_in_class = Student.objects.filter(current_class=academic_class.Class)
        total_students = students_in_class.count()

        # Debug logging removed

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
        "class_filter": class_filter or 'all',
        "academic_year_filter": academic_year_filter or 'all',
        "term_filter": term_filter or 'all',
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
                        students_in_class = Student.objects.filter(current_class__id=class_id)
                        for student in students_in_class:
                            student_bill, _ = StudentBill.objects.get_or_create(
                                student=student,
                                academic_class=academic_class,
                                defaults={'status': 'Unpaid'}
                            )

                            if bill_item.item_name != "School Fees":
                                StudentBillItem.objects.get_or_create(
                                    bill=student_bill,
                                    bill_item=bill_item,
                                    defaults={
                                        'description': bill_item.description,
                                        'amount': amount
                                    }
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

            # Get actual student count for this class
            student_count = Student.objects.filter(current_class=ac.Class).count()

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
    
    