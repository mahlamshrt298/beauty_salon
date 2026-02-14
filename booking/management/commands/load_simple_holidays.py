import json
import os
from django.core.management.base import BaseCommand
from booking.models import Holiday
import jdatetime

class Command(BaseCommand):
    help = 'بارگذاری ساده تعطیلات از JSON'
    
    def handle(self, *args, **kwargs):
        file_path = os.path.join('booking', 'data', 'holidays_1404_final.json')
        
        if not os.path.exists(file_path):
            print('❌ فایل JSON یافت نشد')
            return
        
        with open(file_path, 'r', encoding='utf-8') as f:
            holidays = json.load(f)
        
        # پاک کردن همه تعطیلات قبلی
        Holiday.objects.all().delete()
        print("✅ تعطیلات قبلی پاک شد")
        
        count = 0
        for h in holidays:
            try:
                year, month, day = map(int, h['jalali_date'].split('/'))
                jalali_date = jdatetime.date(year, month, day)
                gregorian_date = jalali_date.togregorian()
                
                Holiday.objects.create(
                    jalali_date=h['jalali_date'],
                    title=h['title'],
                    holiday_type=h['type'],
                    date=gregorian_date,
                    is_active=True
                )
                count += 1
                print(f"✓ {h['jalali_date']} - {h['title']}")
            except:
                print(f"✗ خطا در {h['jalali_date']}")
        
        print(f"\n🎉 {count} تعطیلی بارگذاری شد")
        print("🔥 هر سال فقط فایل JSON رو آپدیت کن")