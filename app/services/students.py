import csv
from datetime import datetime
from app.selectors.school_settings import get_current_academic_year
from app.selectors.classes import get_current_academic_class, get_academic_class_stream, get_class_by_code, get_stream_by_name, get_current_term
import app.selectors.fees_selectors as fees_selectors
from django.contrib import messages
from app.models.students import Student, ClassRegister, StudentRegistrationCSV
from app.models.fees_payment import StudentBill, StudentBillItem,ClassBill
from app.models.classes import *


def register_student(student, _class, stream):
    if isinstance(_class, str):  
        _class = get_class_by_code(_class)  
    current_academic_year = get_current_academic_year()
    term = get_current_term()
    academic_class = get_current_academic_class(current_academic_year, _class, term)
    class_stream = get_academic_class_stream(academic_class, stream)
    class_register = ClassRegister(academic_class_stream=class_stream, student=student)
    class_register.save()
    create_student_bill(student, academic_class)
    return class_register


def bulk_student_registration(csv_obj):
    with open(csv_obj.file_name.path, 'r') as f:
        reader = csv.reader(f)

        for i, row in enumerate(reader):
            if i >= 2:  # Ignore first 2 rows
                reg_no = row[0]
                student_name = row[1]
                gender = row[2]
                birthdate = row[3]  
                nationality = row[4]
                religion = row[5]
                address = row[6]
                guardian = row[7]
                relationship = row[8]
                contact = row[9]
                year = row[10]
                class_code = row[11]
                stream_name = row[12]
                term_id = row[13]

           
                existing_student = Student.objects.filter(reg_no=reg_no).first()
                if existing_student:
                    raise ValueError(f"Student with Reg No {reg_no} already exists. Skipping row {i+1}.")

                try:
                    term_id = int(term_id)
                    term = Term.objects.get(id=term_id)
                except (ValueError, Term.DoesNotExist):
                    raise ValueError(f"Invalid term ID '{row[13]}' in row {i+1}.")

                try:
                    birthdate = datetime.strptime(birthdate, "%m/%d/%Y").date()  
                except ValueError:
                    raise ValueError(f"Invalid birthdate format in row {i+1}. Expected format: YYYY-MM-DD.")

                academic_year = get_current_academic_year()
                current_class = get_class_by_code(class_code)  
                stream = get_stream_by_name(stream_name)

                academic_class = get_current_academic_class(academic_year, current_class, term)

                class_stream_exists = AcademicClassStream.objects.filter(
                    academic_class=academic_class, stream=stream
                ).exists()

                if not class_stream_exists:
                    raise ValueError(f"No academic class stream found for {class_code} and {stream_name} in row {i+1}. Registration aborted.")

                student = Student(
                    reg_no=reg_no, 
                    student_name=student_name, 
                    gender=gender,
                    birthdate=birthdate, 
                    nationality=nationality,
                    religion=religion, 
                    address=address,
                    guardian=guardian, 
                    relationship=relationship,
                    contact=contact, 
                    academic_year=academic_year,
                    current_class=current_class, 
                    stream=stream,
                    term=term
                )
                student.save()

                register_student(student, current_class, stream) 




def delete_all_csv_files():
    StudentRegistrationCSV.objects.all().delete()
        
def create_student_bill(student, academic_class):
    """
    Creates a StudentBill and assigns all Class Bills (including school fees).
    """
    
    student_bill, _ = StudentBill.objects.get_or_create(
        student=student,
        academic_class=academic_class,
        status="Unpaid"
    )

    school_fees_description = f"School Fees for {academic_class.term} - {academic_class.academic_year}"
    school_fees_bill_item = create_bill_Item(
        student_bill, school_fees_description, academic_class.fees_amount
    )

    school_fees_bill_item.save()
    # Get all additional Class Bills for this academic class
    class_bills = ClassBill.objects.filter(academic_class=academic_class)

    for class_bill in class_bills:
        if not StudentBillItem.objects.filter(
            bill=student_bill, bill_item=class_bill.bill_item
        ).exists():
            StudentBillItem.objects.create(
                bill=student_bill,
                bill_item=class_bill.bill_item,
                description=class_bill.bill_item.description,
                amount=class_bill.amount
            )
    return student_bill

    
def create_bill_Item(bill, description, amount, bill_item=None):
    if bill_item == None:
        bill_item = fees_selectors.get_bill_item_by_name("School Fees")
    
    bill_item = StudentBillItem(bill=bill, bill_item=bill_item, description=description, amount=amount)
    
    bill_item.save()
    
    return bill_item
    
def create_class_bill_item(academic_class, bill_item, amount):
    class_bills = fees_selectors.get_academic_class_bills(academic_class)
    bill_item = fees_selectors.get_bill_item(bill_item)
    description = f"{bill_item.item_name} for {academic_class.Class} {academic_class.academic_year}"
    
    for bill in class_bills:
        create_bill_Item(bill, description, amount, bill_item)
        
    
   
    
    