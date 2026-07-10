from django.db import models

class SalonSettings(models.Model):
    #کمپین تولد فعال باشه یا نه؟
    birthday_discount_enabled = models.BooleanField(default=True)

    #مبلغ تخفیف برای کمپین تولد چقدر باشه؟
    birthday_discount_percent = models.PositiveIntegerField(default=20)

    #کد تخفیف کمپین تولد تا چند روز بعد از صدور اعتبار داشته باشه؟
    birthday_discount_valid_days = models.PositiveIntegerField(
        default=3,
        help_text="اعتبار کد تخفیف (روز)"
    )

    birthday_notify_days_before = models.PositiveIntegerField(
        default=7,
        help_text="چند روز قبل از تولد اعلان ارسال شود (حداقل 3 روز)"
    )

    def save(self, *args, **kwargs):
        if self.birthday_notify_days_before < 3:
            self.birthday_notify_days_before = 3
        super().save(*args, **kwargs)

    def __str__(self):
        return "تنظیمات تولد و تخفیف"
