from crum import impersonate, get_current_user
from .base import BudgetBaseTestCase
from budgetdb.models import Transaction, Account
from django.urls import reverse
from decimal import Decimal

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