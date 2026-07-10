from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        # اورراید کردن متد ready واسه رجیستر کردن سیگنال‌های این اپلیکیشن (accounts)
        import accounts.signals
