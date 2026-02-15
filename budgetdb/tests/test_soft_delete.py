from crum import impersonate, get_current_user
from .base import BudgetBaseTestCase
from budgetdb.models import Transaction, Account
from django.urls import reverse
from decimal import Decimal

from django.utils import timezone
from datetime import timedelta


class softDelete(BudgetBaseTestCase):
    def test_soft_delete_transaction(self):
        """Verify transaction is flagged as deleted rather than purged."""

        with impersonate(self.user_a):
            tx = Transaction.objects.create(
                description="soft delete test",
                account_source=self.acc_a,
                amount_actual=Decimal('100.00'),
                date_actual=self.acc_a.date_open,
                currency=self.cad,
            )
            url = reverse('budgetdb:delete_transaction', kwargs={'pk': tx.pk})
            response = self.client.post(url)
            active_exist_view = Transaction.view_objects.for_user(self.user_a).filter(pk=tx.pk).exists()
            active_exist_admin = Transaction.admin_objects.for_user(self.user_a).filter(pk=tx.pk).exists()


        tx.refresh_from_db()
        assert tx.is_deleted is True  # Transaction should be flagged as deleted.
        assert active_exist_view is False # Transaction should not appear through view manager.
        assert active_exist_admin is False # Transaction should not appear through admin manager.

    def test_soft_delete_with_good_friend(self):
        """Verify that a good friend can soft delete."""
 
        with impersonate(self.user_a):
            tx = Transaction.objects.create(
                description="soft delete test",
                account_source=self.acc_a,
                amount_actual=Decimal('100.00'),
                date_actual=self.acc_a.date_open,
                currency=self.cad,
            )
            url = reverse('budgetdb:delete_transaction', kwargs={'pk': tx.pk})

        with impersonate(self.user_friend):
            response = self.client.post(url)
            active_exist_view = Transaction.view_objects.for_user(self.user_friend).filter(pk=tx.pk).exists()
            active_exist_admin = Transaction.admin_objects.for_user(self.user_friend).filter(pk=tx.pk).exists()

        tx.refresh_from_db()              
        assert tx.is_deleted is True  # Transaction should be flagged as deleted.
        assert active_exist_view is False # Transaction should not appear through view manager.
        assert active_exist_admin is False # Transaction should not appear through admin manager.


    def test_soft_delete_with_bad_friend(self):
        """Verifythat a bad friend can only view and not delete."""
       
        with impersonate(self.user_a):
            tx = Transaction.objects.create(
                description="soft delete test",
                account_source=self.acc_b,
                amount_actual=Decimal('100.00'),
                date_actual=self.acc_a.date_open,
                currency=self.cad,
            )
            url = reverse('budgetdb:delete_transaction', kwargs={'pk': tx.pk})

        with impersonate(self.user_friend):
            response = self.client.post(url)
            active_exist_view = Transaction.view_objects.for_user(self.user_friend).filter(pk=tx.pk).exists()
            active_exist_admin = Transaction.admin_objects.for_user(self.user_friend).filter(pk=tx.pk).exists()

        tx.refresh_from_db()
        assert tx.is_deleted is False # Transaction should not be flagged as deleted
        assert active_exist_view is True # Transaction should appear through view manager
        assert active_exist_admin is False # Transaction should not appear through admin manager.


    def test_soft_delete_with_not_friend(self):
        """Verifythat a bad friend can only view and not delete."""
        with impersonate(self.user_a):
            tx = Transaction.objects.create(
                description="soft delete test",
                account_source=self.acc_c,
                amount_actual=Decimal('100.00'),
                date_actual=self.acc_a.date_open,
                currency=self.cad,
            )
            url = reverse('budgetdb:delete_transaction', kwargs={'pk': tx.pk})

        with impersonate(self.user_friend):
            response = self.client.post(url)
            active_exist_view = Transaction.view_objects.for_user(self.user_friend).filter(pk=tx.pk).exists()
            active_exist_admin = Transaction.admin_objects.for_user(self.user_friend).filter(pk=tx.pk).exists()


        tx.refresh_from_db()      
        assert tx.is_deleted is False # Transaction should not be flagged as deleted
        assert active_exist_view is False # Transaction should not appear to unknown users
        assert active_exist_admin is False # Transaction should not appear to unknown users

    def test_soft_delete_audit_trail(self):
        """Verify that soft_delete sets the flag, timestamp, and user."""
        # 1. Setup
        self.client.force_login(self.user_a)
        with impersonate(self.user_a):
            tx = Transaction.objects.create(
                description="Audit Test",
                account_source=self.acc_a,
                amount_actual=Decimal('50.00'),
                date_actual=self.acc_a.date_open,
                currency=self.cad,
            )

        # 2. Action: Perform soft delete
        # (Assuming you have a method/signal or calling it directly)
        with impersonate(self.user_a):
            tx.soft_delete()

        # 3. Assertions
        tx.refresh_from_db()
        self.assertTrue(tx.is_deleted)
        self.assertEqual(tx.deleted_by, self.user_a)
        
        # Check that deleted_at is very recent (within the last 10 seconds)
        now = timezone.now()
        self.assertLess(now - tx.deleted_at, timedelta(seconds=10))

    def test_soft_undelete_clears_audit_trail(self):
        """Verify that undelete restores the object and clears timestamps."""
        with impersonate(self.user_a):
            tx = Transaction.objects.create(
                description="Undelete Test",
                is_deleted=True,
                deleted_at=timezone.now(),
                account_source=self.acc_a,
                amount_actual=Decimal('1.00'),
                date_actual=self.acc_a.date_open,
                currency=self.cad,
            )
            
            tx.soft_undelete()
            
        tx.refresh_from_db()
        self.assertFalse(tx.is_deleted)
        self.assertIsNone(tx.deleted_at)
        self.assertIsNone(tx.deleted_by)