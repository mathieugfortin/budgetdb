# services/ledger_service.py

from django.db import transaction
from decimal import Decimal
from django.db.models import Q, Sum
from budgetdb.models import AccountBalanceDB, Transaction, Account

class LedgerService:
    @staticmethod
    @transaction.atomic
    def record_transaction(transaction_instance):
        """Handles saving the transaction and marking balances dirty."""
        transaction_instance.save()
        
        # Mark the specific dates as dirty 
        if transaction_instance.account_source:
            LedgerService.mark_tree_dirty(
                transaction_instance.account_source, 
                transaction_instance.date_actual
            )
        if transaction_instance.account_destination:
            LedgerService.mark_tree_dirty(
                transaction_instance.account_destination, 
                transaction_instance.date_actual
            )


    @classmethod
    def sync_transaction(cls, transaction_instance, is_new, old_date, old_source_id, old_destination_id):
        """
        1. Updates the 'delta' for the specific days/accounts affected.
        2. Flags the balances as dirty for the future.
        """
        if transaction_instance.audit:
            AccountBalanceDB.objects.filter(account=transaction_instance.account_source,db_date=transaction_instance.date_actual).update(is_audit=True,audit=transaction_instance.amount_actual,balance=transaction_instance.amount_actual)

        # Provisioning: Ensure the rows exist for the dates we are about to touch
        # We check both the new date and the old date (if it moved)
        if transaction_instance.account_source:
            transaction_instance.account_source.ensure_records_exist(transaction_instance.date_actual)
            if not is_new and old_date != transaction_instance.date_actual:
                transaction_instance.account_source.ensure_records_exist(old_date)
        
        if transaction_instance.account_destination:
            transaction_instance.account_destination.ensure_records_exist(transaction_instance.date_actual)
            if not is_new and old_date != transaction_instance.date_actual:
                transaction_instance.account_destination.ensure_records_exist(old_date)


        # Identify every (Account, Date) pair that was touched
        impacted_pairs = []
        
        # Current state
        if transaction_instance.account_source:
            impacted_pairs.append((transaction_instance.account_source_id, transaction_instance.date_actual))
        if transaction_instance.account_destination:
            impacted_pairs.append((transaction_instance.account_destination_id, transaction_instance.date_actual))
            
        # Old state (if edited or moved)
        if not is_new:
            if old_source_id:
                impacted_pairs.append((old_source_id, old_date))
            if old_destination_id:
                impacted_pairs.append((old_destination_id, old_date))

        # Remove duplicates (e.g., if only the amount changed, but account/date stayed same)
        unique_pairs = set(impacted_pairs)

        for account_id, work_date in unique_pairs:
            # 1. Update the Delta for this specific day
            cls.refresh_daily_delta(account_id, work_date)
            
            # 2. Flag the future as dirty
            account = Account.objects.get(id=account_id)
            cls.mark_tree_dirty(account, work_date)

    @classmethod
    def sync_transaction_list(cls, transaction_list):
        """
        Calculates the footprint of a list of transactions 
        and syncs the ledger for all affected areas.
        """
        with transaction.atomic():
            #  Identify unique (Account, Date) pairs in the batch
            affected_footprint = set()
            for tx in transaction_list:
                if tx.account_source_id:
                    affected_footprint.add((tx.account_source_id, tx.date_actual))
                if tx.account_destination_id:
                    affected_footprint.add((tx.account_destination_id, tx.date_actual))

            # Find min and max date per account
            account_earliest_dates = {}
            account_lastest_dates = {}
            for account_id, work_date in affected_footprint:
                # identify earliest change per account
                if account_id not in account_earliest_dates or work_date < account_earliest_dates[account_id]:
                        account_earliest_dates[account_id] = work_date
                if account_id not in account_lastest_dates or work_date > account_lastest_dates[account_id]:
                        account_lastest_dates[account_id] = work_date
            
            # Ensure the BALANCES exists for this range
            for account_id, lastest_dates in account_lastest_dates.items():
                account = Account.objects.get(pk=account_id)
                account.ensure_records_exist(lastest_dates)

            # 2. Sync each unique pair once
            for account_id, work_date in affected_footprint:
                cls.refresh_daily_delta(account_id, work_date)

            # 3. Flag the future as dirty
            for account_id, earliest_date in account_earliest_dates.items():
                account = Account.objects.get(pk=account_id)
                # This one call handles the account, its parents, and respects audits
                cls.mark_tree_dirty(account, earliest_date)


    @staticmethod
    def refresh_daily_delta(account_id, work_date):
        """Calculates the sum of ins and outs for ONE account on ONE day."""
        # Sum transactions coming IN to this account
        inflow = Transaction.objects.filter(
            account_destination_id=account_id,
            date_actual=work_date,
            is_deleted=False,
            audit=False
        ).aggregate(total=Sum('amount_actual'))['total'] or Decimal('0.00')

        # Sum transactions going OUT of this account
        outflow = Transaction.objects.filter(
            account_source_id=account_id,
            date_actual=work_date,
            is_deleted=False,
            audit=False
        ).aggregate(total=Sum('amount_actual'))['total'] or Decimal('0.00')

        # Update the delta in the ledger
        # Note: We do NOT update 'balance' here. We leave it dirty.
        AccountBalanceDB.objects.filter(
            account_id=account_id, 
            db_date=work_date
        ).update(delta=(inflow - outflow))

    @classmethod
    def mark_tree_dirty(cls, account, work_date):
        """
        Recursively flags an account and all its ancestors as dirty for a specific date.
        """
        # find the next audit, the dirtying stops there
        next_audit = AccountBalanceDB.objects.filter(
            account=account,
            db_date__gt=work_date,
            is_audit=True
        ).order_by('db_date').first()

        # dirty this account
        update_filter = {
            'account': account,
            'db_date__gte': work_date,
        }
        if next_audit:
            update_filter['db_date__lt'] = next_audit.db_date
        AccountBalanceDB.objects.filter(**update_filter).update(balance_is_dirty=True)

        # 2. If there is a parent, bubble up
        if account.account_parent:
            cls.mark_tree_dirty(account.account_parent, work_date)        