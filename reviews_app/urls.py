# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.reviews_list, name='reviews'),
    # ثبت نظر برای سرویس خاص
    path('service/<int:service_id>/add/', views.add_review_for_service, name='add_review_for_service'),  

# ✅ حذف نظر توسط کاربر (از پنل)
    path(
        'review/delete/<int:review_id>/',
        views.delete_review,
        name='delete_review'
    ),
    path("review/edit/<int:review_id>/", views.edit_review, name="edit_review"),

]
