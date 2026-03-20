from django.apps import AppConfig


class BudgetdbConfig(AppConfig):
    name = 'budgetdb'

    def ready(self):
            import budgetdb.scheduler as scheduler
            scheduler.start()