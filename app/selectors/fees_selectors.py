from app.models.fees_payment import *

def get_student_bills():
    return StudentBill.objects.all()

def get_student_bill(id):
    return StudentBill.objects.get(pk=id)

def get_bill_items():
    return BillItem.objects.all()

def get_bill_item(id):
    return BillItem.objects.get(pk=id)