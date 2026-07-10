from django.urls import path
from . import views

urlpatterns = [

    #لیست نظرات
    path('', views.reviews_list, name='reviews'),

    #  حذف نظر توسط کاربر (از پنل)
    path(
        'review/delete/<int:review_id>/',
        views.delete_review,
        name='delete_review'
    ),
    
    #ویرایش نظر
    path("review/edit/<int:review_id>/", views.edit_review, name="edit_review"),

]
