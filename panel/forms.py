# panel/forms.py
from django import forms
from accounts.models import DiscountCode
from django.core.exceptions import ValidationError
from django.utils import timezone

class DiscountCodeForm(forms.ModelForm):
    class Meta:
        model = DiscountCode
        fields = [
            "code",          # کد تخفیف
            "percent",       # درصد تخفیف
            "expires_at",    # تاریخ انقضا
            "is_active",
            "extra_message",

        ]
        labels = {
            "code": "کد تخفیف",
            "percent": "درصد تخفیف",
            "expires_at": "تاریخ انقضا",
            "is_active":"فعال باشد؟",
            "extra_message" : "پیام اضافی",
        }
        widgets = {
            "code": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "مثلاً ABC123"
            }),

            "percent": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "مثلاً 20"
            }),

            "expires_at": forms.HiddenInput(),

            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),  # اضافه کن
            
            "extra_message": forms.Textarea(
                attrs={"class": "form-control","rows": 3, "placeholder": "متن دلخواه برای ایمیل"}
            )
        }

    def clean_expires_at(self):
        date = self.cleaned_data.get('expires_at')
        if date and date < timezone.now().date():
            raise ValidationError("تاریخ انقضا نمی‌تواند گذشته باشد")
        return date
