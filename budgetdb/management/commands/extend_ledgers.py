# budgetdb/management/commands/extend_ledger.py
# run this via "python manage.py extend_ledger" on a schedule
from django.core.management.base import BaseCommand
from budgetdb.models import Account
from datetime import date
from dateutil.relativedelta import relativedelta

class Command(BaseCommand):
    help = 'Ensures all active accounts have AccountBalanceDB records for the next 365 days'

    def handle(self, *args, **options):
        target_date = date.today() + relativedelta(years=1)
        active_accounts = Account.objects.filter(date_closed__isnull=True)
        
        for account in active_accounts:
            account.ensure_records_exist(target_date)
            
        self.stdout.write(self.style.SUCCESS('Successfully extended ledgers.'))