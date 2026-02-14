from services_app import views
from django.urls import path

app_name = 'services_app'
urlpatterns = [
    path('', views.services_list,name='service'),
    #path('<int:pk>/', views.service_detail, name='service_detail'),  
   # path('category/<str:category_slug>/', views.subcategory_list, name='subcategory_list'), # صفحه زیردسته‌ها
   # path('subcategory/<str:subcategory_slug>/', views.service_by_subcategory, name='service_by_subcategory'), # صفحه خدمات یک زیردسته
    #path('<int:pk>/', views.service_detail, name='service_detail'), # صفحه جزئیات خدمت
 
    # مسیرهای AJAX برای انتخاب سلسله‌مراتبی
    path('ajax/get-subcategories/', views.get_subcategories, name='get_subcategories'),
    path('ajax/get-services/', views.get_services, name='get_services'),

]