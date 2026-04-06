from django.core.management.base import BaseCommand
from django.db import transaction
from budgetdb.models import Account, Transaction, AccountBalanceDB
from budgetdb.services import LedgerService
from django.db.models import Min, Q

class Command(BaseCommand):
    help = 'Wipes and recalculates the entire AccountBalanceDB from Transaction history.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Starting total ledger rebuild...'))

        with transaction.atomic():
            # 1. Clear the cache
            self.stdout.write('Clearing existing balance records...')
            AccountBalanceDB.objects.all().update(
                delta=0, 
                balance=0, 
                balance_is_dirty=True, 
                is_audit=False, 
                audit=None
            )

            # 2. Identify the footprint of all existing transactions
            self.stdout.write('Identifying transaction footprint...')
            all_tx = Transaction.objects.filter(is_deleted=False)
            
            # We use your existing service logic to refresh deltas
            # This ensures the 'Truth' in Transactions matches the 'Cache' in BalanceDB
            LedgerService.sync_transaction_list(all_tx)

            # 3. Process Accounts Top-Down or Bottom-Up?
            # To ensure parent sums are correct, we must clean Leaf accounts first, 
            # then move up the tree. 
            # We'll sort by 'depth' if you have it, otherwise we'll iterate 
            # and let your recursive 'get_balances' handle it.
            root_accounts = Account.objects.filter(account_parent__isnull=True, is_deleted=False)
                        
            for root in root_accounts:
                self.stdout.write(f'Rebuilding Tree starting at Root: {root.name}')
                
                # Find the earliest transaction in this entire subtree
                # This ensures we cover the full history for the root and all its children
                earliest = Transaction.objects.filter(
                    is_deleted=False
                ).filter(
                    Q(account_source__account_parent=root) | 
                    Q(account_destination__account_parent=root) |
                    Q(account_source=root) |
                    Q(account_destination=root)
                ).aggregate(Min('date_actual'))['date_actual__min']

                if earliest:
                    # This one call will recursively clean every child 
                    # before finishing the parent's calculation.
                    root.get_balances(earliest, datetime.date.today())

        self.stdout.write(self.style.SUCCESS('Successfully rebuilt the ledger hull!'))