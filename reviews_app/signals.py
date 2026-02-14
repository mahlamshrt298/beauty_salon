from django.dispatch import receiver
from .models import Review
from accounts.models import Notification
from django.db.models.signals import pre_save, post_save

@receiver(pre_save, sender=Review)
def review_pre_save(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._old_status = Review.objects.get(pk=instance.pk).status
        except Review.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None
        
@receiver(post_save, sender=Review)
def review_status_notification(sender, instance, created, **kwargs):
    # اگر نظر تازه ساخته شده، اعلان نده
    if created:
        return

    old_status = getattr(instance, "_old_status", None)
    new_status = instance.status

    # فقط وقتی وضعیت تغییر کرده
    if old_status == new_status:
        return

    if new_status == "approved":
        message = "نظر شما تأیید شد و در سایت نمایش داده می‌شود."
    elif new_status == "rejected":
        message = "نظر شما رد شد و نمایش داده نخواهد شد."
    else:
        return

    Notification.objects.create(
        user=instance.user,
        message=message
    )
