from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile
from django.contrib.auth.signals import user_logged_in
from core.utils.birthday import handle_birthday_logic

#ساخت خودکار پروفایل بلافاصله بعد از ثبت‌نام یوزر جدید
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

#برای چک کردن تاریخ تولد کاربر
@receiver(user_logged_in)
def birthday_check_on_login(sender, request, user, **kwargs):
    handle_birthday_logic(user)
