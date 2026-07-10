from django.urls import path
from . import views

urlpatterns = [
    # مسیر اصلی اپلیکیشن: نمایش لیست مقالات (و مدیریت فیلتر/جستجو)
    path('', views.blog_list, name='blog'),
    
     # صفحه جزئیات مقاله
    path('<int:pk>/', views.blog_detail, name='blog_detail'),
    
     # جستجوی زنده
    path('search-suggestions/', views.search_suggestions, name='search_suggestions'),  

]
