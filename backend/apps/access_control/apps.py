from django.apps import AppConfig

class AccessControlConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.access_control'
    verbose_name = 'Access Control'

    def ready(self):
        from django.db.models.signals import post_migrate
        from .signals import create_predefined_groups
        # Hook into the post-migration signal to generate default groups
        post_migrate.connect(create_predefined_groups)

