from django import forms
from .models import Service, ServiceImage, Subcategory

class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = [
            "name",
            "description",
            "duration_minutes",
            "price",
            "is_active",
            "category",
            "subcategory",
            "image",
           
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

# "slug",

class ServiceGalleryForm(forms.ModelForm):
    class Meta:
        model = ServiceImage
        fields = [ "alt_text"]
        labels = {
            
            'alt_text': 'متن جایگزین (اختیاری)',
        }
    