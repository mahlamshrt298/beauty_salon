from django import forms
from .models import Service, ServiceImage, Subcategory

class ServiceForm(forms.ModelForm):
    HOUR_CHOICES = [(i, str(i)) for i in range(0, 13)]
    
    MINUTE_CHOICES = [
        (0, "00"),
        (15, "15"),
        (30, "30"),
        (45, "45"),
    ]

    duration_hours = forms.ChoiceField(
        label="ساعت",
        choices=HOUR_CHOICES,
        required=False,
        initial=0,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm w-auto d-inline-block'})
    )

    duration_extra_minutes = forms.ChoiceField(
        label="دقیقه",
        choices=MINUTE_CHOICES,
        required=False,
        initial=0,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm w-auto d-inline-block'})
    )

    class Meta:
        model = Service
        fields = [
            "name",
            "description",
            "price",
            "is_active",
            "category",
            "subcategory",
            "image",
           
        ]
        
    def clean(self):
        cleaned_data = super().clean()

        hours = int(cleaned_data.get('duration_hours') or 0)
        minutes = int(cleaned_data.get('duration_extra_minutes') or 0)

        if hours == 0 and minutes == 0:
            raise forms.ValidationError("مدت زمان خدمت نمی‌تواند صفر باشد.")

        return cleaned_data

    def clean_price(self):
        price = self.cleaned_data.get('price')

        if price and price > 10_000_000_000:
            raise forms.ValidationError("قیمت بیش از حد مجاز است.")

        return price


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
         # فاصله بین فیلدها
        for field_name, field in self.fields.items():
            if hasattr(field.widget, 'attrs'):
                field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' mb-2'
        
        # فیلدهای اجباری
        self.fields['name'].required = True
        self.fields['name'].error_messages = {'required': 'نام خدمت الزامی است.'}
        
        self.fields['price'].required = True
        self.fields['price'].error_messages = {'required': 'قیمت الزامی است.'}
        
        self.fields['category'].required = True
        self.fields['category'].error_messages = {'required': 'انتخاب دسته اصلی الزامی است.'}
        
        self.fields['subcategory'].required = True
        self.fields['subcategory'].error_messages = {'required': 'انتخاب زیردسته الزامی است.'}
        
        self.fields['image'].required = True
        self.fields['image'].error_messages = {'required': 'انتخاب عکس اصلی الزامی است.'}

        # اگر در حالت ویرایش هستیم، مقدار زمان رو پر کن
        if self.instance.pk:
            total_minutes = self.instance.duration_minutes
            self.fields['duration_hours'].initial = total_minutes // 60
            self.fields['duration_extra_minutes'].initial = total_minutes % 60

        # اول زیر‌دسته رو خالی کن
        self.fields['subcategory'].queryset = Subcategory.objects.none()

        # وقتی کاربر دسته انتخاب کرده 
        if 'category' in self.data:
            try:
                category_id = int(self.data.get('category'))
                self.fields['subcategory'].queryset = Subcategory.objects.filter(
                    category_id=category_id
                ).order_by('name')
            except (ValueError, TypeError):
                pass

        # وقتی در حالت ویرایش هستیم
        elif self.instance.pk:
            self.fields['subcategory'].queryset = self.instance.category.subcategories.all()
        
        self.fields['price'].widget.attrs.update({
            'class': 'form-control mb-2',
            'max': '10000000000'
        })

        self.fields['price'].label = "حداقل قیمت (تومان)"

        #  اضافه کردن راهنما زیر فیلد
        self.fields['price'].help_text = "قیمت اعلامی حداقل هزینه خدمت است و ممکن است بسته به شرایط افزایش یابد."


    def save(self, commit=True):
        instance = super().save(commit=False)

        #تبدیل مقادیر دراپ‌داون‌ها به عدد
        hours = int(self.cleaned_data.get('duration_hours') or 0 )
        minutes = int(self.cleaned_data.get('duration_extra_minutes') or 0 )

        instance.duration_minutes = (hours * 60) + minutes

        if commit:
            instance.save()

        return instance
    

class ServiceGalleryForm(forms.ModelForm):
    class Meta:
        model = ServiceImage
        fields = [ "alt_text"]
        labels = {
            'alt_text': 'متن جایگزین (اختیاری)',
        }
    