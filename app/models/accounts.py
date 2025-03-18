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

        
        if self.user.email != self.staff.email:
            User.objects.filter(pk=self.user.pk).update(email=self.staff.email)

        super().save(*args, **kwargs)


