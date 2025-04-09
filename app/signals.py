from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from app.models.classes import Term
from app.models.students import Student,ClassRegister
from app.models.fees_payment import StudentBill, StudentBillItem,BillItem,BillItem,ClassBill
from app.models.classes import AcademicClass,AcademicClassStream
from app.selectors.classes import get_current_academic_class

 

@receiver(post_save, sender=AcademicClass)
def create_class_bill(sender, instance, created, **kwargs):
    if created:
        bill_item, _ = BillItem.objects.get_or_create(
            item_name="School Fees",
            defaults={
                "category": "Tuition", 
                "bill_duration": "Termly", 
                "description": "Mandatory school fees"
            }
        )

        ClassBill.objects.get_or_create(
            academic_class=instance,
            bill_item=bill_item,
            defaults={"amount": instance.fees_amount}
        )

@receiver(post_save, sender=Student)
def create_student_bill(sender, instance, created, **kwargs):
    if created:
        academic_class = instance.current_class 
        if isinstance(academic_class, str):
            try:
                academic_class = AcademicClass.objects.get(code=academic_class)  
            
            except AcademicClass.DoesNotExist:
                
                return 

        # Ensure academic_class is valid before proceeding
        if not isinstance(academic_class, AcademicClass):
            
            return

        student_bill, _ = StudentBill.objects.get_or_create(
            student=instance,
            academic_class=academic_class,  
            status="Unpaid"
        )

        class_bills = ClassBill.objects.filter(academic_class=academic_class)

        for class_bill in class_bills:
            if not StudentBillItem.objects.filter(
                bill=student_bill,
                bill_item=class_bill.bill_item
            ).exists():
                StudentBillItem.objects.create(
                    bill=student_bill,
                    bill_item=class_bill.bill_item,
                    description=class_bill.bill_item.description,
                    amount=class_bill.amount
                )

        

@receiver(post_save, sender=Term)
def move_students_on_term_change(sender, instance, created, **kwargs):
    """
    Automatically move students to the new current term when a term is marked as current.
    """
    if instance.is_current and not created:
        # Ensure only one term is marked as current
        Term.objects.exclude(id=instance.id).update(is_current=False)
        
        # Get the previous term that was marked as current
        previous_term = Term.objects.filter(is_current=False).order_by('-end_date').first()

        if previous_term:
            students = Student.objects.filter(term=previous_term)

            with transaction.atomic():
                for student in students:
                    # Move student to new term
                    student.term = instance
                    student.save()

                    # Get the correct AcademicClass for the new term
                    academic_class = get_current_academic_class(instance.academic_year, student.current_class, instance)
                    
                    # Get the stream
                    stream = student.stream
                    
                    # Find or create the class stream
                    class_stream = AcademicClassStream.objects.filter(academic_class=academic_class, stream=stream).first()
                    
                    if class_stream:
                        # Update or create Class Register entry
                        class_register, created = ClassRegister.objects.get_or_create(
                            academic_class_stream=class_stream, student=student
                        )

                        if created:
                            print(f"Registered {student.student_name} in {class_stream} for Term {instance.term}.")
                        else:
                            print(f"{student.student_name} was already registered in {class_stream}.")

            print(f"Moved and registered {students.count()} students from Term {previous_term.term} to Term {instance.term}.")
        else:
            print("No previous term found to move students from.")

