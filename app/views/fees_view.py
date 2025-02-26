from django.shortcuts import render, redirect, HttpResponseRedirect
from django.contrib import messages
from django.urls import reverse
from app.selectors.model_selectors import *
from app.constants import *
from app.selectors.fees_selectors import * 
from app.forms.fees_payment import * 
from django.contrib.auth.decorators import login_required


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
    student_bill = get_student_bill(id)

    if student_bill.total_amount > 0:
        
        amount_paid_percentage = (student_bill.amount_paid / student_bill.total_amount) * 100
    else:
        amount_paid_percentage = 0

    
    if student_bill.amount_paid > student_bill.total_amount:
        payment_status = "CR"  
        balance = student_bill.amount_paid - student_bill.total_amount
    elif student_bill.amount_paid < student_bill.total_amount:
        payment_status = "DR"  
        balance = student_bill.total_amount - student_bill.amount_paid
    else:
        payment_status = "Balanced"
        balance = 0

    bill_item_form = StudentBillItemForm(initial={"bill": student_bill})
    payment_form = PaymentForm(initial={"bill": student_bill})

    context = {
        "student_bill": student_bill,
        "bill_item_form": bill_item_form,
        "payment_form": payment_form,
        "amount_paid_percentage": amount_paid_percentage,
        "payment_status": payment_status,
        "balance": balance,
    }

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

