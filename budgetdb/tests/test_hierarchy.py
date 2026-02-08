from decimal import Decimal
from datetime import date
from crum import impersonate
from .base import BudgetBaseTestCase
from budgetdb.models import Account, AccountBalanceDB

class HierarchyLogicTests(BudgetBaseTestCase):

    def test_dirty_flag_bubbles_to_parent(self):
        """Test that setting a child balance to dirty updates the parent's record for that day."""
        with impersonate(self.user_a):
            # 1. Setup: Create a child account
            child_acc = Account.objects.create(
                name="Child Account",
                account_host=self.host,
                currency=self.cad,
                account_parent=self.acc_a, # self.acc_a is the parent from BudgetBaseTestCase
                owner=self.user_a,
                date_open=date(2026, 2, 1)
            )

            # 2. Act: Get a specific day's balance for the child and mark it dirty
            test_day = date(2026, 2, 5)
            child_bal = AccountBalanceDB.objects.get(account=child_acc, db_date=test_day)
            
            # This triggers our defensive save()
            child_bal.balance_is_dirty = True
            child_bal.save()

            # 3. Assert: The parent's record for the same day should now be dirty
            parent_bal = AccountBalanceDB.objects.get(account=self.acc_a, db_date=test_day)
            
            self.assertTrue(
                parent_bal.balance_is_dirty, 
                "Parent balance should be marked dirty when child balance is dirty."
            )

    def test_audit_calculation_with_missing_previous(self):
        """Test that the save() method handles an audit on the very first day (no previous)."""
        with impersonate(self.user_a):
            # Create an account that starts today
            new_acc = Account.objects.create(
                name="Fresh Account",
                account_host=self.host,
                currency=self.cad,
                owner=self.user_a,
                date_open=date(2026, 2, 1)
            )

            # Manually trigger an audit on the opening day
            # This tests the "prev_record = ... .first()" defensive logic
            first_day_bal = AccountBalanceDB.objects.get(account=new_acc, db_date=date(2026, 2, 1))
            first_day_bal.is_audit = True
            first_day_bal.audit = Decimal('150.00')
            
            # This should NOT crash even though there is no record for Jan 31st
            first_day_bal.save()

            self.assertEqual(first_day_bal.balance, Decimal('150.00'))
            self.assertEqual(first_day_bal.delta, Decimal('150.00'))