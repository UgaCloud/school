import json
from django.shortcuts import render, redirect
from django.contrib import messages
from app.models.timetables import  TimeSlot, Timetable, Classroom, WeekDay
from django.contrib.auth.decorators import login_required
from app.models.accounts import StaffAccount
from app.models.subjects import Subject
from app.models.staffs import Staff
from app.models.classes import ClassSubjectAllocation,AcademicClassStream, AcademicClass, Term
from app.models.school_settings import AcademicYear
from collections import defaultdict
from django.db.models import Q



@login_required
def timetable_center(request):
    # Limit streams to current academic year and term to avoid visually duplicated labels across years/terms.
    class_streams = (
        AcademicClassStream.objects
        .select_related('academic_class__Class', 'academic_class__academic_year', 'academic_class__term', 'stream')
        .filter(
            academic_class__academic_year__is_current=True,
            academic_class__term__is_current=True
        )
        .order_by('academic_class__Class__name', 'stream__stream')
        .distinct()
    )
    time_slots = TimeSlot.objects.all()
    selected_class_id = request.GET.get('class_stream_id')
    selected_class = None
    timetable_data = {}

    if selected_class_id:
        selected_class = AcademicClassStream.objects.get(pk=selected_class_id)
        timetable_entries = Timetable.objects.filter(class_stream=selected_class).select_related('time_slot', 'subject', 'teacher', 'classroom')
        # Build nested dict for template access: timetable_data[weekday][slot_id] = entry
        nested = defaultdict(dict)
        for entry in timetable_entries:
            nested[entry.weekday][entry.time_slot.id] = entry
        timetable_data = nested

    if request.method == 'POST':
        action = request.POST.get('action')
        selected_class_id = request.POST.get('class_stream_id')
        selected_class = AcademicClassStream.objects.get(pk=selected_class_id)

        if action == 'copy_previous':
            # Current context
            curr_ac = selected_class.academic_class
            curr_term_code = curr_ac.term.term  # "1" | "2" | "3"
            curr_year_pk = curr_ac.academic_year.pk

            # Find the most recent earlier AcademicClass for the same base Class
            # Earlier means: any prior year, or same year with a lower term number.
            earlier_ac_qs = (
                AcademicClass.objects
                .filter(Class=curr_ac.Class)
                .filter(
                    Q(academic_year__pk__lt=curr_year_pk) |
                    Q(academic_year__pk=curr_year_pk, term__term__lt=curr_term_code)
                )
                .order_by('-academic_year__pk', '-term__term')
            )

            source_stream = None
            source_ac = None

            # Strategy: choose the first earlier stream that actually has timetable entries.
            for ac in earlier_ac_qs:
                cand_stream = AcademicClassStream.objects.filter(
                    academic_class=ac,
                    stream=selected_class.stream
                ).first()
                if not cand_stream:
                    continue
                if Timetable.objects.filter(class_stream=cand_stream).exists():
                    source_stream = cand_stream
                    source_ac = ac
                    break

            # If none of the earlier streams have entries, fall back to the immediate previous AcademicClass (if any)
            if source_stream is None:
                source_ac = earlier_ac_qs.first()
                if source_ac:
                    source_stream = AcademicClassStream.objects.filter(
                        academic_class=source_ac,
                        stream=selected_class.stream
                    ).first()

            # If still nothing found, inform and exit
            if not source_stream:
                messages.warning(request, "No previous class stream found to copy from for this Class/Stream.")
                return redirect(f"{request.path}?class_stream_id={selected_class_id}")

            prev_entries = (
                Timetable.objects
                .filter(class_stream=source_stream)
                .select_related('time_slot', 'subject', 'teacher', 'classroom')
            )

            if not prev_entries:
                messages.warning(request, "No timetable entries found in previous terms for this stream to copy.")
                return redirect(f"{request.path}?class_stream_id={selected_class_id}")

            created_or_updated = 0
            skipped_teacher = 0
            skipped_room = 0

            for e in prev_entries:
                defaults = {
                    'subject': e.subject,
                    'teacher': e.teacher,
                    'classroom': e.classroom,
                }

                # Avoid teacher conflicts across other class streams at same weekday+slot
                if e.teacher_id:
                    teacher_in_use = (
                        Timetable.objects
                        .filter(teacher=e.teacher, weekday=e.weekday, time_slot=e.time_slot)
                        .exclude(class_stream=selected_class)
                        .exists()
                    )
                    if teacher_in_use:
                        defaults['teacher'] = None
                        skipped_teacher += 1

                # Avoid classroom conflicts across other class streams at same weekday+slot
                if e.classroom_id:
                    room_in_use = (
                        Timetable.objects
                        .filter(classroom=e.classroom, weekday=e.weekday, time_slot=e.time_slot)
                        .exclude(class_stream=selected_class)
                        .exists()
                    )
                    if room_in_use:
                        defaults['classroom'] = None
                        skipped_room += 1

                Timetable.objects.update_or_create(
                    class_stream=selected_class,
                    weekday=e.weekday,
                    time_slot=e.time_slot,
                    defaults=defaults
                )
                created_or_updated += 1

            msg = f"Copied {created_or_updated} timetable entries from the most recent previous term."
            if skipped_teacher or skipped_room:
                parts = []
                if skipped_teacher:
                    parts.append(f"{skipped_teacher} teacher conflict(s) cleared")
                if skipped_room:
                    parts.append(f"{skipped_room} room conflict(s) cleared")
                msg += " (" + ", ".join(parts) + ")."
            messages.success(request, msg)
            return redirect(f"{request.path}?class_stream_id={selected_class_id}")

        # Default: save timetable from JSON payload
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
