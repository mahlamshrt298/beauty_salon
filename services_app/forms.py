from django import forms
from .models import Service, ServiceImage

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

# "slug",

class ServiceGalleryForm(forms.ModelForm):
    class Meta:
        model = ServiceImage
        fields = [ "alt_text"]
        labels = {
            
            'alt_text': 'متن جایگزین (اختیاری)',
        }
    