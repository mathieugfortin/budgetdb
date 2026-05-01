from django.apps import AppConfig


class BudgetdbConfig(AppConfig):
    name = 'budgetdb'

    def ready(self):
        from django.contrib.auth import get_user_model
        from auditlog.registry import auditlog
        import budgetdb.scheduler as scheduler
        User = get_user_model()
        auditlog.register(User, mask_fields=['password'])
        scheduler.start()