from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from accounts.models import Notification


def notify_user(
    *,
    user,
    message,
    subject=None,
    notif_type="system",
    channel="site",
    send_email=False,
    appointment=None,
):
    """
    اعلان داخل سایت + (اختیاری) ایمیل
    """

    # 1️⃣ اعلان داخل سایت
    notification = Notification.objects.create(
        user=user,
        appointment=appointment,
        type=notif_type,
        channel=channel,
        message=message,
        status="sent",
        sent_at=timezone.now(),
    )

    # 2️⃣ ایمیل (اختیاری)
    if send_email and user.email:
        send_mail(
            subject=subject or "اعلان جدید",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )

    return notification
