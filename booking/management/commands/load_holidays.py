from django.core.management.base import BaseCommand
from booking.models import Holiday
import jdatetime
from datetime import timedelta

class Command(BaseCommand):
    help = 'بارگذاری تعطیلات رسمی سال جاری'

    def handle(self, *args, **kwargs):
        current_year = jdatetime.date.today().year
        
        # لیست تعطیلات رسمی ایران (تاریخ‌های شمسی)
        holidays = [
            # نوروز
            (current_year, 1, 1, "عید نوروز", "official"),
            (current_year, 1, 2, "عید نوروز", "official"),
            (current_year, 1, 3, "عید نوروز", "official"),
            (current_year, 1, 4, "عید نوروز", "official"),
            
            # روز جمهوری اسلامی
            (current_year, 1, 12, "روز جمهوری اسلامی", "official"),
            
            # سال نو شمسی
            (current_year, 1, 13, "سیزده به در", "official"),
            
            # روز افتتاح
            (current_year, 3, 14, "رحلت امام خمینی", "religious"),
            (current_year, 3, 15, "قیام 15 خرداد", "official"),
            
            # عید فطر
            (current_year, 4, 1, "عید فطر", "religious"),
            (current_year, 4, 2, "عید فطر", "religious"),
            (current_year, 4, 3, "عید فطر", "religious"),
            
            # عید قربان
            (current_year, 6, 10, "عید قربان", "religious"),
            
            # عید غدیر
            (current_year, 6, 18, "عید غدیر", "religious"),
            
            # مبعث پیامبر
            (current_year, 7, 2, "مبعث پیامبر اکرم", "religious"),
            
            # ولادت امام علی
            (current_year, 7, 13, "ولادت امام علی", "religious"),
            
            # شهادت امام رضا
            (current_year, 8, 30, "شهادة الإمام الرضا", "religious"),
            
            # ولادت امام معصومه
            (current_year, 9, 1, "ولادت حضرت معصومه", "religious"),
            
            # ولادت امام رضا
            (current_year, 9, 11, "ولادت امام رضا", "religious"),
            
            # چهلم امام حسین
            (current_year, 9, 20, "اربعین حسینی", "religious"),
            
            # شهادت امام حسن
            (current_year, 10, 2, "شهادة الإمام الحسن", "religious"),
            
            # شهادت امام حسین
            (current_year, 10, 10, "عاشورای حسینی", "religious"),
            
            # شهادت امام زاده
            (current_year, 11, 30, "شهادة الإمام زاده", "religious"),
            
            # ولادت پیامبر و امام جعفر صادق
            (current_year, 12, 20, "میلاد پیامبر و امام جعفر صادق", "religious"),
            
            # شهادت امام حسن
            (current_year, 12, 28, "شهادت امام حسن مجتبی", "religious"),
        ]
        
        count = 0
        for year, month, day, title, htype in holidays:
            try:
                # تبدیل تاریخ شمسی به میلادی
                jalali_date = jdatetime.date(year, month, day)
                gregorian_date = jalali_date.togregorian()
                
                # ایجاد یا بروزرسانی تعطیلی
                holiday, created = Holiday.objects.get_or_create(
                    date=gregorian_date,
                    defaults={
                        'title': title,
                        'holiday_type': htype,
                        'is_active': True
                    }
                )
                
                if created:
                    count += 1
                    self.stdout.write(self.style.SUCCESS(f'✓ اضافه شد: {jalali_date} - {title}'))
                else:
                    self.stdout.write(self.style.WARNING(f'⚠️ قبلاً وجود داشت: {jalali_date} - {title}'))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ خطا در {year}/{month}/{day}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ مجموعاً {count} تعطیلی اضافه شد'))