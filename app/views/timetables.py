import json
from django.shortcuts import render, redirect
from django.contrib import messages
from app.models import AcademicClassStream, TimeSlot, Timetable, Subject, Staff, Classroom, WeekDay
from django.contrib.auth.decorators import login_required
from app.models.accounts import StaffAccount
from app.models.classes import ClassSubjectAllocation

@login_required
def timetable_center(request):
    class_streams = AcademicClassStream.objects.all()
    time_slots = TimeSlot.objects.all()
    selected_class_id = request.GET.get('class_stream_id')
    selected_class = None
    timetable_data = {}
    
    if selected_class_id:
        selected_class = AcademicClassStream.objects.get(pk=selected_class_id)
        timetable_entries = Timetable.objects.filter(class_stream=selected_class)
        for entry in timetable_entries:
            timetable_data[(entry.weekday, entry.time_slot.id)] = entry

    if request.method == 'POST':
        selected_class_id = request.POST.get('class_stream_id')
        selected_class = AcademicClassStream.objects.get(pk=selected_class_id)
        timetable_json = request.POST.get('timetable_json')

        if timetable_json:
            timetable_data = json.loads(timetable_json)
            for weekday, slots in timetable_data.items():
                for time_slot_id, entry in slots.items():
                    subject_id = entry.get('subject')
                    teacher_id = entry.get('teacher')
                    classroom_id = entry.get('classroom')

                    if subject_id and teacher_id:
                        time_slot = TimeSlot.objects.get(pk=time_slot_id)
                        Timetable.objects.update_or_create(
                            class_stream=selected_class,
                            weekday=weekday,
                            time_slot=time_slot,
                            defaults={
                                'subject_id': subject_id,
                                'teacher_id': teacher_id,
                                'classroom_id': classroom_id or None,
                            }
                        )
            messages.success(request, "Timetable updated successfully.")
            return redirect(f"{request.path}?class_stream_id={selected_class_id}")
    
    context = {
        "class_streams": class_streams,
        "selected_class": selected_class,
        "time_slots": time_slots,
        "timetable_data": timetable_data,
        "subjects": Subject.objects.all(),
        "teachers": Staff.objects.all(),
        "classrooms": Classroom.objects.all(),
        "weekdays": WeekDay.choices,
    }
    return render(request, "timetable/timetable_center.html", context)


@login_required
def teacher_timetable_view(request):
    user = request.user

    try:
        staff_account = user.staff_account
    except StaffAccount.DoesNotExist:
        messages.error(request, "You are not linked to a staff account.")
        return redirect("dashboard")  # or wherever appropriate

    if staff_account.role.name != "Teacher":
        messages.error(request, "Access denied. This page is for teachers only.")
        return redirect("dashboard")

    staff = staff_account.staff

    # Get class-subject allocations for this teacher
    assigned_classes = ClassSubjectAllocation.objects.filter(subject_teacher=staff)

    # Build a list of class_streams and subjects the teacher is assigned to
    stream_subject_pairs = [
        (alloc.academic_class_stream, alloc.subject) for alloc in assigned_classes
    ]

    # Get timetable entries for those classes and subjects
    timetable_entries = Timetable.objects.select_related(
        'class_stream', 'subject', 'teacher', 'time_slot', 'classroom'
    ).filter(
        teacher=staff
    ).order_by('weekday', 'time_slot__start_time')

    context = {
        "timetable_entries": timetable_entries,
        "teacher": staff,
    }

    return render(request, "timetable/teacher_timetable.html", context)