from django.db import models
from django.contrib.auth.models import User   # برای مدیریت کاربران (اختیاری)
from services_app.models import Service  # ← ایمپورت از services_app
import uuid
from datetime import datetime, timedelta
from django.utils import timezone
import jdatetime
from hijri_converter import convert
from core.models import PackageBooking
from django.templatetags.static import static

# 💇‍♀️ مدل پرسنل (آرایشگرها)
class Staff(models.Model):
    STATUS_CHOICES = [
        ("active", "فعال"),
        ("inactive", "غیرفعال"),
        ("leave", "مرخصی"),
    ]

    full_name = models.CharField(max_length=100)    #نام کامل
    role = models.CharField(max_length=100)     #تخصص
    phone = models.CharField(max_length=20, blank=True, null=False)      #شماره تماس
    photo = models.ImageField(upload_to='staff_photos/', blank=True, null=True)      # عکس پرسنل
    bio = models.TextField(
        blank=True, 
        null=True,
        verbose_name="توضیحات کوتاه",
        help_text="توضیحات نمایشی در صفحه درباره ما (مثلاً: «با ۸ سال سابقه و گواهی بین‌المللی»)"
        )
    work_days = models.JSONField(default=list, blank=True)   # مثال: ["شنبه","یکشنبه","دوشنبه"]
    work_start_time = models.TimeField(default="09:00")     # ساعت شروع
    work_end_time = models.TimeField(default="18:00")   # ساعت پایان
    is_active = models.BooleanField(default=True)        # وضعیت فعال/غیرفعال بودن پرسنل(هنوز هسیا نه)
    status = models.CharField(max_length=10,choices=STATUS_CHOICES,default="active")
    services = models.ManyToManyField(
        Service,
        related_name="staffs",
        blank=True
    )
    show_in_about_page = models.BooleanField(
        default=False,
        verbose_name="نمایش در صفحه درباره ما"
    )

    # فیلدهای تایم ناهار
    has_lunch_break = models.BooleanField(default=True, verbose_name="تعطیل ناهار")
    lunch_start = models.TimeField(default='13:00', verbose_name="شروع ناهار")
    lunch_end = models.TimeField(default='14:00', verbose_name="پایان ناهار")
    
    @property
    def photo_url(self):
        if self.photo:
            return self.photo.url
        return static('images/person.png')

    class Meta:
        verbose_name = "پرسنل"
        verbose_name_plural = "پرسنل‌ها"

    def __str__(self):
        #نمایش  پرسنل در پنل ادمین
        return self.full_name

# مدل تعطیلات
class Holiday(models.Model):
    HOLIDAY_TYPE_CHOICES = [
        ('solar', 'شمسی (ثابت)'),      # مثل نوروز
        ('lunar', 'قمری (متغیر)'),      # مثل عید فطر
        ('custom', 'سفارشی'),
    ]
    
    # فیلدهای جدید برای تعطیلات قمری
    hijri_month = models.IntegerField(null=True, blank=True, verbose_name="ماه قمری")
    hijri_day = models.IntegerField(null=True, blank=True, verbose_name="روز قمری")
    

    date = models.DateField(null=True, blank=True,verbose_name="تاریخ میلادی")
    jalali_date = models.CharField(max_length=10, verbose_name="تاریخ شمسی", blank=True)
    title = models.CharField(max_length=100, verbose_name="عنوان تعطیلی")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    holiday_type = models.CharField(max_length=20, choices=HOLIDAY_TYPE_CHOICES, default='custom')
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    is_half_day = models.BooleanField(default=False, verbose_name="نیم‌روز")
    half_day_period = models.CharField(max_length=10, choices=[('morning', 'صبح'), ('afternoon', 'عصر')], 
                                       blank=True, null=True, verbose_name="بازه نیم‌روز")
    year = models.IntegerField(null=True, blank=True, verbose_name="سال میلادی مربوطه")  # برای فیلتر سریع
    
    class Meta:
        unique_together = [('hijri_month', 'hijri_day', 'year'), ('date',)]  # جلوگیری از تکرار
    
    def __str__(self):
        return f"{self.jalali_date} - {self.title}"
    
    def save(self, *args, **kwargs):
         # اگر تعطیلی قمری باشد، تاریخ میلادی را محاسبه کن
        if self.holiday_type == 'lunar' and self.hijri_month and self.hijri_day and self.year:
            try:
                # تبدیل تاریخ قمری به میلادی (تقریبی)
                hijri_date = convert.Hijri(self.year - 622, self.hijri_month, self.hijri_day)  # تخمین سال هجری
                gregorian = hijri_date.to_gregorian()
                self.date = gregorian
                self.jalali_date = jdatetime.date.fromgregorian(date=gregorian).strftime('%Y/%m/%d')
                self.year = gregorian.year
            except Exception as e:
                print(f"خطا در محاسبه تاریخ قمری: {e}")
         # اگر تعطیلی شمسی باشد، تاریخ میلادی را از تاریخ شمسی محاسبه کن
        elif self.holiday_type == 'solar' and self.jalali_date:
            try:
                year, month, day = map(int, self.jalali_date.split('/'))
                jalali = jdatetime.date(year, month, day)
                self.date = jalali.togregorian()
                self.year = self.date.year
            except:
                pass
        
        super().save(*args, **kwargs)

# 📅 مدل نوبت‌ها
class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'در انتظار تایید'),
        ('confirmed', 'تایید شده'),
        ('cancelled', 'لغو شده'),
        ('completed', 'انجام شده'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # سرویس انتخابی
    service = models.ForeignKey(Service, on_delete=models.SET_NULL,
    null=True,
    blank=True)
    #پرسنلی که کار رو انجام خواهدداد
    staff = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True , blank=True,
        related_name="appointments",
        verbose_name="پرسنل")
    # تاریخ نوبت
    appointment_date = models.DateField()
    # ساعت شروع نوبت
    start_time = models.TimeField()
    # ساعت پایان نوبت
    end_time = models.TimeField()
    # وضعیت نوبت
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    # یادداشت‌های اضافی
    notes = models.TextField(blank=True, null=True)
    #تاریخ ایجاد
    created_at = models.DateTimeField(auto_now_add=True)

    tracking_code = models.CharField(max_length=20, unique=True, blank=True)

    jalali_date = models.CharField(max_length=20, blank=True)

    # ✅ فیلد جدید برای جلوگیری از ارسال تکراری
    reminder_sent = models.BooleanField(default=False, verbose_name="یادآوری ارسال شد")

    # ✅ فیلد جدید برای شماره تماس موقع رزرو
    phone = models.CharField(max_length=11, blank=True, null=True, verbose_name="شماره تماس")

    package_booking = models.ForeignKey(
        PackageBooking,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    service_name_snapshot = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="نام خدمت در زمان رزرو"
    )

    def is_past_and_not_completed(self):
        """اگر تاریخ نوبت گذشته و وضعیت != completed باشد True بر می‌گرداند"""
        today = timezone.localdate()
        return self.appointment_date <  timezone.localdate() and self.status not in ('completed' , 'cancelled')

    def can_cancel_by_user(self):
        appt_datetime = datetime.combine(
            self.appointment_date,
            self.start_time
        )
        appt_datetime = timezone.make_aware(appt_datetime)

        return timezone.now() <= appt_datetime - timedelta(hours=24)

    @property
    def jalali_date_display(self):
        if not self.appointment_date:
            return ""
        return jdatetime.date.fromgregorian(
            date=self.appointment_date
        ).strftime("%Y/%m/%d")

    def save(self, *args, **kwargs):
        if not self.tracking_code:
            # ساخت یک کد رهگیری مختصر و یکتا
            self.tracking_code = str(uuid.uuid4()).split("-")[0].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        #نمایش در پنل ادمین
        return f"{self.user.username} - {self.service.name} ({self.appointment_date})"


# 💳 مدل پرداخت‌ها
class Payment(models.Model):
    #روش پرداخت
    PAYMENT_METHODS = [
        ('online', 'پرداخت آنلاین'),
        ('cash', 'نقدی'),
        ('card', 'کارت‌خوان'),
    ]
    #وضعیت تراکنش
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('success', 'موفق'),
        ('failed', 'ناموفق'),
    ]
     # نوبت مرتبط (یک به یک)
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE)
    #مبلغ
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    ## روش پرداخت
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='online')
    # شماره تراکنش (برای پرداخت آنلاین)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    # وضعیت پرداخت
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    #تاریخ و زمان
    paid_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        #مثل بالایی ها
        return f"پرداخت #{self.id} - {self.status}"

class PendingAppointment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    step = models.CharField(
        max_length=50,
        help_text="مرحله‌ای که کاربر در آن رها کرده"
    )

    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    is_completed = models.BooleanField(default=False)
    reminder_sent = models.BooleanField(default=False)
    def __str__(self):
        return f"{self.user.username} - {self.step}"

class PackagePayment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    package = models.ForeignKey('core.Package', on_delete=models.CASCADE)
    amount = models.PositiveIntegerField()
    
    PAYMENT_METHODS = [
        ('online', 'پرداخت آنلاین'),
        ('cash', 'نقدی'),
    ]
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('success', 'موفق'),
        ('failed', 'ناموفق'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.package.title}"
