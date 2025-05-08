from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

class Classroom(models.Model):
    name = models.CharField(max_length=50)
    location = models.CharField(max_length=100, verbose_name="Block", blank=True, null=True)
    capacity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name
    

class WeekDay(models.TextChoices):
    MONDAY = 'MON', 'Monday'
    TUESDAY = 'TUE', 'Tuesday'
    WEDNESDAY = 'WED', 'Wednesday'
    THURSDAY = 'THU', 'Thursday'
    FRIDAY = 'FRI', 'Friday'
    SATURDAY = 'SAT', 'Saturday'
    SUNDAY = 'SUN', 'Sunday'


class TimeSlot(models.Model):
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ['start_time']
        unique_together = ('start_time', 'end_time')

    def __str__(self):
        return f'{self.start_time.strftime("%H:%M")} - {self.end_time.strftime("%H:%M")}'

class BreakPeriod(models.Model):
    
    weekday = models.CharField(max_length=3, choices=WeekDay.choices)
    name = models.CharField(max_length=20, default="Break")
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('weekday', 'time_slot')

    def __str__(self):
        return f'{self.name} on {self.weekday} at {self.time_slot}'


class Timetable(models.Model):
    class_stream = models.ForeignKey("app.AcademicClassStream", on_delete=models.CASCADE, related_name='timetables')
    weekday = models.CharField(max_length=3, choices=WeekDay.choices)
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)
    subject = models.ForeignKey('app.Subject', on_delete=models.CASCADE)
    teacher = models.ForeignKey('app.Staff', on_delete=models.SET_NULL, null=True, related_name='teaching_slots')
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, blank=True, related_name="allocations")

    class Meta:
        unique_together = ('timetable', 'weekday', 'time_slot')

    def __str__(self):
        return f'{self.subject} on {self.weekday} at {self.time_slot}'
    
    def clean(self):
        # Conflict: Same teacher at same time
        teacher_conflict = Timetable.objects.filter(
            teacher=self.teacher,
            weekday=self.weekday,
            time_slot=self.time_slot
        ).exclude(pk=self.pk).exists()

        if teacher_conflict:
            raise ValidationError("This teacher is already assigned at this time.")

        # Conflict: Same classroom at same time
        if self.classroom:
            room_conflict = Timetable.objects.filter(
                classroom=self.classroom,
                weekday=self.weekday,
                time_slot=self.time_slot
            ).exclude(pk=self.pk).exists()

            if room_conflict:
                raise ValidationError("This classroom is already in use at this time.")

        # Conflict: Same class already scheduled
        class_conflict = Timetable.objects.filter(
            class_stream=self.class_stream,
            weekday=self.weekday,
            time_slot=self.time_slot
        ).exclude(pk=self.pk).exists()

        if class_conflict:
            raise ValidationError("This class already has a subject at this time.")

    def save(self, *args, **kwargs):
        self.full_clean()  
        super().save(*args, **kwargs)


    