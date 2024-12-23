from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from app.models import Term, Student

@receiver(post_save, sender=Term)
def move_students_on_term_change(sender, instance, created, **kwargs):
    """
    Automatically move students to the new current term when a term is marked as current.
    """
    # Check if the term is marked as current and it wasn't just created
    if instance.is_current and not created:
        # Ensure that only one term is marked as current
        Term.objects.exclude(id=instance.id).update(is_current=False)
        
        # Get the previous term that was marked as current
        previous_term = Term.objects.filter(is_current=False).order_by('-end_date').first()

        if previous_term:
            # Get all students who are currently in the previous term
            students = Student.objects.filter(term=previous_term)
            
            # Use a transaction to ensure consistency
            with transaction.atomic():
                # Loop through each student and move them to the current term
                for student in students:
                    student.term = instance
                    student.save()

            # Log the result
            print(f"Moved {students.count()} students from Term {previous_term.term} to Term {instance.term}.")
        else:
            print("No previous term found to move students from.")
