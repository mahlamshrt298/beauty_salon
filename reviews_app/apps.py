from django.apps import AppConfig


class ReviewsAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reviews_app'
    
    def ready(self):
        import reviews_app.signals