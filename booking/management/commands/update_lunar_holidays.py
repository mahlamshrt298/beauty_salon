# booking/management/commands/update_lunar_holidays.py
from django.core.management.base import BaseCommand
from booking.models import Holiday
import jdatetime
from hijri_converter import convert

class Command(BaseCommand):
    help = 'بروزرسانی تاریخ‌های تعطیلات قمری برای سال جاری'
    
    def handle(self, *args, **kwargs):
        current_year = jdatetime.date.today().year
        
        # 1. تعطیلات قمری موجود
        lunar_holidays = Holiday.objects.filter(holiday_type='lunar')
        
        updated_count = 0
        for holiday in lunar_holidays:
            try:
                # محاسبه سال هجری قمری تقریبی
                hijri_year = current_year - 621
                
                # تبدیل تاریخ قمری به میلادی
                hijri_date = convert.Hijri(hijri_year, holiday.hijri_month, holiday.hijri_day)
                gregorian_date = hijri_date.to_gregorian()
                
                # تاریخ شمسی
                jalali_date = jdatetime.date.fromgregorian(date=gregorian_date)
                
                # بروزرسانی
                holiday.date = gregorian_date
                holiday.jalali_date = f"{jalali_date.year}/{jalali_date.month:02d}/{jalali_date.day:02d}"
                holiday.year = gregorian_date.year
                holiday.save()
                
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f'✓ {holiday.title}: {holiday.jalali_date}'
                ))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'✗ خطا در {holiday.title}: {str(e)}'
                ))
        
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ {updated_count} تعطیلی قمری برای سال {current_year} بروزرسانی شد'
        ))