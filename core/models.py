from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.validators import RegexValidator
from django.templatetags.static import static
from datetime import timedelta

#  تنظیمات سالن
class SalonSettings(models.Model):
    salon_name = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    phone = models.CharField(
        max_length=11,
        validators=[
            RegexValidator(
                regex=r'^(09\d{9}|0\d{10})$',
                message="شماره معتبر وارد کنید (موبایل یا تلفن ثابت)"
            )
        ]
    )
    instagram = models.CharField(max_length=100, blank=True, null=True)
    whatsapp = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        verbose_name="شماره واتس‌اپ",
        help_text="مثال: 989123456789 (بدون + و با کد کشور)",
        validators=[
        RegexValidator(
            regex=r'^989\d{9}$',
            message="شماره واتساپ باید به صورت 989xxxxxxxxx باشد"
        )
        ]
    )
    open_time = models.TimeField(default="09:00")
    close_time = models.TimeField(default="18:00")

    # تنظیمات استراحت پرسنل و تعطیلی موقت
    has_salon_lunch_break = models.BooleanField(default=False, verbose_name="تعطیل ناهار کل سالن")
    salon_lunch_start = models.TimeField(default='13:00', verbose_name="شروع ناهار سالن")
    salon_lunch_end = models.TimeField(default='14:00', verbose_name="پایان ناهار سالن")
    
    # تنظیمات روزهای تعطیل هفتگی
    weekend_days = models.JSONField(default=list, verbose_name="روزهای تعطیل هفتگی")
    # مثال: ["جمعه", "شنبه"]

    enable_online_payment = models.BooleanField(
        default=False,
        verbose_name="فعال بودن پرداخت آنلاین"
    )

    # فاصله تایم‌اسلات‌های رزرو (مثلا هر ۱۵ دقیقه یه نوبت)!!
    booking_interval = models.IntegerField(default=15)

    global_duration_note = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="توضیح سراسری مدت زمان"
    )

    global_price_note = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="توضیح سراسری قیمت"
    )

    class Meta:
        verbose_name = "تنظیمات سالن"
        verbose_name_plural = "تنظیمات سالن"
    
    def __str__(self):
        return "تنظیمات سالن زیبایی نورا"


#برای مدیریت پکیج‌های ویژه و تخفیف‌دار
class Package(models.Model):
    
    title = models.CharField(max_length=100, verbose_name="عنوان پکیج")
    description = models.TextField(verbose_name="توضیحات")

    #قیمت اصلی میتونه خالی باشه ( مثل وقتی که روش تخفیف نیست)
    original_price = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="قیمت اصلی (تومان)"
    )
    
    discounted_price = models.PositiveIntegerField(verbose_name="قیمت تخفیف‌خورده (تومان)")
    discount_badge = models.CharField(
        max_length=50, blank=True, verbose_name="برچسب تخفیف (مثل: ۲۵٪ تخفیف)"
    )
    
    image = models.ImageField(upload_to='packages/', verbose_name="عکس پکیج", blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name="فعال باشد؟")
    
    # اضافه کردن ارتباط با خدمت
    #چون یه پکیج میتونه چندتا سرویس داشته باشه، و یه سرویس هم تو چندتا پکیج باشه
    service = models.ManyToManyField(
        'services_app.Service', 
        verbose_name="خدمت مرتبط",
        related_name="packages",
       
        blank=True
    )

    # فیلدهای تخفیف موقت ( زمان دار)
    is_limited_time = models.BooleanField(
        default=False, verbose_name="تخفیف موقت باشد؟"
    )
    duration_days = models.PositiveSmallIntegerField(
        default=3, verbose_name="مدت زمان تخفیف (به روز)"
    )

    #    برای نمایش در صفحه اصلی
    show_on_homepage = models.BooleanField(
        default=True,
        verbose_name="نمایش در سایت"
    )
    
    # زمان استارت تخفیف برای محاسبه اتوماتیک انقضا تو بک‌اند
    start_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="زمان شروع تخفیف"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True,
        verbose_name="تاریخ ایجاد"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        null=True,
         blank=True,
        verbose_name="آخرین بروزرسانی"
    )

    #در قسمت فرانت لازم نیست چک کنه ببینه عکس هست یا نه،اگر نباشه ما خودمون میدیم
    @property
    def image_url(self):

        if self.image:
            return self.image.url
        return static('images/package.jpg')

    # محاسبه زمان باقی مانده
    @property
    def time_remaining(self):
        if not self.is_limited_time or not self.start_time:
            return None
                
        # تاریخ انقضا = زمان شروع + تعداد روزهای اعتبار
        end_time = self.start_time + timedelta(days=self.duration_days)
        # اینکه کی تموممیشه و چند روز مونده ازش
        remaining = end_time - timezone.now()
        
        if remaining.total_seconds() <= 0:
            return "منقضی شده"
        
        days = remaining.days
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60
        
        return f"{days} روز، {hours} ساعت، {minutes} دقیقه"
    
    class Meta:
        verbose_name = "پکیج"
        verbose_name_plural = "پکیج‌ها"

    def __str__(self):
        return self.title

# برای رزرو خدمات پکیج  
class PackageBooking(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    service = models.ForeignKey('services_app.Service', on_delete=models.CASCADE)
    # (برای تکمیل رزرو اون خدمت از پکیج استفاده میشه)
    is_completed = models.BooleanField(default=False)

