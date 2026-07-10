from django import forms
from accounts.models import DiscountCode
from django.core.exceptions import ValidationError
from django.utils import timezone

# برای ساخت و ویرایش کدهای تخفیف
class DiscountCodeForm(forms.ModelForm):
    class Meta:
        model = DiscountCode
        #چیزهایی که  کاربر تو پنل قراره ببینه و پر کنه
        fields = [
            "code",          
            "percent",       
            "expires_at",    # تاریخ انقضا
            "is_active",    
            "extra_message",

        ]
        #لیبل‌های فارسی
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

            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}), 
            
            "extra_message": forms.Textarea(
                attrs={"class": "form-control","rows": 3, "placeholder": "متن دلخواه برای ایمیل"}
            )
        }

    #برای تاریخ انقضا
    def clean_expires_at(self):
        date = self.cleaned_data.get('expires_at')
        #اگه تاریخ وارد شده بود، نباید کوچکتر از تاریخ امروز باشه
        if date and date < timezone.now().date():
            raise ValidationError("تاریخ انقضا نمی‌تواند گذشته باشد")
        return date

    #برای تکراری نبودن کد تخفیف
    def clean_code(self):
        code = self.cleaned_data.get('code')
        qs = DiscountCode.objects.filter(code=code)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(f'کد تخفیف "{code}" از قبل وجود دارد، لطفاً کد دیگری انتخاب کنید.')
        return code
