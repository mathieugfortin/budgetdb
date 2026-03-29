import pytest
from decimal import Decimal
from datetime import date
from crum import impersonate
from .base import BudgetBaseTestCase
from budgetdb.models import Account, AccountBalanceDB, Transaction

@pytest.mark.django_db
class TestHierarchyLogic_feature:
    def test_dirty_flag_bubbles_to_parent(self, user_a, acc_a, host_1, cad):
        """Test that setting a child balance to dirty updates the parent's record for that day."""
        with impersonate(user_a):
            # 1. Setup: Create a child account
            child_acc = Account.objects.create(
                name="Child Account",
                account_host=host_1,
                currency=cad,
                account_parent=acc_a,
                date_open=date(2026, 2, 1)
            )

            test_day = date(2026, 2, 5)

            # Get clean balances for parent and child
            child_bal = child_acc.get_balance(test_day)
            parent_bal = acc_a.get_balance(test_day)
            assert AccountBalanceDB.objects.get(account__name='account a',db_date='2026-02-05').balance_is_dirty is False
            assert AccountBalanceDB.objects.get(account__name='child account',db_date='2026-02-05').balance_is_dirty is False

            # This triggers our defensive save()
            with impersonate(user_a):
                tx = Transaction.objects.create(
                    description="Anon Test",
                    receipt=False,
                    verified=False,
                    account_source=child_acc,
                    amount_actual=Decimal('10.00'),
                    date_actual=test_day,
                    currency=cad,
                )
           
            assert AccountBalanceDB.objects.get(account__name='account a',db_date='2026-02-05').balance_is_dirty is True
            assert AccountBalanceDB.objects.get(account__name='child account',db_date='2026-02-05').balance_is_dirty is True
