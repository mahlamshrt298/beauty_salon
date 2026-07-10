from django.db import models
from django.contrib.auth.models import User   
from booking.models import Appointment
from django.core.validators import MaxLengthValidator
from core.utils.date_utils import calculate_age
import jdatetime
from django.core.exceptions import ValidationError

class Notification(models.Model):

    #انواع اعلان‌ها
    TYPE_CHOICES = [
        ('reminder', 'یادآوری'),    # برای یادآوری زمان نوبت
        ('status_change', 'تغییر وضعیت'),    # برای اطلاع‌رسانی تغییر وضعیت نوبت
        ('promotion', 'تبلیغاتی'),       # برای ارسال پیشنهادات ویژه و تبلیغات
    ]

    #از چه طریقی اعلان ارسال بشه؟!!
    CHANNEL_CHOICES = [
        ('sms', 'پیامک'),
        ('email', 'ایمیل'),
        ('whatsapp', 'واتساپ'),
    ]

    STATUS_CHOICES = [
        ('pending', 'در انتظار ارسال'),
        ('sent', 'ارسال شده'),
        ('read', 'خوانده شده'),
        ('failed', 'ناموفق'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
     # می‌تواند خالی باشد برای اعلان‌های عمومی مثل تبلیغات
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, null=True, blank=True)
    
    #نوع اعلان
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
   
   #راه ارسال اعلان
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    
    #متن پیام
    message = models.TextField()
    
  
    discount = models.ForeignKey(
        'accounts.DiscountCode',      # نام اپ و مدل کد تخفیف
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )

    #وضعیت اnotif
    status = models.CharField(max_length=20,choices=STATUS_CHOICES, default='pending')
    
    #تاریخ و زمان ارسال
    sent_at = models.DateTimeField(blank=True, null=True)

     # تاریخ و زمان ایجاد رکورد اعلان (به طور خودکار پر می‌شود)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    @property
    def jalali_created_at(self):
        # تبدیل تاریخ برای نمایش تو فرانت
        if not self.created_at:
            return ""
        return jdatetime.datetime.fromgregorian(
            datetime=self.created_at
        ).strftime("%Y/%m/%d - %H:%M")

    def __str__(self):

        # نمایش خوانا و قابل فهم   در پنل ادمین 
        return f"اعلان به {self.user.username} - {self.type} - {self.status}"
    
    class Meta:
        indexes = [
            models.Index(fields=["user", "is_read"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["status"]),
        ]
        ordering = ["-created_at"]


def validate_image_size(image):
    #چک کردن حجم عکس قبل از آپلود
    max_size = 2 * 1024 * 1024  # 2MB
    if image.size > max_size:
        raise ValidationError("حجم تصویر نباید بیشتر از ۲ مگابایت باشد.")


class Profile(models.Model):
    ROLE_CHOICES = (
        ('owner', 'Owner'),
        ('receptionist', 'Receptionist'),
        ('customer', 'Customer'),
    )

    STATUS_CHOICES = (
        ('active', 'فعال'),
        ('inactive', 'غیرفعال'),
        ('leave', 'مرخصی'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='active'
    )

    phone = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=100, blank=True)          
    bio = models.TextField(blank=True , validators=[MaxLengthValidator(300)])                           
    reminder_enabled = models.BooleanField(default=False)        

    birthday = models.DateField(null=True, blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True , validators=[validate_image_size])
    
    #محدودیت تعداد دفعاتی که یوزر میتونه تاریخ تولدش رو عوض کنه
    birthday_change_count = models.PositiveSmallIntegerField(default=0)


    @property
    def age(self):
        return calculate_age(self.birthday)

    def save(self, *args, **kwargs):
        if not getattr(self, '_already_saving', False):
            self._already_saving = True
            super().save(*args, **kwargs)
            self._already_saving = False
        else:
            super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.user.username} - {self.role} - {self.status}"

class DiscountCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=20, unique=True)
    percent = models.PositiveIntegerField()
    expires_at = models.DateField()
    notification_sent = models.BooleanField(default=False)  
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    discount_type = models.CharField(max_length=20, choices=[('percent','درصد'),('fixed','مبلغ ثابت')],default='percent')
    value          = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_purchase   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active      = models.BooleanField(default=True)
    extra_message = models.TextField(
        "متن اضافه برای ایمیل", blank=True, default=""
    )
    def __str__(self):
        return self.code
    
    @property
    def jalali_notification_sent_at(self):
        if not self.notification_sent_at:
            return None
        return jdatetime.datetime.fromgregorian(
            datetime=self.notification_sent_at
        ).strftime("%Y/%m/%d - %H:%M")


class DiscountUsage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    discount = models.ForeignKey(DiscountCode, on_delete=models.CASCADE)
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # جلوگیری از ثبت رکورد تکراری برای یک یوزر و یک کد مشخص در دیتابیس
        unique_together = ('user', 'discount')

    def __str__(self):
        return f"{self.user.username} - {self.discount.code}"
