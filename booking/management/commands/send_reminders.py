# booking/management/commands/send_reminders.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, datetime
from booking.models import Appointment
from accounts.models import Notification
from django.core.mail import send_mail
from django.conf import settings
import logging
# در ابتدای send_reminders.py
import jdatetime  # ✅ برای تبدیل به تاریخ شمسی

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'ارسال یادآوری 24 ساعت قبل از نوبت'

    def handle(self, *args, **kwargs):
        now = timezone.localtime(timezone.now())
        tomorrow = now + timedelta(hours=24)
        
        # پیدا کردن نوبت‌های فردا (فقط تأیید شده‌ها)
        appointments = Appointment.objects.filter(
            appointment_date=tomorrow.date(),
            status__in=['confirmed'],  # فقط نوبت‌های تأیید شده
            reminder_sent=False
        ).select_related('user', 'service', 'staff')

        sent = 0
        for appt in appointments:
            try:
                # ✅ محاسبه تاریخ شمسی و اطلاعات داخل حلقه (برای هر نوبت)
                jalali_date = jdatetime.date.fromgregorian(date=appt.appointment_date)
                jalali_date_str = jalali_date.strftime('%Y/%m/%d')
                jalali_weekday = jalali_date.strftime('%A')  # نام روز هفته فارسی
                formatted_time = appt.start_time.strftime('%H:%M')
                staff_name = appt.staff.full_name if appt.staff else "تعریف نشده"

                # ✉️ ارسال ایمیل با تاریخ شمسی
                if appt.user.email:
                    subject = f'یادآوری نوبت - سالن زیبایی نورا ({jalali_date_str})'
                    message = f"""سلام {appt.user.first_name or appt.user.username} عزیز،

    فردا ({jalali_date_str} - {jalali_weekday}) نوبت شما در سالن زیبایی نورا است:

    خدمت: {appt.service.name}
    ساعت: {formatted_time}
    پرسنل: {staff_name}

    لطفاً 15 دقیقه قبل از موعد حضور داشته باشید.
    در صورت لغو، حداقل 2 ساعت قبل از نوبت تماس بگیرید.

    آدرس: تهران، میدان ولیعصر، خیابان نورا، پلاک ۱۲
    تلفن: ۰۲۱-۱۲۳۴۵۶۷۸

    با احترام،
    تیم سالن زیبایی نورا
    """
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [appt.user.email],
                        fail_silently=True,
                    )
                    logger.info(f"ایمیل یادآوری به {appt.user.email} ارسال شد")

                # 🔔 ایجاد نوتیفیکیشن با تاریخ شمسی
                notification_message = (
                    f"🔔 یادآوری نوبت فردا\n"
                    f"خدمت: {appt.service.name}\n"
                    f"تاریخ: {jalali_date_str} ({jalali_weekday})\n"
                    f"ساعت: {formatted_time}\n"
                    f"پرسنل: {staff_name}"
                )
                Notification.objects.create(
                    user=appt.user,
                    message=notification_message,
                    type='reminder',
                    channel='in_app',
                    status='sent'
                )

                # ✅ علامت‌گذاری برای جلوگیری از ارسال مجدد
                appt.reminder_sent = True
                appt.save()
                
                sent += 1
                logger.info(f"یادآوری برای نوبت #{appt.id} به {appt.user.email} ارسال شد")
                
            except Exception as e:
                logger.error(f"خطا در ارسال یادآوری نوبت #{appt.id}: {str(e)}")
        
        self.stdout.write(self.style.SUCCESS(f'✅ یادآوری برای {sent} نوبت ارسال شد'))