import pytest
from crum import impersonate, get_current_user
from .base import BudgetBaseTestCase
from budgetdb.models import Transaction, Account
from django.urls import reverse
from decimal import Decimal

from django.utils import timezone
from datetime import timedelta

@pytest.mark.django_db
class TestSoftDelete_features:
    def test_soft_delete_transaction(self, client, user_a, acc_a, cad):
        """Verify transaction is flagged as deleted rather than purged."""

        # 1. Setup the transaction using fixtures
        with impersonate(user_a):
            tx = Transaction.objects.create(
                description="soft delete test",
                account_source=acc_a,
                amount_actual=Decimal('100.00'),
                date_actual=acc_a.date_open,
                currency=cad,
            )
            
            # 2. Execute the delete via the view
            # Note: 'client' is a built-in pytest-django fixture
            client.force_login(user_a) 
            url = reverse('budgetdb:delete_transaction', kwargs={'pk': tx.pk})
            client.post(url)
            
            # 3. Check Visibility via Managers
            active_exist_view = Transaction.view_objects.for_user(user_a).filter(pk=tx.pk).exists()
            active_exist_admin = Transaction.admin_objects.for_user(user_a).filter(pk=tx.pk).exists()

        # 4. Final Assertions
        tx.refresh_from_db()
        assert tx.is_deleted is True
        assert active_exist_view is False
        assert active_exist_admin is False

    @pytest.mark.parametrize("account_name, expected_deleted, view_exists, admin_exists", [
        ("acc_a", True,  False, False), # Good friend: Can delete
        ("acc_b", False, True,  False), # Bad friend: View only, no delete
        ("acc_c", False, False, False), # Not friend: No view, no delete
    ])
    def test_soft_delete_scenarios(self, client, user_a, user_friend, cad, 
                                   request, account_name, expected_deleted, 
                                   view_exists, admin_exists):
        """Consolidated test for various friend permission levels."""
        
        # Dynamically get the account fixture by name
        # (Assuming you have acc_a, acc_b, acc_c fixtures in conftest)
        account = request.getfixturevalue(account_name)

        # 1. Setup Transaction as Owner
        with impersonate(user_a):
            tx = Transaction.objects.create(
                description="soft delete test",
                account_source=account,
                amount_actual=Decimal('100.00'),
                date_actual=account.date_open,
                currency=cad,
            )
        url = reverse('budgetdb:delete_transaction', kwargs={'pk': tx.pk})

        # 2. Action as Friend
        client.force_login(user_friend)
        with impersonate(user_friend):
            client.post(url)
            
            # Check visibility
            exists_v = Transaction.view_objects.for_user(user_friend).filter(pk=tx.pk).exists()
            exists_a = Transaction.admin_objects.for_user(user_friend).filter(pk=tx.pk).exists()

        # 3. Assertions
        tx.refresh_from_db()
        assert tx.is_deleted == expected_deleted
        assert exists_v == view_exists
        assert exists_a == admin_exists

    def test_soft_delete_audit_trail(self, user_a, acc_a, cad):
        """Verify that soft_delete sets the flag, timestamp, and user."""
        # 1. Setup the transaction
        with impersonate(user_a):
            tx = Transaction.objects.create(
                description="Audit Test",
                account_source=acc_a,
                amount_actual=Decimal('50.00'),
                date_actual=acc_a.date_open,
                currency=cad,
            )

            # 2. Action: Perform soft delete
            tx.soft_delete()

        # 3. Assertions
        tx.refresh_from_db()
        assert tx.is_deleted is True
        assert tx.deleted_by == user_a
        
        # Check that deleted_at is very recent
        assert (timezone.now() - tx.deleted_at) < timedelta(seconds=10)

    def test_soft_undelete_clears_audit_trail(self, user_a, acc_a, cad):
        """Verify that undelete restores the object and clears timestamps."""
        # 1. Setup a pre-deleted transaction
        with impersonate(user_a):
            tx = Transaction.objects.create(
                description="Undelete Test",
                is_deleted=True,
                deleted_at=timezone.now(),
                deleted_by=user_a,
                account_source=acc_a,
                amount_actual=Decimal('1.00'),
                date_actual=acc_a.date_open,
                currency=cad,
            )
            
            # 2. Action: Undelete
            tx.soft_undelete()
            
        # 3. Assertions
        tx.refresh_from_db()
        assert tx.is_deleted is False
        assert tx.deleted_at is None
        assert tx.deleted_by is None
