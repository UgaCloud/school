from django.shortcuts import render, redirect, HttpResponseRedirect,get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib import messages
from django.urls import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from app.selectors.model_selectors import *
from app.constants import *
from app.selectors.fees_selectors import * 
from app.forms.fees_payment import * 
from django.contrib.auth.decorators import login_required
from app.models.students import *
from app.models.classes import *
from app.models.school_settings import AcademicYear

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from io import BytesIO
from django.utils import timezone

@login_required
def manage_bill_items_view(request):
    bill_items = get_bill_items()
    bill_item_form = BillItemForm()
    
    context = {
        "bill_items": bill_items,
        "bill_item_form": bill_item_form
    }
    return render(request, "fees/bill_items.html", context)

@login_required
def add_bill_item_view(request):
    if request.method == "POST":
        bill_item_form = BillItemForm(request.POST)
    
        if bill_item_form.is_valid():
            bill_item_form.save()
            
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
    else:
        messages.warning(request, "Not a Post Method")
        
    return HttpResponseRedirect(reverse(manage_bill_items_view))


@login_required
def edit_bill_item_view(request,id):
    bill_item = get_model_record(BillItem,id)
    if request.method =="POST":
        form= BillItemForm(request.POST,instance=bill_item)
        if form.is_valid():
            form.save()

            messages.success(request,SUCCESS_ADD_MESSAGE)
            return HttpResponseRedirect(reverse(manage_bill_items_view))
        else:
            messages.error(request,FAILURE_MESSAGE)
            
    form = BillItemForm(instance=bill_item)
    context={
        "form":form,
        "bill_item":bill_item
        
    }
    return render(request,"fees/edit_bill_item.html",context)


def delete_bill_item_view(request, id):
    bill_item = get_model_record(BillItem, id)
    
    bill_item.delete()
    
    messages.success(request, DELETE_MESSAGE)

    return HttpResponseRedirect(reverse(manage_bill_items_view))



@login_required
def manage_student_bills_view(request):
    # Get filter parameters
    academic_year_id = request.GET.get('academic_year')
    term_id = request.GET.get('term')
    class_id = request.GET.get('class')
    search_query = request.GET.get('search', '').strip()

    # Convert 'None' strings to None
    if academic_year_id == 'None' or academic_year_id == '':
        academic_year_id = None
    if term_id == 'None' or term_id == '':
        term_id = None
    if class_id == 'None' or class_id == '':
        class_id = None

    # Get all filter options
    academic_years = AcademicYear.objects.all()
    terms = Term.objects.all()
    classes = Class.objects.all()

    # Start with all student bills
    student_bills = StudentBill.objects.select_related(
        'student', 'academic_class', 'academic_class__academic_year',
        'academic_class__term', 'academic_class__Class'
    ).order_by('-bill_date')

    # Apply filters
    if academic_year_id:
        student_bills = student_bills.filter(academic_class__academic_year_id=academic_year_id)

    if term_id:
        student_bills = student_bills.filter(academic_class__term_id=term_id)

    if class_id:
        student_bills = student_bills.filter(academic_class__Class_id=class_id)

    if search_query:
        student_bills = student_bills.filter(
            student__student_name__icontains=search_query
        )

    # Calculate summary statistics before pagination
    all_bills = student_bills  # Keep reference for statistics
    total_bills = all_bills.count()
    total_amount = sum(bill.total_amount for bill in all_bills)
    total_paid = sum(bill.amount_paid for bill in all_bills)
    total_outstanding = total_amount - total_paid

    # Status breakdown
    paid_bills = all_bills.filter(status='Paid').count()
    unpaid_bills = all_bills.filter(status='Unpaid').count()
    overdue_bills = all_bills.filter(status='Overdue').count()

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(student_bills, 25)  # 25 bills per page

    try:
        student_bills = paginator.page(page)
    except PageNotAnInteger:
        student_bills = paginator.page(1)
    except EmptyPage:
        student_bills = paginator.page(paginator.num_pages)

    context = {
        "student_bills": student_bills,
        "academic_years": academic_years,
        "terms": terms,
        "classes": classes,
        "selected_academic_year": str(academic_year_id) if academic_year_id else '',
        "selected_term": str(term_id) if term_id else '',
        "selected_class": str(class_id) if class_id else '',
        "search_query": search_query,
        # Summary statistics
        "total_bills": total_bills,
        "total_amount": total_amount,
        "total_paid": total_paid,
        "total_outstanding": total_outstanding,
        "paid_bills": paid_bills,
        "unpaid_bills": unpaid_bills,
        "overdue_bills": overdue_bills,
    }
    return render(request, "fees/student_bills.html", context)

@login_required
def manage_student_bill_details_view(request, id):
    context = get_student_bill_details(id)
    context["bill_item_form"] = StudentBillItemForm(initial={"bill": context["student_bill"]})
    # Pre-fill recorded_by so bursar doesn't need to type it
    context["payment_form"] = PaymentForm(initial={
        "bill": context["student_bill"],
        "recorded_by": getattr(request.user, "username", "") or getattr(request.user, "get_username", lambda: "")()
    })
    student = context["student_bill"].student
    context["academic_year"] = student.academic_year
    context["term"] = student.term

    return render(request, "fees/student_bill_details.html", context)



@login_required
def add_student_bill_item_view(request, id):
    bill = get_student_bill(id)
    
    if request.method == "POST":
        
        form = StudentBillItemForm(request.POST)
        
        if form.is_valid():
            form.save()
            
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
    else:
        messages.warning(request, "Not a Post Method")
        
    return HttpResponseRedirect(reverse(manage_student_bill_details_view, args=[bill.id]))

@login_required
def add_student_payment_view(request, id):
    bill = get_student_bill(id)
    
    if request.method == "POST":
        form = PaymentForm(request.POST)
        
        if form.is_valid():
            payment = form.save(commit=False)
            # Ensure the recorder is always the current user regardless of form input
            payment.bill = bill  # enforce bill from URL context
            payment.recorded_by = getattr(request.user, "username", "") or getattr(request.user, "get_username", lambda: "")()
            # Auto-generate reference_no if not provided or blank
            if not getattr(payment, "reference_no", None) or str(payment.reference_no).strip() == "":
                payment.reference_no = f"PMT-{bill.id}-{timezone.now().strftime('%Y%m%d%H%M%S%f')}"
            payment.save()
            
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
    else:
        messages.warning(request, "Not a Post Method")
        
    return HttpResponseRedirect(reverse(manage_student_bill_details_view, args=[bill.id]))
    

  

@login_required
def student_fees_status_view(request):
    """Fees status scoped to current academic year and term, enrolled students only, with due dates and payment history."""
    # Scope: current academic year and current term by default
    current_year = AcademicYear.objects.filter(is_current=True).first()
    current_term = Term.objects.filter(is_current=True, academic_year=current_year).first() if current_year else None

    selected_academic_class = request.GET.get("academic_class")
    selected_term_id = request.GET.get("term")
    selected_year_id = request.GET.get("year")

    # Resolve selected academic year (defaults to current)
    selected_year = None
    if selected_year_id:
        selected_year = AcademicYear.objects.filter(id=selected_year_id).first()
    if not selected_year:
        selected_year = current_year

    # Available filters (limited to selected year)
    academic_years = AcademicYear.objects.all().order_by('-id')
    academic_classes = AcademicClass.objects.filter(academic_year=selected_year) if selected_year else AcademicClass.objects.none()
    terms = Term.objects.filter(academic_year=selected_year) if selected_year else Term.objects.none()

    # Apply selected filters
    filtered_academic_classes = academic_classes
    if selected_academic_class:
        filtered_academic_classes = filtered_academic_classes.filter(Class_id=selected_academic_class)
    if selected_term_id:
        filtered_academic_classes = filtered_academic_classes.filter(term_id=selected_term_id)
    else:
        # default to current term of selected year
        default_term = Term.objects.filter(is_current=True, academic_year=selected_year).first()
        if default_term:
            filtered_academic_classes = filtered_academic_classes.filter(term=default_term)

    # Determine effective term
    term_obj = Term.objects.filter(id=selected_term_id).first() if selected_term_id else Term.objects.filter(is_current=True, academic_year=selected_year).first()

    # Build rows from StudentBill to ensure we show existing billed data
    student_fees_data = []
    now = timezone.now().date()
    bills_qs = StudentBill.objects.filter(
        academic_class__academic_year=selected_year,
        academic_class__term=term_obj,
    )
    if selected_academic_class:
        bills_qs = bills_qs.filter(academic_class__Class_id=selected_academic_class)

    for bill in bills_qs.select_related("student", "academic_class", "academic_class__Class"):
        total_amount = bill.total_amount
        amount_paid = bill.amount_paid
        due_date = bill.due_date

        if amount_paid >= total_amount and total_amount > 0:
            payment_status = "Paid"; balance = 0; balance_label = ""
        elif amount_paid == 0 and total_amount == 0:
            payment_status = "No Bill"; balance = 0; balance_label = ""
        else:
            balance = abs(total_amount - amount_paid)
            if amount_paid > total_amount:
                payment_status = "Overpaid"; balance_label = "CR"
            elif amount_paid == 0 and total_amount > 0:
                is_overdue = bool(due_date and now > due_date)
                payment_status = "Overdue" if is_overdue else "Unpaid"; balance_label = "DR"
            else:
                is_overdue = bool(due_date and now > due_date and amount_paid < total_amount)
                payment_status = "Overdue" if is_overdue else "Partial"; balance_label = "DR"

        recent_payments = list(
            Payment.objects.filter(bill=bill).order_by("-payment_date").values("amount", "payment_date")[:3]
        )

        student_fees_data.append({
            "student": bill.student,
            "academic_class": bill.academic_class,
            "academic_year": bill.academic_class.academic_year,
            "term": bill.academic_class.term,
            "total_amount": total_amount,
            "amount_paid": amount_paid,
            "amount_paid_percentage": (amount_paid / total_amount * 100) if total_amount > 0 else 0,
            "payment_status": payment_status,
            "balance": balance if 'balance' in locals() else 0,
            "balance_label": balance_label if 'balance_label' in locals() else "",
            "recent_payments": recent_payments,
            "bill_id": bill.id,
        })

    if request.GET.get("download_pdf"):
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Margins and title
        left_margin = 2 * cm
        top_margin = height - 2 * cm
        bottom_margin = 2 * cm
        row_height = 1 * cm

        p.setFont("Helvetica-Bold", 16)
        title = "Student Fees Payment Status"
        title_width = p.stringWidth(title, "Helvetica-Bold", 16)
        p.drawString((width - title_width) / 2, top_margin, title)
        y = top_margin - 1.5 * cm

        headers = ["Class", "Student", "Total Fees", "Amount Paid", "Balance", "Status"]
        col_widths = [3 * cm, 5 * cm, 3 * cm, 3 * cm, 3 * cm, 4 * cm]

        def draw_table_row(values, y_pos, is_header=False, shade=False):
            x = left_margin
            p.setStrokeColor(colors.black)

            if shade:
                p.setFillColor(colors.lightgrey)
                p.rect(left_margin, y_pos - row_height + 0.2 * cm, sum(col_widths), row_height, fill=1, stroke=0)

            p.setFillColor(colors.black)
            p.setFont("Helvetica-Bold", 10 if is_header else 9)

            for i, value in enumerate(values):
                p.drawString(x + 0.2 * cm, y_pos, str(value))
                x += col_widths[i]

            # Draw horizontal lines
            p.line(left_margin, y_pos + 0.2 * cm, left_margin + sum(col_widths), y_pos + 0.2 * cm)
            p.line(left_margin, y_pos - row_height + 0.2 * cm, left_margin + sum(col_widths), y_pos - row_height + 0.2 * cm)

            # Draw vertical lines
            x = left_margin
            for w in col_widths:
                p.line(x, y_pos + 0.2 * cm, x, y_pos - row_height + 0.2 * cm)
                x += w
            p.line(x, y_pos + 0.2 * cm, x, y_pos - row_height + 0.2 * cm)

        draw_table_row(headers, y, is_header=True)
        y -= row_height

        for idx, row in enumerate(student_fees_data):
            if y < bottom_margin + row_height:
                p.showPage()
                y = top_margin
                p.setFont("Helvetica-Bold", 16)
                p.drawString((width - title_width) / 2, y, title)
                y -= 1.5 * cm
                draw_table_row(headers, y, is_header=True)
                y -= row_height

            values = [
                str(row["academic_class"]),
                row["student"].student_name,
                f"{row['total_amount']:,}",
                f"{row['amount_paid']:,}",
                f"{row['balance_label']} {row['balance']:,}" if row["balance_label"] else f"{row['balance']:,}",
                row["payment_status"],
            ]
            draw_table_row(values, y, shade=(idx % 2 == 0))
            y -= row_height

        p.save()
        buffer.seek(0)
        return HttpResponse(buffer, content_type="application/pdf")

    # Fallback: if no rows for selected term, try latest term WITH data in the selected year
    if not student_fees_data:
        from django.db.models import Max
        # Find latest term (by start_date) within selected year that has any StudentBill
        term_ids_with_bills = (
            StudentBill.objects.filter(academic_class__academic_year=selected_year)
            .values_list('academic_class__term_id', flat=True)
            .distinct()
        )
        fallback_term = (
            Term.objects.filter(id__in=term_ids_with_bills, academic_year=selected_year)
            .order_by('-start_date')
            .first()
        )
        if fallback_term and (not selected_term_id or str(fallback_term.id) != str(selected_term_id)):
            term_obj = fallback_term
            # Rebuild from bills for fallback term
            bills_qs = StudentBill.objects.filter(
                academic_class__academic_year=selected_year,
                academic_class__term=term_obj,
            )
            if selected_academic_class:
                bills_qs = bills_qs.filter(academic_class__Class_id=selected_academic_class)
            student_fees_data = []
            now = timezone.now().date()
            for bill in bills_qs.select_related("student", "academic_class", "academic_class__Class"):
                total_amount = bill.total_amount
                amount_paid = bill.amount_paid
                due_date = bill.due_date
                if amount_paid >= total_amount and total_amount > 0:
                    payment_status = "Paid"; balance = 0; balance_label = ""
                elif amount_paid == 0 and total_amount == 0:
                    payment_status = "No Bill"; balance = 0; balance_label = ""
                else:
                    balance = abs(total_amount - amount_paid)
                    if amount_paid > total_amount:
                        payment_status = "Overpaid"; balance_label = "CR"
                    elif amount_paid == 0 and total_amount > 0:
                        is_overdue = bool(due_date and now > due_date)
                        payment_status = "Overdue" if is_overdue else "Unpaid"; balance_label = "DR"
                    else:
                        is_overdue = bool(due_date and now > due_date and amount_paid < total_amount)
                        payment_status = "Overdue" if is_overdue else "Partial"; balance_label = "DR"
                recent_payments = list(
                    Payment.objects.filter(bill=bill).order_by('-payment_date').values('amount','payment_date')[:3]
                )
                student_fees_data.append({
                    "student": bill.student,
                    "academic_class": bill.academic_class,
                    "academic_year": bill.academic_class.academic_year,
                    "term": bill.academic_class.term,
                    "total_amount": total_amount,
                    "amount_paid": amount_paid,
                    "amount_paid_percentage": (amount_paid / total_amount * 100) if total_amount > 0 else 0,
                    "payment_status": payment_status,
                    "balance": balance if 'balance' in locals() else 0,
                    "balance_label": balance_label if 'balance_label' in locals() else "",
                    "recent_payments": recent_payments,
                    "bill_id": bill.id,
                })
            # Update the effective filters
            selected_term_id = str(fallback_term.id)

    # Summary metrics for UX
    total_fees = sum(row["total_amount"] for row in student_fees_data)
    total_paid = sum(row["amount_paid"] for row in student_fees_data)
    total_balance = sum(row["balance"] for row in student_fees_data if row.get("balance_label") != "CR")

    context = {
        "academic_years": academic_years,
        "academic_classes": academic_classes,
        "terms": terms,
        "class_filter": int(selected_academic_class) if selected_academic_class else "",
        "academic_class_filter": int(selected_academic_class) if selected_academic_class else "",
        "term_filter": int(selected_term_id) if selected_term_id else (current_term.id if current_term else ""),
        "year_filter": int(selected_year.id) if selected_year else "",
        "student_fees_data": student_fees_data,
        "total_fees": total_fees,
        "total_paid": total_paid,
        "total_balance": total_balance,
        "current_term": term_obj if 'term_obj' in locals() and term_obj else current_term,
        "current_year": selected_year,
    }

    return render(request, "fees/student_fees_status.html", context)



