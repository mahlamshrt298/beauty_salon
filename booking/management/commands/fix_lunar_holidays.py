from django.core.management.base import BaseCommand
from booking.models import Holiday
import jdatetime
from hijri_converter import convert

class Command(BaseCommand):
    help = 'اصلاح تاریخ‌های تعطیلات قمری'
    
    def handle(self, *args, **kwargs):
        current_year = jdatetime.date.today().year
        
        # تعطیلات قمری مهم
        lunar_holidays = [
            # (ماه قمری, روز قمری, عنوان, روزهای تمدید)
            (10, 1, "عید فطر", 3),
            (12, 10, "عید قربان", 1),
            (12, 18, "عید غدیر", 1),
            (1, 9, "تاسوعا", 1),
            (1, 10, "عاشورا", 1),
            (3, 20, "اربعین حسینی", 1),
        ]
        
        # 1. پاک کردن تعطیلات قمری فعلی (اگر می‌خوای)
        # Holiday.objects.filter(holiday_type='lunar').delete()
        
        for hijri_month, hijri_day, title, duration in lunar_holidays:
            try:
                # سال هجری قمری برای سال 1404
                # سال 1404 شمسی ≈ سال 1446 قمری
                hijri_year = 1446  # برای سال 1404
                
                hijri_date = convert.Hijri(hijri_year, hijri_month, hijri_day)
                gregorian = hijri_date.to_gregorian()
                jalali = jdatetime.date.fromgregorian(date=gregorian)
                
                # ایجاد تعطیلی اصلی
                Holiday.objects.update_or_create(
                    hijri_month=hijri_month,
                    hijri_day=hijri_day,
                    year=gregorian.year,
                    defaults={
                        'title': title,
                        'holiday_type': 'lunar',
                        'is_active': True,
                        'date': gregorian,
                        'jalali_date': f"{jalali.year}/{jalali.month:02d}/{jalali.day:02d}"
                    }
                )
                self.stdout.write(self.style.SUCCESS(f'✓ {title}: {jalali.strftime("%Y/%m/%d")}'))
                
                # برای عید فطر که چند روزه است
                if duration > 1:
                    for day_offset in range(1, duration):
                        hijri_date_extra = convert.Hijri(hijri_year, hijri_month, hijri_day + day_offset)
                        gregorian_extra = hijri_date_extra.to_gregorian()
                        jalali_extra = jdatetime.date.fromgregorian(date=gregorian_extra)
                        
                        Holiday.objects.update_or_create(
                            hijri_month=hijri_month,
                            hijri_day=hijri_day + day_offset,
                            year=gregorian_extra.year,
                            defaults={
                                'title': title,
                                'holiday_type': 'lunar',
                                'is_active': True,
                                'date': gregorian_extra,
                                'jalali_date': f"{jalali_extra.year}/{jalali_extra.month:02d}/{jalali_extra.day:02d}"
                            }
                        )
                        self.stdout.write(self.style.SUCCESS(f'  ├ روز {day_offset+1}: {jalali_extra.strftime("%Y/%m/%d")}'))
                        
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ {title}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ تعطیلات قمری سال {current_year} اصلاح شد'))