import json
from datetime import datetime, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.db.models import Count, Q

from app.forms.attendance import AttendanceSessionForm
from app.models.attendance import AttendanceSession, AttendanceStatus, AttendanceRecord
from app.models.classes import AcademicClassStream, ClassSubjectAllocation
from app.models.timetables import Timetable
from app.models.school_settings import AcademicYear
from app.models.students import ClassRegister
from app.models.staffs import Staff
from app.models.students import Student
from app.models.subjects import Subject
from app.services.attendance import (
    get_or_create_session,
    initialize_session_records,
    save_attendance_records,
)


def _get_staff(request):
    staff_account = getattr(request.user, "staff_account", None)
    return getattr(staff_account, "staff", None)


@login_required
def attendance_dashboard(request):
    staff = _get_staff(request)
    if not staff:
        messages.error(request, "Access denied.")
        return redirect("dashboard")

    allocations = ClassSubjectAllocation.objects.filter(subject_teacher=staff).select_related(
        "academic_class_stream", "subject"
    )
    class_streams = sorted({a.academic_class_stream for a in allocations}, key=lambda x: str(x))
    subjects = sorted({a.subject for a in allocations}, key=lambda x: x.name)

    context = {
        "class_streams": class_streams,
        "subjects": subjects,
        "all_class_streams": AcademicClassStream.objects.all(),
    }
    return render(request, "attendance/attendance_dashboard.html", context)


@login_required
def take_attendance(request):
    staff = _get_staff(request)
    if not staff:
        messages.error(request, "Access denied.")
        return redirect("dashboard")

    allocations = ClassSubjectAllocation.objects.filter(subject_teacher=staff).select_related(
        "academic_class_stream", "subject"
    )
    class_streams = sorted({a.academic_class_stream for a in allocations}, key=lambda x: str(x))
    subjects = sorted({a.subject for a in allocations}, key=lambda x: x.name)

    class_stream_id = request.GET.get("class_stream") or request.POST.get("class_stream")
    subject_id = request.GET.get("subject") or request.POST.get("subject")
    
    # Clean up empty strings
    if class_stream_id == "":
        class_stream_id = None
    if subject_id == "":
        subject_id = None

    # Determine date and time_slot
    current_date = timezone.now().date()
    target_date = current_date
    target_time_slot = None

    # Map Python weekday (0=Mon) to WeekDay choices
    weekday_map = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
    today_weekday = weekday_map[target_date.weekday()]

    # Auto-detect time slot from timetable for this class/subject/weekday
    auto_time_slot = None
    if class_stream_id and subject_id:
        timetable_entry = Timetable.objects.filter(
            class_stream_id=class_stream_id,
            subject_id=subject_id,
            weekday=today_weekday,
        ).select_related('time_slot').first()
        if timetable_entry:
            auto_time_slot = timetable_entry.time_slot
            target_time_slot = auto_time_slot

    initial_data = {"date": current_date}
    if auto_time_slot:
        initial_data["time_slot"] = auto_time_slot.pk

    # Allow GET params to override auto-detected values
    if request.method == "GET":
        date_param = request.GET.get("date")
        if date_param:
            from django.utils.dateparse import parse_date
            parsed = parse_date(date_param)
            if parsed:
                target_date = parsed
                initial_data["date"] = target_date

        time_slot_param = request.GET.get("time_slot")
        if time_slot_param:
            target_time_slot = time_slot_param
            initial_data["time_slot"] = target_time_slot

    session_form = AttendanceSessionForm(request.POST or None, initial=initial_data)
    
    session = None
    students = []
    records = {}

    # Logic to fetch data:
    # 1. If POST and Valid: Use form data (Save action)
    # 2. If GET (or POST invalid) and we have class/subject: Try to load for target_date (View action)
    
    should_fetch = False
    if request.method == "POST":
        if session_form.is_valid():
            target_date = session_form.cleaned_data["date"]
            target_time_slot = session_form.cleaned_data["time_slot"]
            should_fetch = True
    elif class_stream_id and subject_id:
        # GET request with required params
        should_fetch = True

    if should_fetch and class_stream_id and subject_id:
        try:
            class_stream = AcademicClassStream.objects.get(pk=class_stream_id)
            # Find subject (optimization: could use get() if we didn't already have the list, 
            # but since we have `subjects` list, finding it matches existing style)
            subject = next((s for s in subjects if s.id == int(subject_id)), None)
            
            if class_stream and subject:
                academic_year = AcademicYear.objects.filter(is_current=True).first()
                term = class_stream.academic_class.term

                if academic_year and term:
                    # Get or Create Session
                    # Note: On a purely GET view, creating a session might be aggressive, 
                    # but it ensures the grid is ready.
                    session = get_or_create_session(
                        class_stream=class_stream,
                        subject=subject,
                        teacher=staff,
                        date=target_date,
                        time_slot=target_time_slot,
                        academic_year=academic_year,
                        term=term,
                    )
                    initialize_session_records(session)

                    students = (
                        ClassRegister.objects.filter(academic_class_stream=class_stream)
                        .select_related("student")
                        .order_by("student__student_name")
                    )
                    records = {r.student_id: r for r in session.records.select_related("student")}
        except (AcademicClassStream.DoesNotExist, ValueError):
            pass

    # Determine if the current user can unlock sessions (admin / DOS)
    staff_account = getattr(request.user, "staff_account", None)
    role_name = staff_account.role.name if staff_account and staff_account.role else None
    active_role = request.session.get("active_role_name")
    # Only superusers can unlock attendance sessions
    can_unlock = request.user.is_superuser

    if request.method == "POST" and session:
        # Block save if session is locked (unless user can unlock)
        if session.is_locked and not can_unlock:
            messages.warning(request, "This attendance session is locked and cannot be edited. Contact admin or DOS to unlock.")
        else:
            payload_raw = request.POST.get("attendance_payload")
            if payload_raw:
                payload = json.loads(payload_raw)
                save_attendance_records(session, payload, staff)
                # Lock the session after saving
                session.is_locked = True
                session.save(update_fields=["is_locked"])
                messages.success(request, "Attendance saved and locked successfully.")
                return redirect(f"{request.path}?class_stream={class_stream_id}&subject={subject_id}&date={target_date}&time_slot={target_time_slot or ''}")

    context = {
        "class_streams": class_streams,
        "subjects": subjects,
        "session_form": session_form,
        "session": session,
        "students": students,
        "records": records,
        "status_choices": AttendanceStatus.choices,
        "is_locked": session.is_locked if session else False,
        "can_unlock": can_unlock,
    }
    return render(request, "attendance/take_attendance.html", context)


@login_required
def unlock_attendance(request, session_id):
    """Allow only superusers to unlock a locked attendance session."""
    # Only superusers can unlock attendance sessions
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to unlock attendance sessions.")
        return redirect("attendance_dashboard")

    try:
        att_session = AttendanceSession.objects.get(pk=session_id)
        att_session.is_locked = False
        att_session.save(update_fields=["is_locked"])
        messages.success(request, f"Attendance session for {att_session} has been unlocked.")
        return redirect(f"/attendance/take/?class_stream={att_session.class_stream_id}&subject={att_session.subject_id}&date={att_session.date}&time_slot={att_session.time_slot_id or ''}")
    except AttendanceSession.DoesNotExist:
        messages.error(request, "Attendance session not found.")
        return redirect("attendance_dashboard")


@login_required
def attendance_analysis(request):
    class_stream_id = request.GET.get("class_stream") or ""
    min_percent = float(request.GET.get("min") or 75)

    records = (
        ClassRegister.objects.select_related("student", "academic_class_stream")
        .filter(student__is_active=True)
    )
    if class_stream_id:
        records = records.filter(academic_class_stream_id=class_stream_id)

    data_rows = []
    for reg in records:
        total = reg.student.attendance_records.count()
        present = reg.student.attendance_records.filter(status=AttendanceStatus.PRESENT).count()
        percent = round((present / total) * 100, 0) if total else 0
        if percent < min_percent:
            data_rows.append(
                {
                    "student": reg.student,
                    "class_stream": reg.academic_class_stream,
                    "percent": percent,
                }
            )

    context = {
        "class_streams": AcademicClassStream.objects.all(),
        "selected_class_stream": class_stream_id,
        "min_percent": min_percent,
        "rows": data_rows,
    }
    return render(request, "attendance/attendance_analysis.html", context)


@login_required
def student_attendance_report(request):
    """View individual student's attendance records with date filtering."""
    student_id = request.GET.get("student")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    
    # Default to current month if no dates provided
    today = timezone.now().date()
    if not date_from:
        date_from = today.replace(day=1)  # First day of month
    else:
        from django.utils.dateparse import parse_date
        date_from = parse_date(date_from) or today.replace(day=1)
    
    if not date_to:
        date_to = today
    else:
        date_to = parse_date(date_to) or today
    
    # Get student if selected
    student = None
    records = None
    if student_id:
        try:
            student = Student.objects.get(pk=student_id)
            records = (
                AttendanceRecord.objects.filter(
                    student=student,
                    session__date__gte=date_from,
                    session__date__lte=date_to
                )
                .select_related("session", "session__class_stream", "session__subject")
                .order_by("session__date")
            )
        except (Student.DoesNotExist, ValueError):
            pass
    
    # Calculate summary
    if records is not None:
        total = records.count()
        present = records.filter(status=AttendanceStatus.PRESENT).count()
        absent = records.filter(status=AttendanceStatus.ABSENT).count()
        late = records.filter(status=AttendanceStatus.LATE).count()
        excused = records.filter(status=AttendanceStatus.EXCUSED).count()
    else:
        total = 0
        present = 0
        absent = 0
        late = 0
        excused = 0
    
    # Format dates for HTML date input
    date_from_str = date_from.strftime('%Y-%m-%d') if date_from else ''
    date_to_str = date_to.strftime('%Y-%m-%d') if date_to else ''
    
    context = {
        "students": Student.objects.filter(is_active=True).order_by("student_name"),
        "selected_student": student,
        "date_from": date_from_str,
        "date_to": date_to_str,
        "records": records if records is not None else [],
        "total": total,
        "present": present,
        "absent": absent,
        "late": late,
        "excused": excused,
        "attendance_percentage": round((present / total) * 100, 1) if total > 0 else 0,
    }
    return render(request, "attendance/student_attendance_report.html", context)


@login_required
def class_attendance_report(request):
    """View class attendance by date range with breakdown by subject."""
    class_stream_id = request.GET.get("class_stream")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    subject_id = request.GET.get("subject")
    
    # Default to current week if no dates provided
    today = timezone.now().date()
    if not date_from:
        # Start of week (Monday)
        date_from = today - timedelta(days=today.weekday())
    else:
        from django.utils.dateparse import parse_date
        date_from = parse_date(date_from) or (today - timedelta(days=today.weekday()))
    
    if not date_to:
        date_to = today
    else:
        date_to = parse_date(date_to) or today
    
    # Get class stream if selected
    class_stream = None
    subject = None
    sessions = []
    student_summary = []
    
    if class_stream_id:
        try:
            class_stream = AcademicClassStream.objects.get(pk=class_stream_id)
            
            # Get filter for sessions
            session_filter = Q(
                class_stream=class_stream,
                date__gte=date_from,
                date__lte=date_to
            )
            
            if subject_id:
                try:
                    subject = Subject.objects.get(pk=subject_id)
                    session_filter &= Q(subject=subject)
                except Subject.DoesNotExist:
                    pass
            
            sessions = AttendanceSession.objects.filter(session_filter).order_by("date", "subject")
            
            # Get all students in this class
            class_registers = ClassRegister.objects.filter(
                academic_class_stream=class_stream
            ).select_related("student")
            
            # Calculate summary per student
            for reg in class_registers:
                student = reg.student
                records = AttendanceRecord.objects.filter(
                    student=student,
                    session__in=sessions
                )
                
                total = records.count()
                present = records.filter(status=AttendanceStatus.PRESENT).count()
                absent = records.filter(status=AttendanceStatus.ABSENT).count()
                
                student_summary.append({
                    "student": student,
                    "total": total,
                    "present": present,
                    "absent": absent,
                    "percentage": round((present / total) * 100, 1) if total > 0 else 0,
                })
            
            # Sort by attendance percentage (lowest first - those who need attention)
            student_summary.sort(key=lambda x: x["percentage"])
            
        except AcademicClassStream.DoesNotExist:
            pass
    
    # Get all subjects for filter dropdown
    all_subjects = Subject.objects.all()
    
    # Prepare chart data
    chart_data = None
    subject_chart_data = None
    if class_stream and sessions:
        # Prefetch records for better performance
        sessions = sessions.prefetch_related('records')
        
        # Daily attendance trend
        daily_data = {}
        for session in sessions:
            date_str = session.date.strftime('%Y-%m-%d')
            if date_str not in daily_data:
                daily_data[date_str] = {'present': 0, 'absent': 0, 'late': 0, 'total': 0}
            records = session.records.all()
            daily_data[date_str]['present'] += records.filter(status=AttendanceStatus.PRESENT).count()
            daily_data[date_str]['absent'] += records.filter(status=AttendanceStatus.ABSENT).count()
            daily_data[date_str]['late'] += records.filter(status=AttendanceStatus.LATE).count()
            daily_data[date_str]['total'] += records.count()
        
        # Only create chart data if there's actual data
        if daily_data:
            chart_data = {
                'labels': sorted(daily_data.keys()),
                'present': [daily_data[d]['present'] for d in sorted(daily_data.keys())],
                'absent': [daily_data[d]['absent'] for d in sorted(daily_data.keys())],
                'late': [daily_data[d]['late'] for d in sorted(daily_data.keys())],
            }
        
        # Subject breakdown
        subject_stats = {}
        for session in sessions:
            subj_name = session.subject.name
            if subj_name not in subject_stats:
                subject_stats[subj_name] = {'present': 0, 'total': 0}
            records = session.records.all()
            subject_stats[subj_name]['present'] += records.filter(status=AttendanceStatus.PRESENT).count()
            subject_stats[subj_name]['total'] += records.count()
        
        # Only create subject chart data if there's actual data
        if subject_stats:
            subject_chart_data = {
                'labels': list(subject_stats.keys()),
                'present': [subject_stats[s]['present'] for s in subject_stats],
                'total': [subject_stats[s]['total'] for s in subject_stats],
            }
    
    # Calculate totals
    total_present = sum(s['present'] for s in student_summary)
    total_absent = sum(s['absent'] for s in student_summary)
    
    # Format dates for HTML date input
    date_from_str = date_from.strftime('%Y-%m-%d') if date_from else ''
    date_to_str = date_to.strftime('%Y-%m-%d') if date_to else ''
    
    context = {
        "class_streams": AcademicClassStream.objects.all(),
        "selected_class_stream": class_stream,
        "subjects": all_subjects,
        "selected_subject": subject,
        "date_from": date_from_str,
        "date_to": date_to_str,
        "sessions": sessions,
        "student_summary": student_summary,
        "chart_data": chart_data,
        "subject_chart_data": subject_chart_data,
        "total_present": total_present,
        "total_absent": total_absent,
    }
    return render(request, "attendance/class_attendance_report.html", context)
