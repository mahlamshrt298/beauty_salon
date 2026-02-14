from django.core.management.base import BaseCommand
from booking.models import Holiday
import jdatetime
from hijri_converter import convert

class Command(BaseCommand):
    help = 'بارگذاری تعطیلات هوشمند (شمسی + قمری تقریبی)'

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, help='سال میلادی برای بارگذاری تعطیلات')

    def handle(self, *args, **kwargs):
        target_year = kwargs.get('year') or jdatetime.date.today().year
        
        # تبدیل سال شمسی به میلادی (تخمین)
        gregorian_year = target_year + 621 
        
        # ۱. تعطیلات شمسی ثابت (نوروز و...)
        solar_holidays = [
            (target_year, 1, 1, "عید نوروز", 1, 1),
            (target_year, 1, 2, "عید نوروز", 1, 2),
            (target_year, 1, 3, "عید نوروز", 1, 3),
            (target_year, 1, 4, "عید نوروز", 1, 4),
            (target_year, 1, 12, "روز جمهوری اسلامی", 1, 12),
            (target_year, 1, 13, "سیزده به در", 1, 13),
            (target_year, 3, 14, "رحلت امام خمینی", 3, 14),
            (target_year, 3, 15, "قیام 15 خرداد", 3, 15),
            # ... سایر تعطیلات شمسی
        ]
        
        for year, month, day, title, _, _ in solar_holidays:
            jalali_str = f"{year}/{month:02d}/{day:02d}"
            Holiday.objects.get_or_create(
                jalali_date=jalali_str,
                defaults={
                    'title': title,
                    'holiday_type': 'solar',
                    'is_active': True
                }
            )
            self.stdout.write(self.style.SUCCESS(f'✓ شمسی: {jalali_str} - {title}'))

        # ۲. تعطیلات قمری (تقریبی با کتابخانه)
        lunar_holidays = [
            (1, 1, "عید فطر"),      # 1 شوال
            (1, 2, "عید فطر"),      # 2 شوال
            (1, 3, "عید فطر"),      # 3 شوال
            (12, 10, "عید قربان"),  # 10 ذیحجه
            (12, 18, "عید غدیر"),   # 18 ذیحجه
            (1, 9, "عاشورا"),       # 9 محرم
            (1, 10, "عاشورا"),      # 10 محرم
            # ... سایر تعطیلات قمری
        ]
        
        for hijri_month, hijri_day, title in lunar_holidays:
            try:
                # تخمین سال هجری قمری (سال میلادی - 622)
                hijri_year = target_year  - 621
                
                # تبدیل تاریخ قمری به میلادی
                hijri_date = convert.Hijri(hijri_year, hijri_month, hijri_day)
                gregorian = hijri_date.to_gregorian()
                
                # ذخیره با اطلاعات قمری
                Holiday.objects.get_or_create(
                    hijri_month=hijri_month,
                    hijri_day=hijri_day,
                    year=gregorian.year,
                    defaults={
                        'title': title,
                        'holiday_type': 'lunar',
                        'is_active': True,
                        'date': gregorian
                    }
                )
                jalali = jdatetime.date.fromgregorian(date=gregorian)
                self.stdout.write(self.style.WARNING(f'🌙 قمری: {jalali.strftime("%Y/%m/%d")} ({hijri_year}/{hijri_month}/{hijri_day}) - {title}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ خطا در محاسبه {title}: {str(e)}'))

        self.stdout.write(self.style.SUCCESS(f'\n✅ تعطیلات سال {target_year} بارگذاری شد'))
        self.stdout.write(self.style.WARNING('⚠️ نکته: تاریخ‌های قمری تقریبی هستند. حتماً در پنل مدیریت، تاریخ‌های رسمی را اصلاح کنید!'))