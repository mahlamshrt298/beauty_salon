from django.contrib import admin
from accounts.models import DiscountCode
# Register your models here.
from .models import SalonSettings

admin.site.register(SalonSettings)

admin.site.register(DiscountCode)