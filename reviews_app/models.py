from django.db import models
from services_app.models import Service  # ← ایمپورت مدل Service
from django.contrib.auth.models import User
from booking.models import Appointment

# Create your models here.
#نظرات و امتیازات
class Review(models.Model):
    STATUS_CHOICES = (
        ('pending', 'در انتظار'),
        ('approved', 'تأیید شده'),
        ('rejected', 'رد شده'),
    )

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    #امتیاز
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], default=5)
    #متن نظر
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    #وضعیت تأیید/عدم تأیید
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='وضعیت'
    )
    # سرویس مرتبط با نظر
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="خدمت مرتبط",
        related_name='reviews'  
    )

    admin_reply = models.TextField(
        blank=True,
        null=True,
        verbose_name="پاسخ مدیریت"
    )

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='نوبت مربوطه'
    )

    show_on_home = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.rating}/5"