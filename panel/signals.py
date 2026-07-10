from django.contrib.auth.models import Group
from django.db.models.signals import post_migrate
from django.dispatch import receiver

@receiver(post_migrate)
def create_default_groups(sender, **kwargs):
    # ساخت گروه‌های کاربری پیش‌فرض سیستم برای مدیریت سطح دسترسی‌ها (مالک سالن و منشی/پذیرش)
    owner_group, created = Group.objects.get_or_create(name="owner")
    receptionist_group, created = Group.objects.get_or_create(name="receptionist")
