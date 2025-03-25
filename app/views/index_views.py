from django.shortcuts import render, redirect, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from app.models.classes import Class
from app.models.staffs import Staff
from app.models.students import Student


@login_required
def index_view(request):
    total_staff = Staff.objects.count()
    total_males = Staff.objects.filter(gender='M').count()
    total_females = Staff.objects.filter(gender='F').count()

    total_students = Student.objects.count()
    total_male_students = Student.objects.filter(gender='M').count()
    total_female_students = Student.objects.filter(gender='F').count()


    male_percentage = (total_males / total_staff * 100) if total_staff > 0 else 0
    female_percentage = (total_females / total_staff * 100) if total_staff > 0 else 0

    male_students_percentage = (total_male_students / total_students * 100) if total_students > 0 else 0
    female_students_percentage = (total_female_students / total_students * 100) if total_students > 0 else 0

    context = {
        'total_staff': total_staff,
        'total_males': total_males,
        'total_females': total_females,
        'total_students': total_students,
        'total_male_students': total_male_students,
        'total_female_students': total_female_students,
        'male_percentage': round(male_percentage, 2),
        'female_percentage': round(female_percentage, 2),
        'male_students_percentage': round(male_students_percentage, 2),
        'female_students_percentage': round(female_students_percentage, 2),
    }

    return render(request, "index.html", context)
