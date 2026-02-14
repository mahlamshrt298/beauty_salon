from booking import views
from django.urls import path

#مسیرها
urlpatterns = [
    path('reserve/', views.reserve,name='reserve'),
    path('select-date/<int:service_id>/', views.select_date, name='select_date'),
    
    # مسیر با سال و ماه برای تغییر ماه تقویم
    path('select-date/<int:service_id>/<int:year>/<int:month>/', views.select_date, name='select_date_with_month'),
    path("select-date/package/<int:package_id>/", views.select_date_from_package, name="select_date_from_package"),

    path('contact-info/', views.contact_info, name='contact_info'),
    path('payment-confirm/', views.payment_confirm, name='payment_confirm'),
    path('save-selected-service/', views.save_selected_service, name='save_selected_service'),
    path('save-and-redirect/', views.save_and_redirect, name='save_and_redirect'),
    path('get-available-times/', views.get_available_times, name='get_available_times'),
    path('confirmation/<str:tracking_code>/', views.confirmation, name='confirmation'),

    path(
        "ajax/get-available-staff/",
        views.get_available_staff_ajax,
        name="get_available_staff"
    ),

]