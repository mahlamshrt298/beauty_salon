from datetime import date, timedelta
from accounts.models import DiscountCode
from panel.models import SalonSettings
import random, string
from accounts.models import Notification

def generate_code():
    return "BD-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def days_until_birthday(birthday):
    today = date.today()
    birthday_this_year = birthday.replace(year=today.year)

    if birthday_this_year < today:
        birthday_this_year = birthday_this_year.replace(year=today.year + 1)

    return (birthday_this_year - today).days


def handle_birthday_logic(user):
    profile = user.profile
    settings = SalonSettings.objects.first()

    if not settings or not profile.birthday:
        return

    days_left = days_until_birthday(profile.birthday)
    today = date.today()

    # 🔔 اعلان قبل از تولد
    if days_left == settings.birthday_notify_days_before:
        already_notified = Notification.objects.filter(
            user=user,
            message__contains="روز تا تولدت مونده",
            created_at__date=today
        ).exists()

        if not already_notified:
            Notification.objects.create(
                user=user,
                message=f"🎉 فقط {days_left} روز تا تولدت مونده!"
            )

    # 🎁 روز تولد → ساخت کد تخفیف
    if days_left == 0 and settings.birthday_discount_enabled:
         # سعی کن یک کد موجود برای کاربر پیدا کن
        discount = DiscountCode.objects.filter(
            user=user,
            expires_at__gte=today
        ).first()

        if discount:
            # اگر قبلاً ساخته شده بود، فقط فیلد اعلان را بروز کن
            discount.notification_sent = True
            discount.save()
        else:
            # ساخت کد جدید
            DiscountCode.objects.create(
                user=user,
                code=generate_code(),
                percent=settings.birthday_discount_percent,
                expires_at=today + timedelta(
                    days=settings.birthday_discount_valid_days
                ),
                notification_sent=True,      # ← همینجا مقداردهی می‌کنیم
            )