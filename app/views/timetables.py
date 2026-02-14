import json
from django.shortcuts import render, redirect
from django.contrib import messages
from app.models.timetables import  TimeSlot, Timetable, Classroom, WeekDay, BreakPeriod
from django.contrib.auth.decorators import login_required
from app.models.accounts import StaffAccount
from app.models.subjects import Subject
from app.models.staffs import Staff
from app.models.classes import ClassSubjectAllocation,AcademicClassStream, AcademicClass, Term
from app.models.school_settings import AcademicYear, SchoolSetting
from app.forms.timetables import TimeSlotForm
from collections import defaultdict
from django.db.models import Q
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from django.utils import timezone



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
    time_slots = TimeSlot.objects.order_by('start_time', 'end_time', 'id')
    time_slot_form = TimeSlotForm()
    selected_class_id = request.GET.get('class_stream_id')
    selected_class = None
    timetable_data = {}

    break_map = {}
    if selected_class_id:
        selected_class = AcademicClassStream.objects.get(pk=selected_class_id)
        timetable_entries = Timetable.objects.filter(class_stream=selected_class).select_related('time_slot', 'subject', 'teacher', 'classroom')
        # Build nested dict for template access: timetable_data[weekday][slot_id] = entry
        nested = defaultdict(dict)
        for entry in timetable_entries:
            nested[entry.weekday][entry.time_slot.id] = entry
        timetable_data = nested

        break_qs = BreakPeriod.objects.select_related("time_slot").all()
        break_map = {f"{b.weekday}_{b.time_slot_id}": b for b in break_qs}
        break_any_slots = {b.time_slot_id: b for b in break_qs}
    else:
        break_any_slots = {}

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_time_slot':
            time_slot_form = TimeSlotForm(request.POST)
            if time_slot_form.is_valid():
                time_slot_form.save()
                messages.success(request, "Time slot added successfully.")
            else:
                messages.error(request, "Please correct the time slot form errors.")
            return redirect(request.path)

        if action == 'edit_time_slot':
            slot_id = request.POST.get('slot_id')
            slot = TimeSlot.objects.filter(pk=slot_id).first()
            if not slot:
                messages.error(request, "Time slot not found.")
                return redirect(request.path)
            edit_form = TimeSlotForm(request.POST, instance=slot)
            if edit_form.is_valid():
                edit_form.save()
                messages.success(request, "Time slot updated successfully.")
            else:
                messages.error(request, "Please correct the time slot form errors.")
            return redirect(request.path)

        if action == 'delete_time_slot':
            slot_id = request.POST.get('slot_id')
            slot = TimeSlot.objects.filter(pk=slot_id).first()
            if not slot:
                messages.error(request, "Time slot not found.")
                return redirect(request.path)
            if Timetable.objects.filter(time_slot=slot).exists():
                messages.error(request, "Cannot delete a time slot that is used in the timetable.")
                return redirect(request.path)
            slot.delete()
            messages.success(request, "Time slot deleted successfully.")
            return redirect(request.path)

        selected_class_id = request.POST.get('class_stream_id')
        selected_class = AcademicClassStream.objects.get(pk=selected_class_id)

        if action == 'print_pdf':
            timetable_entries = Timetable.objects.filter(
                class_stream=selected_class
            ).select_related('time_slot', 'subject', 'teacher', 'classroom')

            nested = defaultdict(dict)
            for entry in timetable_entries:
                nested[entry.weekday][entry.time_slot.id] = entry

            school = SchoolSetting.load()
            break_qs = BreakPeriod.objects.select_related("time_slot").all()
            break_map = {f"{b.weekday}_{b.time_slot_id}": b for b in break_qs}
            break_any_slots = {b.time_slot_id: b for b in break_qs}

            context = {
                "school": school,
                "class_stream": selected_class,
                "academic_year": getattr(selected_class.academic_class.academic_year, "academic_year", "-"),
                "term": getattr(selected_class.academic_class.term, "term", "-"),
                "time_slots": TimeSlot.objects.all(),
                "weekdays": WeekDay.choices,
                "timetable_data": nested,
                "break_map": break_map,
                "break_any_slots": break_any_slots,
                "generated_at": timezone.now(),
            }
            html = render_to_string("timetable/timetable_print.html", context)
            response = HttpResponse(content_type="application/pdf")
            response["Content-Disposition"] = "inline; filename=timetable.pdf"
            pisa_status = pisa.CreatePDF(html, dest=response)
            if pisa_status.err:
                return HttpResponse("PDF generation error", status=500)
            return response

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

        if action == 'auto_generate':
            time_slots = list(TimeSlot.objects.all())
            weekdays = [code for code, _ in WeekDay.choices]

            allocations = ClassSubjectAllocation.objects.filter(
                academic_class_stream=selected_class
            ).select_related('subject', 'subject_teacher')

            if not allocations.exists():
                messages.warning(request, "No subject allocations found for this class stream.")
                return redirect(f"{request.path}?class_stream_id={selected_class_id}")

            timetable_entries = []
            slot_index = 0

            total_slots = len(time_slots) * len(weekdays)
            if total_slots == 0:
                messages.error(request, "Please configure time slots before auto-generating the timetable.")
                return redirect(f"{request.path}?class_stream_id={selected_class_id}")

            for allocation in allocations:
                if slot_index >= total_slots:
                    messages.warning(request, "Not enough time slots to schedule all allocations.")
                    break

                day_index = slot_index // len(time_slots)
                time_index = slot_index % len(time_slots)
                weekday_code = weekdays[day_index]
                time_slot = time_slots[time_index]

                # Skip conflicts for teacher/classroom by finding next free slot
                attempts = 0
                while attempts < total_slots:
                    conflict = Timetable.objects.filter(
                        Q(teacher=allocation.subject_teacher, weekday=weekday_code, time_slot=time_slot) |
                        Q(class_stream=selected_class, weekday=weekday_code, time_slot=time_slot)
                    ).exists()
                    if not conflict:
                        break
                    slot_index = (slot_index + 1) % total_slots
                    day_index = slot_index // len(time_slots)
                    time_index = slot_index % len(time_slots)
                    weekday_code = weekdays[day_index]
                    time_slot = time_slots[time_index]
                    attempts += 1

                Timetable.objects.update_or_create(
                    class_stream=selected_class,
                    weekday=weekday_code,
                    time_slot=time_slot,
                    defaults={
                        'subject': allocation.subject,
                        'teacher': allocation.subject_teacher,
                        'classroom': None,
                    }
                )
                slot_index += 1

            messages.success(request, "Timetable auto-generated from subject allocations.")
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

    staff_account = getattr(request.user, "staff_account", None)
    role_name = getattr(getattr(staff_account, "role", None), "name", "")
    role_name = str(role_name).lower()
    active_role = str(request.session.get("active_role_name") or "").lower()
    effective_role = active_role or role_name
    editable_roles = {"admin", "director of studies", "dos"}
    is_head_role = "head" in role_name
    hide_time_slots = is_head_role or (effective_role not in editable_roles)

    context = {
        "class_streams": class_streams,
        "selected_class": selected_class,
        "time_slots": time_slots,
        "time_slot_form": time_slot_form,
        "timetable_data": timetable_data,
        "break_map": break_map,
        "break_any_slots": break_any_slots,
        "subjects": Subject.objects.all(),
        "teachers": Staff.objects.all(),
        "classrooms": Classroom.objects.all(),
        "weekdays": WeekDay.choices,
        "hide_time_slots": hide_time_slots,
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

    if not hasattr(staff_account, 'staff'):
        messages.error(request, "Access denied.")
        return redirect("dashboard")

    staff = staff_account.staff
    role_names = []
    account_role = getattr(staff_account.role, "name", None)
    if account_role:
        role_names.append(account_role)
    try:
        role_names.extend(list(staff.roles.values_list("name", flat=True)))
    except Exception:
        pass
    role_names = [str(name).lower() for name in role_names if name]

    if not staff.is_academic_staff and not any("teacher" in name for name in role_names):
        messages.error(request, "Access denied.")
        return redirect("dashboard")

    # Get allocations for this teacher
    allocations = ClassSubjectAllocation.objects.filter(subject_teacher=staff).select_related("academic_class_stream", "subject")
    subjects = sorted({a.subject for a in allocations}, key=lambda x: x.name)
    class_streams = sorted({a.academic_class_stream for a in allocations}, key=lambda x: str(x))
    teacher_subject_ids = list(allocations.values_list("subject_id", flat=True).distinct())

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

    # Fallback: if no direct teacher matches exist, infer by subject allocations
    if not timetable_entries.exists() and teacher_subject_ids:
        inferred_filter = Q(subject_id__in=teacher_subject_ids)
        if selected_weekday:
            inferred_filter &= Q(weekday=selected_weekday)
        if selected_subject:
            inferred_filter &= Q(subject_id=selected_subject)
        if selected_stream:
            inferred_filter &= Q(class_stream_id=selected_stream)

        timetable_entries = Timetable.objects.filter(inferred_filter).select_related(
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


@login_required
def school_timetable_overview(request):
    time_slots = TimeSlot.objects.order_by('start_time', 'end_time')
    class_streams = (
        AcademicClassStream.objects
        .select_related('academic_class__Class', 'academic_class__academic_year', 'academic_class__term', 'stream')
        .order_by('academic_class__Class__name', 'stream__stream')
    )
    timetable_entries = Timetable.objects.select_related(
        'class_stream', 'time_slot', 'subject', 'teacher', 'classroom'
    )
    timetable_data = defaultdict(lambda: defaultdict(dict))
    for entry in timetable_entries:
        timetable_data[entry.class_stream_id][entry.weekday][entry.time_slot.id] = entry
    context = {
        "time_slots": time_slots,
        "class_streams": class_streams,
        "timetable_data": timetable_data,
        "weekdays": WeekDay.choices,
    }
    return render(request, "timetable/school_timetable.html", context)


@login_required
def class_timetable_overview(request):
    class_streams = (
        AcademicClassStream.objects
        .select_related('academic_class__Class', 'academic_class__academic_year', 'academic_class__term', 'stream')
        .order_by('academic_class__Class__name', 'stream__stream')
    )
    context = {
        "class_streams": class_streams,
    }
    return render(request, "timetable/class_timetable.html", context)


@login_required
def classrooms_overview(request):
    classrooms = Classroom.objects.order_by('name')
    context = {
        "classrooms": classrooms,
    }
    return render(request, "timetable/classrooms.html", context)
