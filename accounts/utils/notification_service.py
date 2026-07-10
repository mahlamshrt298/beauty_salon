from accounts.models import Notification
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime


def notify_user(user, message, subject, notif_type, channel, send_email=False, appointment=None):
    #سرویس اصلی برای ارسال نوتیف به کاربر و لاگ کردنش تو دیتابیس.
    # ایجاد اعلان جدید
    notification = Notification.objects.create(
        user=user,
        message=message,
        type=notif_type,
        channel=channel,
        appointment=appointment,
    )

    # اگه کاربر درخواست ارسال ایمیل داشت و ایمیلش هم ست شده بود
    if send_email and user.email:
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
            notification.status = "sent"
            notification.sent_at = datetime.now()
        except Exception as e:
            notification.status = "failed"
            notification.save()
            return  # اگر ایمیل ارسال نشد، اعلان رو به عنوان ناموفق ذخیره کن

    notification.save()