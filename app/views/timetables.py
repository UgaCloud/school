import json
from django.shortcuts import render, redirect
from django.contrib import messages
from app.models.timetables import  TimeSlot, Timetable, Classroom, WeekDay
from django.contrib.auth.decorators import login_required
from app.models.accounts import StaffAccount
from app.models.subjects import Subject
from app.models.staffs import Staff
from app.models.classes import ClassSubjectAllocation,AcademicClassStream
from collections import defaultdict
from django.db.models import Q



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

            # Convert label (e.g., "Monday") to short code (e.g., "MON")
            weekday_map = {label: code for code, label in WeekDay.choices}

            for weekday_label, slots in timetable_data.items():
                weekday_code = weekday_map.get(weekday_label, weekday_label)

                for time_slot_id, entry in slots.items():
                    subject_id = entry.get('subject')
                    teacher_id = entry.get('teacher')
                    classroom_id = entry.get('classroom')

                    if subject_id and teacher_id:
                        time_slot = TimeSlot.objects.get(pk=time_slot_id)
                        Timetable.objects.update_or_create(
                            class_stream=selected_class,
                            weekday=weekday_code,
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

def get_time_slots():
    """Utility function to get all time slots in order"""
    return TimeSlot.objects.order_by('start_time').all()


@login_required
def teacher_timetable_view(request):
    user = request.user
    try:
        staff_account = user.staff_account
    except AttributeError:
        messages.error(request, "You are not linked to a staff account.")
        return redirect("dashboard")

    if not hasattr(staff_account, 'staff') or staff_account.role.name != "Teacher":
        messages.error(request, "Access denied.")
        return redirect("dashboard")

    staff = staff_account.staff

    # Get allocations for this teacher
    allocations = ClassSubjectAllocation.objects.filter(subject_teacher=staff).select_related("academic_class_stream", "subject")
    subjects = sorted({a.subject for a in allocations}, key=lambda x: x.name)
    class_streams = sorted({a.academic_class_stream for a in allocations}, key=lambda x: str(x))

    # Filters from query params
    selected_weekday = request.GET.get("weekday")
    selected_subject = request.GET.get("subject")
    selected_stream = request.GET.get("stream")

    timetable_filter = Q(teacher=staff)
    if selected_weekday:
        timetable_filter &= Q(weekday=selected_weekday)
    if selected_subject:
        timetable_filter &= Q(subject_id=selected_subject)
    if selected_stream:
        timetable_filter &= Q(class_stream_id=selected_stream)

    timetable_entries = Timetable.objects.filter(timetable_filter).select_related(
        'class_stream', 'subject', 'time_slot', 'classroom'
    ).order_by('weekday', 'time_slot__start_time')

    time_slots = get_time_slots()
    timetable_data = {
        day[0]: {slot.id: [] for slot in time_slots} for day in WeekDay.choices
    }

    for entry in timetable_entries:
        timetable_data[entry.weekday][entry.time_slot.id].append(entry)

    context = {
        "timetable_data": timetable_data,
        "time_slots": time_slots,
        "weekdays": WeekDay.choices,
        "teacher": staff,
        "subjects": subjects,
        "class_streams": class_streams,
        "selected_weekday": selected_weekday,
        "selected_subject": selected_subject,
        "selected_stream": selected_stream,
    }

    return render(request, "timetable/teacher_timetable.html", context)
