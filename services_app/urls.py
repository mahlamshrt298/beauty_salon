from services_app import views
from django.urls import path

app_name = 'services_app'
urlpatterns = [
    
    #صفحه لیست همه سرویس ها رو میاره
    path('', views.services_list,name='service'),

    # وقتی دسته انتخاب میشه، یه ریکوست میاد تا زیردسته هاش رو برگردونه
    path('ajax/get-subcategories/', views.get_subcategories, name='get_subcategories'),
    
    #وقتی یه زیر دسته انتخاب میشه، یه ریکوست میاد تا سرویسهاش رو برگردونه
    path('ajax/get-services/', views.get_services, name='get_services'),

]