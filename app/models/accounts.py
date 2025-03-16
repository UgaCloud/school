from django.contrib.auth.models import User
from django.db import models
from app.models.staffs import *

class StaffAccount(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_account')
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if not self.user.username:
            self.user.username = f"{self.staff.first_name}.{self.staff.last_name}".lower()
            self.user.set_password('123')  
    
        self.user.email = self.staff.email  
        self.user.save()
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.staff} - {self.role}"

    class Meta:
        unique_together = ('staff', 'user', 'role')
