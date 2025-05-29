from django.shortcuts import render, get_object_or_404,redirect
from django.views.generic import ListView, DetailView
from app.models import AcademicClassStream, Staff, Subject
from app.models import Timetable, Classroom, WeekDay, TimeSlot, BreakPeriod
from django.views.decorators.http import require_POST
from app.forms.timetables import TimeSlotForm
from app.models.timetables import TimeSlot



def select_class_for_timetable(request):
    classes = AcademicClassStream.objects.all()
    return render(request, 'timetable/select_class.html', {'classes': classes})



def set_timetable(request, class_stream_id):
    class_stream = get_object_or_404(AcademicClassStream, pk=class_stream_id)
    time_slots = TimeSlot.objects.all().order_by('start_time')
    weekdays = list(WeekDay.choices)

    # Build a lookup table for quick access
    timetable_entries = Timetable.objects.filter(class_stream=class_stream)
    timetable_lookup = {}
    for entry in timetable_entries:
        key = f"{entry.weekday}_{entry.time_slot_id}"
        timetable_lookup[key] = entry

    # Prepare rows for rendering
    table_data = []
    for slot in time_slots:
        row = {
            'slot_label': f"{slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')}",
            'entries': []
        }
        for day_code, _ in weekdays:
            key = f"{day_code}_{slot.id}"
            row['entries'].append(timetable_lookup.get(key))  # Could be None
        table_data.append(row)

    context = {
        'class_stream': class_stream,
        'weekdays': weekdays,
        'table_data': table_data,
    }
    return render(request, 'timetable/set_timetable.html', context)


def create_time_slots(request):
    if request.method == 'POST':
        form = TimeSlotForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('time_slots_list')
    else:
        form = TimeSlotForm()

    time_slots = TimeSlot.objects.all()
    return render(request, 'timetable/create_time_slots.html', {
        'form': form,
        'time_slots': time_slots
    })

def edit_time_slot(request, pk):
    slot = get_object_or_404(TimeSlot, pk=pk)
    if request.method == 'POST':
        form = TimeSlotForm(request.POST, instance=slot)
        if form.is_valid():
            form.save()
            return redirect('time_slots_list')
    else:
        form = TimeSlotForm(instance=slot)
    return render(request, 'timetable/edit_time_slot.html', {'form': form, 'slot': slot})

@require_POST
def delete_time_slot(request, pk):
    slot = get_object_or_404(TimeSlot, pk=pk)
    slot.delete()
    return redirect('time_slots_list')




























class SchoolTimetableView(ListView):
    model = Timetable
    template_name = 'timetable/school_timetable.html'
    context_object_name = 'timetables'

    def get_queryset(self):
        return Timetable.objects.all().order_by('weekday', 'time_slot')


class ClassTimetableView(ListView):
    model = Timetable
    template_name = 'timetable/class_timetable.html'
    context_object_name = 'timetables'

    def get_queryset(self):
        class_id = self.kwargs.get('class_id')
        return Timetable.objects.filter(class_stream__id=class_id).order_by('weekday', 'time_slot')


class TeacherTimetableView(ListView):
    model = Timetable
    template_name = 'timetable/teacher_timetable.html'
    context_object_name = 'timetables'

    def get_queryset(self):
        teacher_id = self.kwargs.get('teacher_id')
        return Timetable.objects.filter(teacher__id=teacher_id).order_by('weekday', 'time_slot')


class ClassroomListView(ListView):
    model = Classroom
    template_name = 'timetable/classrooms.html'
    context_object_name = 'classrooms'


class ClassroomDetailView(DetailView):
    model = Classroom
    template_name = 'timetable/classroom_detail.html'
    context_object_name = 'classroom'

