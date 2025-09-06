from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from app.models.classes import Term
from app.models.students import Student,ClassRegister
from app.models.fees_payment import StudentBill, StudentBillItem,BillItem,BillItem,ClassBill, Payment,StudentCredit
from app.models.classes import AcademicClass,AcademicClassStream, Class, Stream, Term
from app.models.staffs import Staff
from app.models.school_settings import AcademicYear
from app.selectors.classes import get_current_academic_class
from django.db.models.signals import post_save
from django.dispatch import receiver

 

@receiver(pre_save, sender=AcademicClass)
def track_fees_amount_change(sender, instance, **kwargs):
    """
    Track the original fees_amount before saving to detect changes
    """
    if instance.pk:  
        try:
            original = AcademicClass.objects.get(pk=instance.pk)
            instance._original_fees_amount = original.fees_amount
        except AcademicClass.DoesNotExist:
            pass


@receiver(post_save, sender=AcademicClass)
def create_class_bill(sender, instance, created, **kwargs):
    # Handle both creation and updates to fees_amount
    if created or hasattr(instance, '_original_fees_amount'):
        # Check if fees_amount has changed (for updates)
        fees_changed = False
        if hasattr(instance, '_original_fees_amount'):
            fees_changed = instance._original_fees_amount != instance.fees_amount
        else:
            fees_changed = True  # For new instances

        if created or fees_changed:
            bill_item, _ = BillItem.objects.get_or_create(
                item_name="School Fees",
                defaults={
                    "category": "Tuition",
                    "bill_duration": "Termly",
                    "description": "Mandatory school fees"
                }
            )

            # Update or create ClassBill
            class_bill, created = ClassBill.objects.get_or_create(
                academic_class=instance,
                bill_item=bill_item,
                defaults={"amount": instance.fees_amount}
            )

            # Update existing ClassBill amount
            if not created:
                class_bill.amount = instance.fees_amount
                class_bill.save()

            # Update all existing StudentBillItem for this class
            if not created:  # Only for updates, not new creations
                student_bills = StudentBill.objects.filter(academic_class=instance)
                for student_bill in student_bills:
                    student_bill_item, item_created = StudentBillItem.objects.get_or_create(
                        bill=student_bill,
                        bill_item=bill_item,
                        defaults={
                            'description': f'School Fees - {instance}',
                            'amount': instance.fees_amount
                        }
                    )
                    # Update existing StudentBillItem amount
                    if not item_created:
                        student_bill_item.amount = instance.fees_amount
                        student_bill_item.save()

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
    This includes maintaining their class/stream assignments and creating new bills.
    Enhanced to handle edge cases and provide better logging.
    """
    if instance.is_current and not created:
        

        # Ensure only one term is marked as current
        other_current_terms = Term.objects.filter(is_current=True).exclude(id=instance.id)
        if other_current_terms.exists():
    
            other_current_terms.update(is_current=False)

        # Get the previous term that was marked as current
        previous_term = Term.objects.filter(
            academic_year=instance.academic_year,
            is_current=False
        ).order_by('-end_date').first()

        if previous_term:
            

            # Get all students from the previous term
            students = Student.objects.filter(term=previous_term).select_related('current_class', 'stream')

            if students.exists():
                print(f"👥 Found {students.count()} students to move")

                moved_count = 0
                registered_count = 0
                bills_created_count = 0
                errors_count = 0

                with transaction.atomic():
                    for student in students:
                        try:
                            print(f"   ↳ Processing student: {student.student_name} (Class: {student.current_class}, Stream: {student.stream})")

                            # Move student to new term
                            old_term = student.term
                            student.term = instance
                            student.save()
                            moved_count += 1
                            print(f"   ✅ Moved {student.student_name} to Term {instance.term}")

                            # Get the correct AcademicClass for the new term
                            academic_class = get_current_academic_class(
                                instance.academic_year,
                                student.current_class,
                                instance
                            )

                            if academic_class:
                                print(f"   📚 Found AcademicClass: {academic_class}")

                                # Get the student's stream
                                stream = student.stream

                                # Find the class stream for the new term
                                class_stream = AcademicClassStream.objects.filter(
                                    academic_class=academic_class,
                                    stream=stream
                                ).first()

                                if class_stream:
                                    print(f"   🏫 Found ClassStream: {class_stream}")

                                    # Register student in the new class stream
                                    class_register, created = ClassRegister.objects.get_or_create(
                                        academic_class_stream=class_stream,
                                        student=student
                                    )

                                    if created:
                                        registered_count += 1
                                        print(f"   📝 Registered {student.student_name} in {class_stream}")
                                    else:
                                        print(f"   ℹ️  {student.student_name} already registered in {class_stream}")

                                    # Create new student bills for the new term
                                    # Get all class bills for this academic class
                                    class_bills = ClassBill.objects.filter(academic_class=academic_class)

                                    if class_bills.exists():
                                        print(f"   💰 Processing {class_bills.count()} class bills for {student.student_name}")

                                        for class_bill in class_bills:
                                            # Check if student bill already exists for this bill item
                                            existing_student_bill = StudentBillItem.objects.filter(
                                                bill__student=student,
                                                bill__academic_class=academic_class,
                                                bill_item=class_bill.bill_item
                                            ).exists()

                                            if not existing_student_bill:
                                                # Create student bill if it doesn't exist
                                                student_bill, bill_created = StudentBill.objects.get_or_create(
                                                    student=student,
                                                    academic_class=academic_class,
                                                    defaults={'status': 'Unpaid'}
                                                )

                                                # Create student bill item
                                                bill_item, item_created = StudentBillItem.objects.get_or_create(
                                                    bill=student_bill,
                                                    bill_item=class_bill.bill_item,
                                                    defaults={
                                                        'description': class_bill.bill_item.description,
                                                        'amount': class_bill.amount
                                                    }
                                                )

                                                if bill_created or item_created:
                                                    bills_created_count += 1
                                                    print(f"   🧾 Created bill item: {class_bill.bill_item.item_name} for {student.student_name}")
                                            else:
                                                print(f"   ℹ️  Bill item {class_bill.bill_item.item_name} already exists for {student.student_name}")

                                        # Carry forward unused credits from previous term
                                        # Get all previous bills for this student in the current academic year
                                        previous_term_bills = StudentBill.objects.filter(
                                            student=student,
                                            academic_class__academic_year=instance.academic_year
                                        ).exclude(academic_class__term=instance)  # Exclude current term bills

                                        print(f"   🔍 Found {previous_term_bills.count()} previous bills for {student.student_name}")

                                        for prev_bill in previous_term_bills:
                                            # Get unused credits from previous bills
                                            unused_credits = StudentCredit.objects.filter(
                                                student=student,
                                                original_bill=prev_bill,
                                                is_applied=False
                                            )

                                            print(f"   💰 Found {unused_credits.count()} unused credits for bill #{prev_bill.id}")

                                            for credit in unused_credits:
                                                # Check if this credit was already carried forward
                                                existing_carry_forward = StudentCredit.objects.filter(
                                                    student=student,
                                                    description__icontains=f'Carried forward from {previous_term.term}',
                                                    original_bill=credit.original_bill,
                                                    is_applied=False
                                                ).exists()

                                                if not existing_carry_forward:
                                                    # Create a new credit record for the new term
                                                    StudentCredit.objects.create(
                                                        student=student,
                                                        amount=credit.amount,
                                                        description=f'Carried forward from {previous_term.term}: {credit.description}',
                                                        original_bill=credit.original_bill,
                                                        applied_to_bill=None,  # Not applied yet
                                                        is_applied=False
                                                    )
                                                    print(f"   ✅ Carried forward UGX {credit.amount} credit for {student.student_name}")
                                                else:
                                                    print(f"   ℹ️  Credit already carried forward for {student.student_name}")
                                    else:
                                        print(f"   ⚠️  No class bills found for AcademicClass {academic_class}")
                                else:
                                    print(f"   ❌ No ClassStream found for AcademicClass {academic_class} and Stream {stream}")
                                    # Try to create the class stream if it doesn't exist
                                    try:
                                        class_stream = AcademicClassStream.objects.create(
                                            academic_class=academic_class,
                                            stream=stream,
                                            class_teacher=None  # Will be assigned later
                                        )
                                        print(f"   🆕 Created missing ClassStream: {class_stream}")

                                        # Now register the student
                                        class_register, created = ClassRegister.objects.get_or_create(
                                            academic_class_stream=class_stream,
                                            student=student
                                        )
                                        if created:
                                            registered_count += 1
                                            print(f"   📝 Registered {student.student_name} in newly created {class_stream}")
                                    except Exception as e:
                                        print(f"   ❌ Failed to create ClassStream: {str(e)}")
                            else:
                                print(f"   ❌ No AcademicClass found for Year {instance.academic_year}, Class {student.current_class}, Term {instance}")
                                # Try to create the academic class if it doesn't exist
                                try:
                                    academic_class = AcademicClass.objects.create(
                                        academic_year=instance.academic_year,
                                        Class=student.current_class,
                                        term=instance,
                                        section=student.current_class.section,
                                        fees_amount=0  # Default, can be updated later
                                    )
                                    print(f"   🆕 Created missing AcademicClass: {academic_class}")

                                    # Now create the class stream
                                    class_stream = AcademicClassStream.objects.create(
                                        academic_class=academic_class,
                                        stream=student.stream,
                                        class_teacher=None
                                    )
                                    print(f"   🆕 Created ClassStream: {class_stream}")

                                    # Register the student
                                    class_register, created = ClassRegister.objects.get_or_create(
                                        academic_class_stream=class_stream,
                                        student=student
                                    )
                                    if created:
                                        registered_count += 1
                                        print(f"   📝 Registered {student.student_name} in {class_stream}")
                                except Exception as e:
                                    print(f"   ❌ Failed to create AcademicClass: {str(e)}")

                        except Exception as e:
                            # Log error but continue with other students
                            print(f"   ❌ Error moving student {student.student_name}: {str(e)}")
                            errors_count += 1
                            continue

                # Summary message
                print(f"\n✅ Term Transition Complete:")
                print(f"   • Moved {moved_count} students from Term {previous_term.term} to Term {instance.term}")
                print(f"   • Registered {registered_count} students in new class streams")
                print(f"   • Created {bills_created_count} new student bills")
                if errors_count > 0:
                    print(f"   • Errors encountered: {errors_count}")
            else:
                print(f"ℹ️  No students found in Term {previous_term.term} to move.")
        else:
            print("ℹ️  No previous term found to move students from.")
            # If this is the first term or no previous terms exist, just log it
            print(f"ℹ️  This appears to be the first term (Term {instance.term}) in the academic year.")


@receiver(post_save, sender=Term)
def auto_create_academic_classes(sender, instance, created, **kwargs):
    """
    Automatically create AcademicClass records when a new Term is created
    """
    if created:
        # Get all classes
        classes = Class.objects.all()
        academic_year = instance.academic_year

        for class_obj in classes:
            # Check if AcademicClass already exists
            if not AcademicClass.objects.filter(
                academic_year=academic_year,
                Class=class_obj,
                term=instance
            ).exists():
                # Create AcademicClass with default fee amount
                AcademicClass.objects.create(
                    academic_year=academic_year,
                    Class=class_obj,
                    term=instance,
                    section=class_obj.section,
                    fees_amount=0  # Default, can be updated later
                )


@receiver(post_save, sender=AcademicClass)
def auto_create_academic_class_streams(sender, instance, created, **kwargs):
    """
    Automatically create AcademicClassStream records when a new AcademicClass is created
    """
    if created:
        # Get all streams
        streams = Stream.objects.all()

        for stream in streams:
            # Check if AcademicClassStream already exists
            if not AcademicClassStream.objects.filter(
                academic_class=instance,
                stream=stream
            ).exists():
                # Try to find a suitable class teacher
                # First, look for existing teachers in the same class
                existing_teacher = None
                existing_streams = AcademicClassStream.objects.filter(
                    academic_class__Class=instance.Class,
                    academic_class__academic_year=instance.academic_year
                ).exclude(class_teacher__isnull=True)

                if existing_streams.exists():
                    # Use the same teacher from previous terms
                    existing_teacher = existing_streams.first().class_teacher

                # If no existing teacher, use any available staff
                if not existing_teacher:
                    available_staff = Staff.objects.all()
                    if available_staff.exists():
                        existing_teacher = available_staff.first()

                # Create AcademicClassStream
                AcademicClassStream.objects.create(
                    academic_class=instance,
                    stream=stream,
                    class_teacher=existing_teacher
                )


@receiver([post_save, post_delete], sender=Payment)
def update_bill_status_on_payment(sender, instance, **kwargs):
    """
    Automatically update StudentBill status when payments are added, updated, or deleted
    """
    bill = instance.bill

    # Refresh the bill from database to get updated payment calculations
    bill.refresh_from_db()

    # Update status based on payment status
    if bill.balance <= 0:
        bill.status = 'Paid'
    elif bill.amount_paid > 0:
        bill.status = 'Unpaid'  # Partial payment
    else:
        bill.status = 'Unpaid'

    bill.save(update_fields=['status'])


@receiver([post_save, post_delete], sender=Payment)
def handle_overpayment_credit(sender, instance, **kwargs):
    """
    Automatically detect overpayments and create credit records
    """
    bill = instance.bill

    # Refresh the bill from database to get updated payment calculations
    bill.refresh_from_db()

    # Check if there's an overpayment (amount paid > total amount)
    if bill.amount_paid > bill.total_amount:
        overpayment_amount = bill.amount_paid - bill.total_amount

        # Check if credit already exists for this overpayment
        existing_credit = StudentCredit.objects.filter(
            student=bill.student,
            original_bill=bill,
            description__icontains='overpayment',
            is_applied=False
        ).first()

        if not existing_credit:
            # Create credit for overpayment
            StudentCredit.objects.create(
                student=bill.student,
                amount=overpayment_amount,
                description=f'Overpayment credit from bill #{bill.id}',
                original_bill=bill,
                is_applied=False
            )
            print(f"💰 Created overpayment credit of UGX {overpayment_amount} for {bill.student.student_name}")
        else:
            # Update existing credit if amount changed
            if existing_credit.amount != overpayment_amount:
                existing_credit.amount = overpayment_amount
                existing_credit.save()
                print(f"💰 Updated overpayment credit to UGX {overpayment_amount} for {bill.student.student_name}")


@receiver(post_save, sender=StudentBill)
def apply_available_credits(sender, instance, created, **kwargs):
    """
    Automatically apply available credits to new bills
    """
    if created and instance.balance > 0:
        # Get available credits for this student
        available_credits = instance.available_credits

        if available_credits > 0:
            # Apply credits to reduce the bill balance
            credit_applied = instance.apply_credit(instance.balance)

            if credit_applied > 0:
                print(f"💳 Applied UGX {credit_applied} credit to bill #{instance.id} for {instance.student.student_name}")

                # Update bill status after applying credit
                instance.refresh_from_db()
                if instance.balance <= 0:
                    instance.status = 'Paid'
                    instance.save(update_fields=['status'])


@receiver(post_save, sender=Payment)
def update_bill_after_payment(sender, instance, created, **kwargs):
    """
    Additional check to ensure bill is updated after any payment
    """
    if created:
        bill = instance.bill
        bill.refresh_from_db()

        # Force recalculation of balance and status
        if bill.balance <= 0:
            bill.status = 'Paid'
        elif bill.amount_paid > 0:
            bill.status = 'Unpaid'  # Partial payment
        else:
            bill.status = 'Unpaid'

        bill.save(update_fields=['status'])
        print(f"💰 Payment processed for bill #{bill.id}, balance: UGX {bill.balance}")

