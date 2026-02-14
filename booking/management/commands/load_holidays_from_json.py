# booking/management/commands/load_holidays_from_json.py
import json
import os
from django.core.management.base import BaseCommand
from booking.models import Holiday
import jdatetime
from hijri_converter import convert

class Command(BaseCommand):
    help = 'بارگذاری تعطیلات از فایل‌های JSON'
    
    def handle(self, *args, **kwargs):
        current_year = jdatetime.date.today().year
        
        # 1. بارگذاری تعطیلات شمسی
        solar_path = os.path.join('booking', 'data', 'solar_holidays.json')
        if os.path.exists(solar_path):
            with open(solar_path, 'r', encoding='utf-8') as f:
                solar_holidays = json.load(f)
            
            for h in solar_holidays:
                try:
                    year, month, day = map(int, h['jalali_date'].split('/'))
                    jalali_date = jdatetime.date(year, month, day)
                    gregorian_date = jalali_date.togregorian()
                    
                    Holiday.objects.update_or_create(
                        jalali_date=h['jalali_date'],
                        defaults={
                            'title': h['title'],
                            'holiday_type': h['holiday_type'],
                            'date': gregorian_date,
                            'is_active': True,
                            'year': gregorian_date.year
                        }
                    )
                    self.stdout.write(self.style.SUCCESS(f'✓ شمسی: {h["jalali_date"]}'))
                except:
                    pass
        
        # 2. بارگذاری تعطیلات قمری
        lunar_path = os.path.join('booking', 'data', 'lunar_holidays.json')
        if os.path.exists(lunar_path):
            with open(lunar_path, 'r', encoding='utf-8') as f:
                lunar_holidays = json.load(f)
            
            for h in lunar_holidays:
                try:
                    hijri_year = current_year - 621
                    hijri_date = convert.Hijri(hijri_year, h['hijri_month'], h['hijri_day'])
                    gregorian_date = hijri_date.to_gregorian()
                    jalali_date = jdatetime.date.fromgregorian(date=gregorian_date)
                    jalali_str = f"{jalali_date.year}/{jalali_date.month:02d}/{jalali_date.day:02d}"
                    
                    Holiday.objects.update_or_create(
                        hijri_month=h['hijri_month'],
                        hijri_day=h['hijri_day'],
                        year=gregorian_date.year,
                        defaults={
                            'title': h['title'],
                            'holiday_type': 'lunar',
                            'date': gregorian_date,
                            'jalali_date': jalali_str,
                            'is_active': True
                        }
                    )
                    self.stdout.write(self.style.WARNING(f'🌙 قمری: {jalali_str}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'✗ خطا: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ تعطیلات سال {current_year} بارگذاری شد'))