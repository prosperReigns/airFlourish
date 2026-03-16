from django.apps import AppConfig


class WalletsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.wallets'

    def ready(self):
        import app.wallets.signals
