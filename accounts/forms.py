from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from accounts.models import Profile
import re
from reviews_app.models import Review
from django.core.exceptions import ValidationError
from django.contrib.auth import password_validation
from django.utils.translation import gettext as _

class CustomRegisterForm(UserCreationForm):
    # فرم سفارشی ثبت‌نام با فارسی‌سازی کامل
    email = forms.EmailField(
        label="ایمیل",
        help_text="آدرس ایمیل معتبر خود را وارد کنید (مثال: user@example.com)"
    )
    phone = forms.CharField(
        max_length=11,
        required=True,
        label="شماره موبایل",
        help_text="مثال: 09123456789 (بدون خط‌تیره و با صفر اول)"
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label="نام",
        help_text="نام خود را به فارسی وارد کنید"
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        label="نام خانوادگی",
        help_text="نام خانوادگی خود را به فارسی وارد کنید"
    )

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2:
            if password1 != password2:
                raise ValidationError("رمز عبور و تکرار آن یکسان نیستند.")

            try:
                password_validation.validate_password(password2, self.instance)
            except ValidationError as error:
                error_messages = []
                for e in error.messages:
                    if "too similar" in e:
                        error_messages.append("رمز عبور نباید شبیه نام کاربری یا اطلاعات شخصی شما باشد.")
                    elif "too short" in e:
                        error_messages.append("رمز عبور باید حداقل ۸ کاراکتر باشد.")
                    elif "too common" in e:
                        error_messages.append("این رمز عبور خیلی ساده و قابل حدس است.")
                    elif "entirely numeric" in e:
                        error_messages.append("رمز عبور نباید فقط شامل اعداد باشد.")
                    else:
                        error_messages.append("رمز عبور معتبر نیست.")

                raise ValidationError(error_messages)

        return password2


    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # ✅ فارسی‌سازی کامل فیلدهای ارث‌بری‌شده از UserCreationForm
        self.fields['username'].label = "نام کاربری"
        self.fields['username'].help_text = "نام کاربری باید ۳ تا ۱۵۰ کاراکتر باشد و فقط شامل حروف انگلیسی، اعداد و علائم @ . + - _ باشد"
        
        self.fields['password1'].label = "رمز عبور"
        self.fields['password1'].help_text = "رمز عبور باید حداقل ۸ کاراکتر باشد و ترکیبی از حروف بزرگ، کوچک و اعداد باشد"
        
        self.fields['password2'].label = "تکرار رمز عبور"
        self.fields['password2'].help_text = "رمز عبور را دوباره وارد کنید (برای تأیید)"

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if not re.fullmatch(r'09\d{9}', phone):
            raise forms.ValidationError("شماره موبایل معتبر نیست. لطفاً شماره‌ای معتبر با فرمت 09123456789 وارد کنید.")
        return phone

    def save(self, commit=True):
        user = super().save(commit=commit)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()

        profile, created = Profile.objects.get_or_create(user=user)
        profile.phone = self.cleaned_data["phone"]
        profile.save()

        return user
    
class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(choices=[
                (1, '⭐'),
                (2, '⭐⭐'),
                (3, '⭐⭐⭐'),
                (4, '⭐⭐⭐⭐'),
                (5, '⭐⭐⭐⭐⭐'),
            ]),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'نظر خود را بنویسید...'
            })
        }
