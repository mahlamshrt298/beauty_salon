from django.urls import path
from . import views

app_name = 'panel'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    # مدیریت نوبت‌ها
    path('bookings/', views.booking_list, name='booking_list'),
    path('bookings/<int:pk>/approve/', views.booking_approve, name='booking_approve'),
    path('bookings/<int:pk>/cancel/', views.booking_cancel, name='booking_cancel'),
    path('bookings/<int:booking_id>/edit/', views.booking_update, name='booking_update'),
    path('today-appointments/', views.today_appointments, name='today_appointments'),
    path('booking/<int:pk>/complete/', views.booking_complete, name='booking_complete'),
    path('booking/<int:pk>/no-show/', views.booking_no_show, name='booking_no_show'),
    path('tomorrow-appointments/', views.tomorrow_appointments, name='tomorrow_appointments'),
    
    # مدیریت خدمات
    path('services/', views.services_list, name='services_list'),
    path('services/add/', views.service_add, name='service_add'),
    path('services/delete/<int:id>/', views.service_delete, name='service_delete'),
    path("service/edit/<int:id>/", views.service_edit, name="service_edit"),
    path("categories/add/", views.category_add, name="category_add"),
    path("subcategories/add/", views.subcategory_add, name="subcategory_add"),
    path("service/image/delete/<int:image_id>/",views.delete_service_image,name="delete_service_image"),
    path('category/delete/<int:id>/', views.service_delete_category, name='service_delete_category'),
    path('subcategory/delete/<int:id>/', views.service_delete_subcategory, name='service_delete_subcategory'),
    path(
        "services/<int:pk>/toggle/",
        views.service_toggle_status,
        name="service_toggle_status"
    ),

    # مدیریت منشی‌ها
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/add/', views.staff_add, name='staff_add'),
    path("staff/edit/<int:id>/", views.staff_edit, name="staff_edit"),
    path("staff/<int:user_id>/status/<str:status>/", views.staff_change_status, name="staff_change_status"),
    path("staff/salon/add/", views.salon_staff_add, name="salon_staff_add"),
    path("salon-staff/<int:staff_id>/status/<str:status>/",views.salon_staff_change_status,name="salon_staff_change_status"),
    path("salon-staff/edit/<int:id>/",views.salon_staff_edit,name="salon_staff_edit"),

    path("messages/", views.messages_manage, name="messages_manage"),

    path("no-access/", views.no_access, name="no_access"),

    # 👇 مدیریت خدمات پرطرفدار
    path('popular-services/', views.popular_services_list, name='popular_services_list'),
    path('popular-services/add/', views.popular_service_add, name='popular_service_add'),
    path('popular-services/<int:pk>/edit/', views.popular_service_edit, name='popular_service_edit'),
    path('popular-services/<int:pk>/delete/', views.popular_service_delete, name='popular_service_delete'),

    # مدیریت مقالات
    path('articles/', views.article_list, name='article_list'),
    path('articles/add/', views.article_add, name='article_add'),
    path('articles/<int:pk>/edit/', views.article_edit, name='article_edit'),
    path('articles/<int:pk>/delete/', views.article_delete, name='article_delete'),

    # مدیریت دسته‌بندی مقالات
    path('article-categories/', views.article_category_list, name='article_category_list'),
    path('article-categories/add/', views.article_category_add, name='article_category_add'),
    path('article-categories/<int:pk>/edit/', views.article_category_edit, name='article_category_edit'),
    path('article-categories/<int:pk>/delete/', views.article_category_delete, name='article_category_delete'),

    #نظرات مشتریان
    path('reviews/', views.panel_review_list, name='review_list'),
    path('reviews/<int:pk>/approve/', views.review_approve, name='review_approve'),
    path('reviews/<int:pk>/reject/', views.review_reject, name='review_reject'),
    path("reviews/<int:pk>/reply/", views.review_reply, name="review_reply"),

    #کد تخفیف
    path('discount-codes/', views.discount_codes, name='discount_codes'),
    # panel/urls.py
    path('discount-codes/add/', views.discount_code_create, name='discount_code_add'),
    path('discount-codes/<int:pk>/edit/', views.discount_code_edit, name='discount_code_edit'),

    #تعطیلات
    # مدیریت تعطیلات
    path('holidays/', views.holiday_list, name='holiday_list'),
    path('holidays/create/', views.holiday_create, name='holiday_create'),
    path('holidays/<int:pk>/edit/', views.holiday_edit, name='holiday_edit'),
    path('holidays/<int:pk>/delete/', views.holiday_delete, name='holiday_delete'),
    path('holidays/<int:pk>/toggle-active/', views.holiday_toggle_active, name='holiday_toggle_active'),

#تنظیمات سالن
    path('settings/salon/', views.salon_settings, name='salon_settings'),

    # مدیریت پکیج‌ها - پیشنهاد های ویژه
    path('packages/', views.package_list, name='package_list'),
    path('packages/add/', views.package_add, name='package_add'),
    path('packages/<int:pk>/edit/', views.package_edit, name='package_edit'),
    path('packages/<int:pk>/delete/', views.package_delete, name='package_delete'),
    path('packages/<int:pk>/resend/', views.package_resend_notification, name='package_resend'),

    # مدیریت پرداخت‌ها
    path('payments/', views.payment_list, name='payment_list'),

    #گزارش درامد
    path('reports/income/', views.income_report, name='income_report'),

]
