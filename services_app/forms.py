from django import forms
from .models import Service, ServiceImage, Subcategory

class ServiceForm(forms.ModelForm):
    duration_hours = forms.IntegerField(
        label="ساعت",
        required=False,
        min_value=0,
        initial=0
    )

    duration_extra_minutes = forms.IntegerField(
        label="دقیقه",
        required=False,
        min_value=0,
        max_value=59,
        initial=0
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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

# اگر در حالت ویرایش هستیم مقدار رو پر کن
        if self.instance.pk:
            total_minutes = self.instance.duration_minutes
            self.fields['duration_hours'].initial = total_minutes // 60
            self.fields['duration_extra_minutes'].initial = total_minutes % 60

        # اول زیر‌دسته رو خالی کن
        self.fields['subcategory'].queryset = Subcategory.objects.none()

        # وقتی کاربر دسته انتخاب کرده (POST یا AJAX)
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
    
    def save(self, commit=True):
        instance = super().save(commit=False)

        hours = self.cleaned_data.get('duration_hours') or 0
        minutes = self.cleaned_data.get('duration_extra_minutes') or 0

        instance.duration_minutes = (hours * 60) + minutes

        if commit:
            instance.save()

        return instance
    
# "slug",

class ServiceGalleryForm(forms.ModelForm):
    class Meta:
        model = ServiceImage
        fields = [ "alt_text"]
        labels = {
            
            'alt_text': 'متن جایگزین (اختیاری)',
        }
    