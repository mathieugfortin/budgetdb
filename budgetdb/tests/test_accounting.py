from decimal import Decimal
from datetime import date
from crum import impersonate
from .base import BudgetBaseTestCase
from budgetdb.models import Transaction, Account
from django.core.exceptions import ValidationError

class TransactionValidationTests(BudgetBaseTestCase):

    def test_audit_requires_amount(self):
        """Ensure an Audit transaction fails if amount_actual is None."""
        with impersonate(self.user_a):
            tx = Transaction(
                account_source=self.acc_a,
                date_actual=date(2026, 2, 1),
                audit=True,
                amount_actual=None, # This is the problem
                # owner=self.user_a
                currency=self.cad,
                description="test a"
            )
            
            # This should raise a ValidationError
            with self.assertRaises(ValidationError):
                tx.save()

    def test_prevent_self_transfer(self):
        """Ensure we can't send money from an account to itself."""
        with impersonate(self.user_a):
            tx = Transaction(
                account_source=self.acc_a,
                account_destination=self.acc_a, # Same account
                amount_actual=Decimal('10.00'),
                date_actual=date(2026, 2, 1),
                # owner=self.user_a
            )
            
            with self.assertRaises(ValidationError):
                tx.save()

class AccountingTests(BudgetBaseTestCase):
    
    def test_balance_calculation_with_audits(self):
        """Test that balance_by_EOD respects audits and sums transactions correctly."""
        with impersonate(self.user_a):
            # 1. Create an initial Audit (Starting balance of $1000)
            Transaction.objects.create(
                account_source=self.acc_a,
                amount_actual=Decimal('1000.00'),
                date_actual="2026-02-01",
                audit=True,
                currency=self.cad,
                description="test a"
                # owner=self.user_a
            )

            # 2. Add a normal transaction ($200 outflow)
            Transaction.objects.create(
                account_source=self.acc_a,
                amount_actual=Decimal('200.00'),
                date_actual="2026-02-02",
                audit=False,
                currency=self.cad,
                description="test a"
                #owner=self.user_a
            )

            # 3. Verify balance on the 1st (Should be $1000)
            bal_1st = self.acc_a.balance_by_EOD("2026-02-01")
            self.assertEqual(bal_1st, Decimal('1000.00'))

            # 4. Verify balance on the 2nd (1000 - 200 = $800)
            bal_2nd = self.acc_a.balance_by_EOD("2026-02-02")
            self.assertEqual(bal_2nd, Decimal('800.00'))

            # 5. Add a NEW Audit on the 3rd (Hard reset to $500)
            Transaction.objects.create(
                account_source=self.acc_a,
                amount_actual=Decimal('500.00'),
                date_actual="2026-02-03",
                audit=True,
                # owner=self.user_a
                currency=self.cad,
                description="test a"
            )

            # 6. Verify the audit override works
            bal_3rd = self.acc_a.balance_by_EOD("2026-02-03")
            self.assertEqual(bal_3rd, Decimal('500.00'))

    def test_recursive_parent_balance(self):
        """Test that a parent account correctly sums its children's balances."""
        with impersonate(self.user_a):
            # Create a child account
            child_acc = Account.objects.create(
                name="Child Savings",
                account_host=self.host,
                currency=self.cad,
                account_parent=self.acc_a, # Link to Main Checking
                owner=self.user_a,
                date_open="2026-01-01"
            )

            # Put $500 in the child via Audit
            Transaction.objects.create(
                account_source=child_acc,
                amount_actual=Decimal('500.00'),
                date_actual="2026-02-01",
                audit=True,
                # owner=self.user_a
                currency=self.cad,
                description="test a"
            )

            # Put $1000 in the parent via Audit
            Transaction.objects.create(
                account_source=self.acc_a,
                amount_actual=Decimal('1000.00'),
                date_actual="2026-02-01",
                audit=True,
                # owner=self.user_a
                currency=self.cad,
                description="test a"
            )

            # Check parent balance. Your code logic says:
            # If children exist, return SUM of children. 
            # Note: Depending on your exact intent, if the parent has its own 
            # transactions, they might be ignored if children exist.
            parent_bal = self.acc_a.balance_by_EOD("2026-02-02")
            self.assertEqual(parent_bal, Decimal('500.00'))


    def test_recursive_parent_balance_child_is_fresher(self):
        """Test that a parent account correctly sums its children's balances."""
        with impersonate(self.user_a):
            # Create a child account
            child_acc = Account.objects.create(
                name="Child Savings",
                account_host=self.host,
                currency=self.cad,
                account_parent=self.acc_a, # Link to Main Checking
                owner=self.user_a,
                date_open="2026-01-01"
            )

            # Put $500 in the child via Audit
            Transaction.objects.create(
                account_source=child_acc,
                amount_actual=Decimal('500.00'),
                date_actual="2026-02-02",
                audit=True,
                # owner=self.user_a
                currency=self.cad,
                description="test a"
            )

            # Put $1000 in the parent via Audit
            Transaction.objects.create(
                account_source=self.acc_a,
                amount_actual=Decimal('1000.00'),
                date_actual="2026-02-01",
                audit=True,
                # owner=self.user_a
                currency=self.cad,
                description="test a"
            )

            # Check parent balance. Your code logic says:
            # If children exist, return SUM of children. 
            # Note: Depending on your exact intent, if the parent has its own 
            # transactions, they might be ignored if children exist.
            parent_bal = self.acc_a.balance_by_EOD("2026-02-02")
            self.assertEqual(parent_bal, Decimal('500.00'))            

    def test_recursive_parent_balance_parent_is_fresher(self):
        """Test that a parent account correctly sums its children's balances."""
        with impersonate(self.user_a):
            # Create a child account
            child_acc = Account.objects.create(
                name="Child Savings",
                account_host=self.host,
                currency=self.cad,
                account_parent=self.acc_a, # Link to Main Checking
                owner=self.user_a,
                date_open="2026-01-01"
            )

            # Put $500 in the child via Audit
            Transaction.objects.create(
                account_source=child_acc,
                amount_actual=Decimal('500.00'),
                date_actual="2026-02-01",
                audit=True,
                # owner=self.user_a
                currency=self.cad,
                description="test a"
            )

            # Put $1000 in the parent via Audit
            Transaction.objects.create(
                account_source=self.acc_a,
                amount_actual=Decimal('1000.00'),
                date_actual="2026-02-02",
                audit=True,
                # owner=self.user_a
                currency=self.cad,
                description="test a"
            )

            # Check parent balance. Your code logic says:
            # If children exist, return SUM of children. 
            # Note: Depending on your exact intent, if the parent has its own 
            # transactions, they might be ignored if children exist.
            parent_bal = self.acc_a.balance_by_EOD("2026-02-02")
            self.assertEqual(parent_bal, Decimal('1000.00'))            