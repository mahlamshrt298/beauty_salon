# accounts/utils/notification_service.py

from accounts.models import Notification
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime


def notify_user(user, message, subject, notif_type, channel, send_email=False, appointment=None):
    """
    این تابع یک اعلان جدید ایجاد می‌کند و می‌تواند ایمیل هم ارسال کند.

    Args:
        user (User): کاربری که اعلان بهش ارسال می‌شه
        message (str): متن اعلان
        subject (str): موضوع ایمیل (اگر ایمیل ارسال بشه)
        notif_type (str): نوع اعلان (reminder, status_change, promotion)
        channel (str): کانال ارسال (email, sms, whatsapp)
        send_email (bool): اگر True باشه، ایمیل هم ارسال می‌شه
        appointment (Appointment): نوبت مرتبط (اختیاری)
    """
    # ایجاد اعلان جدید
    notification = Notification.objects.create(
        user=user,
        message=message,
        type=notif_type,
        channel=channel,
        appointment=appointment,
    )

    if send_email and user.email:
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            notification.status = "sent"
            notification.sent_at = datetime.now()
        except Exception as e:
            notification.status = "failed"
            notification.save()
            return  # اگر ایمیل ارسال نشد، اعلان رو به عنوان ناموفق ذخیره کن

    notification.save()