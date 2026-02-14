from django.db import models

class ContactMessage(models.Model):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class SalonSettings(models.Model):
    birthday_discount_enabled = models.BooleanField(default=True)

    birthday_discount_percent = models.PositiveIntegerField(default=20)

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
