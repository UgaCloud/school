from app.models.fees_payment import *

def get_student_bills():
    return StudentBill.objects.all()

def get_student_bill(id):
    return StudentBill.objects.get(pk=id)

def get_academic_class_bills(academic_class):
    return StudentBill.objects.filter(academic_class=academic_class)

def get_academic_class_bill_item(academic_class):
    academic_class_bills = get_academic_class_bills(academic_class)
    
    bill_item = StudentBillItem.objects.filter(bill__in = academic_class_bills)
    
    return bill_item

def get_bill_items():
    return BillItem.objects.all()

def get_bill_item(id):
    return BillItem.objects.get(pk=id)

def get_bill_item_by_name(item_name):
    return BillItem.objects.get(item_name=item_name)