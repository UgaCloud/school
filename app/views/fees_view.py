from django.shortcuts import render, redirect, HttpResponseRedirect,get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib import messages
from django.urls import reverse
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
def  manage_student_bills_view(request):
    student_bills = get_student_bills()
    
    context = {
        "student_bills": student_bills,
    }
    return render(request, "fees/student_bills.html", context)

@login_required
def manage_student_bill_details_view(request, id):
    context = get_student_bill_details(id)
    context["bill_item_form"] = StudentBillItemForm(initial={"bill": context["student_bill"]})
    context["payment_form"] = PaymentForm(initial={"bill": context["student_bill"]})
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
            form.save()
            
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
    else:
        messages.warning(request, "Not a Post Method")
        
    return HttpResponseRedirect(reverse(manage_student_bill_details_view, args=[bill.id]))
    

    



@login_required
def student_fees_status_view(request):
    students = Student.objects.all()
    student_fees_data = []

    selected_academic_class = request.GET.get("academic_class")
    selected_term = request.GET.get("term")

    academic_classes = AcademicClass.objects.all()
    terms = Term.objects.all()

    filtered_academic_classes = academic_classes
    if selected_academic_class:
        filtered_academic_classes = filtered_academic_classes.filter(Class_id=selected_academic_class)
    if selected_term:
        filtered_academic_classes = filtered_academic_classes.filter(term_id=selected_term)

    if selected_academic_class or selected_term:
        class_ids = filtered_academic_classes.values_list("Class_id", flat=True)
        students = students.filter(current_class_id__in=class_ids)

    for student in students:
        student_bill = StudentBill.objects.filter(student=student).first()
        academic_class = AcademicClass.objects.filter(Class=student.current_class).first()

        academic_year = academic_class.academic_year if academic_class else None
        term = academic_class.term if academic_class else None

        total_amount = student_bill.total_amount if student_bill else 0
        amount_paid = student_bill.amount_paid if student_bill else 0
        amount_paid_percentage = (amount_paid / total_amount * 100) if total_amount > 0 else 0

        if amount_paid > total_amount:
            payment_status = "Cleared"
            balance = amount_paid - total_amount 
            balance_label = "CR"
        elif amount_paid < total_amount:
            payment_status = "Defaulter"
            balance = total_amount - amount_paid 
            balance_label = "DR"
        else:
            payment_status = "Balanced"
            balance = 0
            balance_label = ""

        student_fees_data.append({
            "student": student,
            "academic_class": student.current_class if hasattr(student, 'current_class') else "N/A",
            "academic_year": academic_year,
            "term": term,
            "total_amount": total_amount,
            "amount_paid": amount_paid,
            "amount_paid_percentage": amount_paid_percentage,
            "payment_status": payment_status,
            "balance": balance, 
            "balance_label": balance_label,
            "bill_id": student_bill.id if student_bill else None,
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

    context = {
        "academic_classes": academic_classes,
        "terms": terms,
        "class_filter": int(selected_academic_class) if selected_academic_class else "",
        "term_filter": int(selected_term) if selected_term else "",
        "student_fees_data": student_fees_data,
    }

    return render(request, "fees/student_fees_status.html", context)

