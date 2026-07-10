from accounts import views
from django.urls import path
from django.urls import reverse_lazy
from .views import MyPasswordChangeView, CustomPasswordResetView
from django.contrib.auth import views as auth_views

urlpatterns = [
    #صفحه ثبت‌نام
    path('register', views.register,name='register'),   
    
    path('login/',views.login_view,name='login'),
    
    #صفحه خروج
    path('logout/', views.custom_logout, name='logout'),
    
    path('profile/', views.profile, name='profile'),

    # مسیرهای تغییر رمز عبور (برای کاربر لاگین شده)
    path('password_change/', MyPasswordChangeView.as_view(),
          name="password_change"),

    path('password_change/done/', 
         auth_views.PasswordChangeDoneView.as_view(template_name='password_change_done.html'),
         name='password_change_done'),

    #  فراموشی رمز (ارسال لینک به ایمیل)
    path('password/reset/', CustomPasswordResetView.as_view(
        template_name='password_reset.html',
        email_template_name='password_reset_email.txt',
        html_email_template_name='password_reset_email.html',
        subject_template_name='password_reset_subject.txt',
        success_url=reverse_lazy('accounts:password_reset_done')  
    ), name='password_reset'),

    # پیام موفقیت ارسال ایمیل
    path('password/reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='password_reset_done.html'
    ), name='password_reset_done'),

    # لینک داخل ایمیل → فرم رمز جدید
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='password_reset_confirm.html',
        success_url=reverse_lazy('accounts:password_reset_complete')
    ), name='password_reset_confirm'),

    # پیام نهایی
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset_complete.html'
    ), name='password_reset_complete'),

    path("notifications/", views.notifications_list, name="notifications_list"),
    path('ajax/add_review/<int:appointment_id>/', views.ajax_add_review, name='ajax_add_review'),
    path('cancel_appointment/<int:appt_id>/', views.cancel_appointment, name='cancel_appointment'),
    
    ]
