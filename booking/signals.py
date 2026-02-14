from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import datetime

from .models import Appointment
from accounts.utils.notification_service import notify_user
import jdatetime

@receiver(pre_save, sender=Appointment)
def send_notification_on_appointment_edit(sender, instance, **kwargs):
    
    # ❌ اگر از ویو لغو شده، اعلان نفرست
    if getattr(instance, '_skip_signal', False):
        return
    
    # اگر نوبت تازه ساخته می‌شود → کاری نکن
    if not instance.pk:
        return

    try:
        old = Appointment.objects.get(pk=instance.pk)
    except Appointment.DoesNotExist:
        return

    # اگر هیچ تغییری نداشته
    if old.appointment_date == instance.appointment_date and \
       old.start_time == instance.start_time and \
       old.service == instance.service and \
       old.status == instance.status and \
       old.staff == instance.staff:
        return

    user = instance.user
    
    # ✅ تبدیل تاریخ میلادی به شمسی برای نمایش
    jalali_date = jdatetime.date.fromgregorian(date=instance.appointment_date)
    formatted_date = jalali_date.strftime('%Y/%m/%d')
    weekday_fa = jalali_date.strftime('%A')

    # ✅ شناسایی تمام تغییرات
    has_status_change = old.status != instance.status
    has_date_change = old.appointment_date != instance.appointment_date
    has_time_change = old.start_time != instance.start_time
    has_service_change = old.service != instance.service
    has_staff_change = old.staff != instance.staff

    # ✅ شمارش تعداد تغییرات
    change_count = sum([
        has_status_change,
        has_date_change,
        has_time_change,
        has_service_change,
        has_staff_change
    ])

    # ✅ اگر فقط یک تغییر داشته → پیام ساده
    if change_count == 1:
        message = create_single_change_message(
            old, instance, user, 
            formatted_date, weekday_fa,
            has_status_change, has_date_change,
            has_time_change, has_service_change,
            has_staff_change
        )
        
        notify_user(
            user=user,
            message=message,
            subject="🔔 اطلاع‌رسانی نوبت",
            notif_type="appointment_update",
            channel="email",
            send_email=True,
            appointment=instance,
        )
    
    # ✅ اگر چند تغییر داشته → پیام ترکیبی
    else:
        message = create_combined_change_message(
            old, instance, user,
            formatted_date, weekday_fa,
            has_status_change, has_date_change,
            has_time_change, has_service_change,
            has_staff_change
        )
        
        notify_user(
            user=user,
            message=message,
            subject="🔔 اطلاع‌رسانی نوبت",
            notif_type="appointment_update",
            channel="email",
            send_email=True,
            appointment=instance,
        )

# ✅ تابع ساخت پیام تکی
def create_single_change_message(old, instance, user, formatted_date, weekday_fa,
                                  has_status_change, has_date_change,
                                  has_time_change, has_service_change,
                                  has_staff_change):
    """ساخت پیام برای یک تغییر واحد"""
    
    if has_status_change:
        if instance.status == 'confirmed':
            return (
                f"✅ نوبت شما تأیید شد!\n"
                f"━━━━━━━━━━━━━━\n"
                f"👤 مشتری: {user.get_full_name() or user.username}\n"
                f"💼 خدمت: {instance.service.name}\n"
                f"📅 تاریخ: {formatted_date} ({weekday_fa})\n"
                f"⏰ ساعت: {instance.start_time.strftime('%H:%M')}\n"
                f"💇 پرسنل: {instance.staff.full_name if instance.staff else 'تخصیص داده خواهد شد'}\n"
                f"━━━━━━━━━━━━━━\n"
                f"لطفاً 15 دقیقه قبل از موعد حضور داشته باشید."
            )
        elif instance.status == 'cancelled':
            if hasattr(instance, '_cancellation_reason') and instance._cancellation_reason == 'no_show':
                # پیام خاص عدم حضور
                return (
                    f"❌ نوبت شما به دلیل عدم حضور لغو شد.\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"📅 تاریخ: {formatted_date} ({weekday_fa})\n"
                    f"⏰ ساعت: {instance.start_time.strftime('%H:%M')}\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"برای رزرو مجدد، از طریق سایت اقدام کنید."
                )
            else:
                # پیام لغو عمومی
                return(
                    f"❌ نوبت شما لغو شد.\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"👤 مشتری: {user.get_full_name() or user.username}\n"
                    f"💼 خدمت: {instance.service.name}\n"
                    f"📅 تاریخ: {formatted_date} ({weekday_fa})\n"
                    f"⏰ ساعت: {instance.start_time.strftime('%H:%M')}\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"برای اطلاعات بیشتر با سالن تماس بگیرید."
                )

        elif instance.status == 'completed':
            return (
                f"✨ خدمت شما با موفقیت انجام شد!\n"
                f"━━━━━━━━━━━━━━\n"
                f"👤 مشتری: {user.get_full_name() or user.username}\n"
                f"💼 خدمت: {instance.service.name}\n"
                f"📅 تاریخ: {formatted_date} ({weekday_fa})\n"
                f"⏰ ساعت: {instance.start_time.strftime('%H:%M')}\n"
                f"💇 پرسنل: {instance.staff.full_name if instance.staff else '—'}\n"
                f"━━━━━━━━━━━━━━\n"
                f"از اعتمادتان سپاسگزاریم 🌸"
            )
        else:
            return (
                f"🔔 وضعیت نوبت تغییر کرد: {old.status} → {instance.status}\n"
                f"📅 تاریخ: {formatted_date} ({weekday_fa})\n"
                f"⏰ ساعت: {instance.start_time.strftime('%H:%M')}"
            )
    
    elif has_date_change:
        old_jalali = jdatetime.date.fromgregorian(date=old.appointment_date)
        return (
            f"📅 تاریخ نوبت تغییر کرد:\n"
            f"━━━━━━━━━━━━━━\n"
            f"📅 قبل: {old_jalali.strftime('%Y/%m/%d')} ({old_jalali.strftime('%A')})\n"
            f"📅 بعد: {formatted_date} ({weekday_fa})\n"
            f"⏰ ساعت: {instance.start_time.strftime('%H:%M')}\n"
            f"💼 خدمت: {instance.service.name}"
        )
    
    elif has_time_change:
        return (
            f"⏰ ساعت نوبت تغییر کرد:\n"
            f"━━━━━━━━━━━━━━\n"
            f"📅 تاریخ: {formatted_date} ({weekday_fa})\n"
            f"⏰ قبل: {old.start_time.strftime('%H:%M')}\n"
            f"⏰ بعد: {instance.start_time.strftime('%H:%M')}\n"
            f"💼 خدمت: {instance.service.name}"
        )
    
    elif has_service_change:
        return (
            f"💼 خدمت نوبت تغییر کرد:\n"
            f"━━━━━━━━━━━━━━\n"
            f"📅 تاریخ: {formatted_date} ({weekday_fa})\n"
            f"⏰ ساعت: {instance.start_time.strftime('%H:%M')}\n"
            f"💼 قبل: {old.service.name}\n"
            f"💼 بعد: {instance.service.name}"
        )
    
    elif has_staff_change:
        return (
            f"💇 پرسنل نوبت تغییر کرد:\n"
            f"━━━━━━━━━━━━━━\n"
            f"📅 تاریخ: {formatted_date} ({weekday_fa})\n"
            f"⏰ ساعت: {instance.start_time.strftime('%H:%M')}\n"
            f"💼 خدمت: {instance.service.name}\n"
            f"💇 قبل: {old.staff.full_name if old.staff else '—'}\n"
            f"💇 بعد: {instance.staff.full_name if instance.staff else 'تخصیص داده خواهد شد'}"
        )
    
    return ""

# ✅ تابع ساخت پیام ترکیبی
def create_combined_change_message(old, instance, user, formatted_date, weekday_fa,
                                    has_status_change, has_date_change,
                                    has_time_change, has_service_change,
                                    has_staff_change):
    """ساخت پیام ترکیبی برای چندین تغییر"""
    
    message = "🔄 نوبت شما ویرایش شد:\n"
    message += "━━━━━━━━━━━━━━\n\n"
    
    # اضافه کردن هر تغییر به پیام
    if has_status_change:
        message += f"🔔 وضعیت: {old.status} → {instance.status}\n"
    
    if has_date_change:
        old_jalali = jdatetime.date.fromgregorian(date=old.appointment_date)
        message += f"📅 تاریخ: {old_jalali.strftime('%Y/%m/%d')} → {formatted_date}\n"
    
    if has_time_change:
        message += f"⏰ ساعت: {old.start_time.strftime('%H:%M')} → {instance.start_time.strftime('%H:%M')}\n"
    
    if has_service_change:
        message += f"💼 خدمت: {old.service.name} → {instance.service.name}\n"
    
    if has_staff_change:
        old_staff = old.staff.full_name if old.staff else '—'
        new_staff = instance.staff.full_name if instance.staff else 'تخصیص داده خواهد شد'
        message += f"💇 پرسنل: {old_staff} → {new_staff}\n"
    
    message += "\n━━━━━━━━━━━━━━\n"
    message += f"📅 تاریخ نهایی: {formatted_date} ({weekday_fa})\n"
    message += f"⏰ ساعت نهایی: {instance.start_time.strftime('%H:%M')}\n"
    message += f"💼 خدمت نهایی: {instance.service.name}\n"
    message += f"💇 پرسنل نهایی: {instance.staff.full_name if instance.staff else 'تخصیص داده خواهد شد'}"
    
    return message