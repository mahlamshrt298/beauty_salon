# reviews_app/forms.py
from django import forms
from .models import Review
from booking.models import Appointment
import jdatetime 

#فرم ثبت نظر
class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        # فیلدهای قابل نمایش در فرم
        fields = ['appointment', 'rating', 'comment']
        widgets = {
            'appointment': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'rating': forms.HiddenInput(),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'نظر خود را بنویسید...', 'required': True}),
        }
        labels = {
            'appointment': 'نوبت مربوطه',
            'comment': 'متن نظر',
        }

    def __init__(self, *args, **kwargs):
         # ✅ استخراج user از kwargs قبل از فراخوانی super()
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # ✅ استفاده از self.user به جای user
        if self.user and self.user.is_authenticated:
            # فقط نوبت‌های تکمیل‌شده کاربر فعلی
            self.fields['appointment'].queryset = Appointment.objects.filter(
                user=self.user,
                status='completed'
            ).select_related('service').order_by('-appointment_date')
            
            self.fields['appointment'].label_from_instance = self.appointment_label
            self.fields['appointment'].empty_label = "-- انتخاب نوبت --"
        else:
            self.fields['appointment'].queryset = Appointment.objects.none()
            self.fields['appointment'].empty_label = "ابتدا وارد سایت شوید"
    
    # ✅ متد جدید برای نمایش تاریخ شمسی در لیست نوبت‌ها
    def appointment_label(self, obj):
        # تبدیل تاریخ میلادی به شمسی
        jalali_date = jdatetime.date.fromgregorian(date=obj.appointment_date)
        # فرمت: نام خدمت - تاریخ شمسی (ساعت)
        return f"{obj.service.name} - {jalali_date.strftime('%Y/%m/%d')} ({obj.start_time.strftime('%H:%M')})"