from decimal import Decimal
from datetime import date
from crum import impersonate
from .base import BudgetBaseTestCase
from budgetdb.models import Transaction, Account
from django.core.exceptions import ValidationError

class viewManagerValidation(BudgetBaseTestCase):
    def test_view_manager_visibility_friend(self):
        view_count = Account.objects.filter(users_view=self.user_friend,is_deleted=False).count()
        admin_count = Account.objects.filter(users_admin=self.user_friend,is_deleted=False).count()
        # with impersonate(self.user_friend):
        visible = Account.view_objects.for_user(self.user_friend).all()
        self.assertEqual(visible.count(), view_count + admin_count)
        self.assertTrue(visible.filter(id=self.acc_a.id).exists())
        self.assertTrue(visible.filter(id=self.acc_b.id).exists())
        self.assertFalse(visible.filter(id=self.acc_c.id).exists())
        self.assertFalse(visible.filter(id=self.acc_da.id).exists())
        self.assertFalse(visible.filter(id=self.acc_db.id).exists())

    def test_view_manager_visibility_owner(self):
        view_count = Account.objects.filter(users_view=self.user_a,is_deleted=False).count()
        admin_count = Account.objects.filter(users_admin=self.user_a,is_deleted=False).count()
        owner_count = Account.objects.filter(owner=self.user_a,is_deleted=False).count()
        #with impersonate(self.user_a):
        visible = Account.view_objects.for_user(self.user_a).all()
        self.assertEqual(visible.count(), view_count + admin_count + owner_count)
        self.assertTrue(visible.filter(id=self.acc_a.id).exists())
        self.assertTrue(visible.filter(id=self.acc_b.id).exists())
        self.assertTrue(visible.filter(id=self.acc_c.id).exists())
        self.assertFalse(visible.filter(id=self.acc_da.id).exists())
        self.assertFalse(visible.filter(id=self.acc_db.id).exists())

class adminManagerValidation(BudgetBaseTestCase):
    def test_admin_manager_visibility_friend(self):
        admin_count = Account.objects.filter(users_admin=self.user_friend,is_deleted=False).count()
        # with impersonate(self.user_friend):
        visible = Account.admin_objects.for_user(self.user_friend).all()
        self.assertEqual(visible.count(), admin_count)
        self.assertTrue(visible.filter(id=self.acc_a.id).exists())
        self.assertFalse(visible.filter(id=self.acc_b.id).exists())
        self.assertFalse(visible.filter(id=self.acc_c.id).exists())
        self.assertFalse(visible.filter(id=self.acc_da.id).exists())
        self.assertFalse(visible.filter(id=self.acc_db.id).exists())

    def test_admin_manager_visibility_owner(self):
        admin_count = Account.objects.filter(users_admin=self.user_a,is_deleted=False).count()
        owner_count = Account.objects.filter(owner=self.user_a,is_deleted=False).count()
        #with impersonate(self.user_a):
        visible = Account.view_objects.for_user(self.user_a).all()
        self.assertEqual(visible.count(), admin_count + owner_count)
        self.assertTrue(visible.filter(id=self.acc_a.id).exists())
        self.assertTrue(visible.filter(id=self.acc_b.id).exists())
        self.assertTrue(visible.filter(id=self.acc_c.id).exists())
        self.assertFalse(visible.filter(id=self.acc_da.id).exists())
        self.assertFalse(visible.filter(id=self.acc_db.id).exists())


class deletedManagerValidation(BudgetBaseTestCase):
    def test_delete_manager_visibility_friend(self):
        view_count = Account.objects.filter(users_view=self.user_friend,is_deleted=True).count()
        admin_count = Account.objects.filter(users_admin=self.user_friend,is_deleted=True).count()
        #with impersonate(self.user_friend):
        visible = Account.view_deleted_objects.for_user(self.user_friend).all()
        self.assertEqual(visible.count(), admin_count + view_count)
        self.assertFalse(visible.filter(id=self.acc_a.id).exists())
        self.assertFalse(visible.filter(id=self.acc_b.id).exists())
        self.assertFalse(visible.filter(id=self.acc_c.id).exists())
        self.assertTrue(visible.filter(id=self.acc_da.id).exists())
        self.assertTrue(visible.filter(id=self.acc_db.id).exists())

    def test_delete_manager_visibility_owner(self):
        view_count = Account.objects.filter(users_view=self.user_a,is_deleted=True).count()
        admin_count = Account.objects.filter(users_admin=self.user_a,is_deleted=True).count()
        owner_count = Account.objects.filter(owner=self.user_a,is_deleted=True).count()
        # with impersonate(self.user_a):
        visible = Account.view_deleted_objects.for_user(self.user_a).all()
        self.assertEqual(visible.count(), view_count + admin_count + owner_count)
        self.assertFalse(visible.filter(id=self.acc_a.id).exists())
        self.assertFalse(visible.filter(id=self.acc_b.id).exists())
        self.assertFalse(visible.filter(id=self.acc_c.id).exists())
        self.assertTrue(visible.filter(id=self.acc_da.id).exists())
        self.assertTrue(visible.filter(id=self.acc_db.id).exists())


class TransactionManagerTests(BudgetBaseTestCase):

    def setUp(self):
        super().setUp()
        # Create a transaction where user_friend is an ADMIN on acc_a 
        # but has NO access to acc_c.
        with impersonate(self.user_a):
            self.tx_active = Transaction.objects.create(
                description="Active Transaction",
                account_source=self.acc_a,       # friend is admin
                account_destination=self.acc_c,  # friend has no access
                amount_actual=Decimal('10.00'),
                date_actual=self.acc_a.date_open,
                currency=self.cad,
            )

            self.tx_deleted = Transaction.objects.create(
                description="Deleted Transaction",
                account_source=self.acc_a,
                account_destination=self.acc_b,
                amount_actual=Decimal('20.00'),
                date_actual=self.acc_a.date_open,
                currency=self.cad,
            )
            self.tx_deleted.soft_delete()

    def test_viewer_manager_active_visibility(self):
        """Friend can see active tx because they admin acc_a."""
        # Using the for_user(user) pattern we built
        active = Transaction.view_objects.for_user(self.user_friend).filter(pk=self.tx_active.pk).exists()
        deleted = Transaction.view_objects.for_user(self.user_friend).filter(pk=self.tx_deleted.pk).exists()
        assert active is True
        # Should NOT see the deleted one in the active view
        assert deleted is False

    def test_deleted_manager_visibility(self):
        """Friend can see deleted tx in the deleted_objects manager."""
        qs = Transaction.view_deleted_objects.for_user(self.user_friend)
        
        self.assertTrue(qs.filter(pk=self.tx_deleted.pk).exists())
        self.assertFalse(qs.filter(pk=self.tx_active.pk).exists())

    def test_admin_manager_permissions(self):
        """Verify AdminManager only shows accounts where user has admin rights."""
        # acc_a: friend is admin -> Should see
        # acc_b: friend is viewer -> Should NOT see if only involving acc_b
        
        with impersonate(self.user_a):
            self.tx_active = Transaction.objects.create(
                description="Active Transaction",
                account_source=self.acc_a,       # friend is admin
                account_destination=self.acc_c,  # friend has no access
                amount_actual=Decimal('10.00'),
                date_actual=self.acc_a.date_open,
                currency=self.cad,
            )

            self.tx_deleted = Transaction.objects.create(
                description="Deleted Transaction",
                account_source=self.acc_a,
                account_destination=self.acc_b,
                amount_actual=Decimal('20.00'),
                date_actual=self.acc_a.date_open,
                currency=self.cad,
            )
            self.tx_deleted.soft_delete()

    def test_viewer_manager_active_visibility(self):
        """Friend can see active tx because they admin acc_a."""
        # Using the for_user(user) pattern we built
        active = Transaction.view_objects.for_user(self.user_friend).filter(pk=self.tx_active.pk).exists()
        deleted = Transaction.view_objects.for_user(self.user_friend).filter(pk=self.tx_deleted.pk).exists()
        assert active is True
        # Should NOT see the deleted one in the active view
        assert deleted is False

    def test_deleted_manager_visibility(self):
        """Friend can see deleted tx in the deleted_objects manager."""
        qs = Transaction.view_deleted_objects.for_user(self.user_friend)
        
        self.assertTrue(qs.filter(pk=self.tx_deleted.pk).exists())
        self.assertFalse(qs.filter(pk=self.tx_active.pk).exists())

    def test_admin_manager_permissions(self):
        """Verify AdminManager only shows accounts where user has admin rights."""
        # acc_a: friend is admin -> Should see
        # acc_b: friend is viewer -> Should NOT see if only involving acc_b
        
        with impersonate(self.user_a):
            tx_viewer_only = Transaction.objects.create(
                description="Viewer Only Acc",
                account_source=self.acc_b, # friend is viewer
                amount_actual=Decimal('5.00'),
                date_actual=self.acc_a.date_open,
                currency=self.cad,
            )

        qs = Transaction.admin_objects.for_user(self.user_friend)
        
        # Can't see tx_active (admin on acc_a but not on acc_c)
        self.assertFalse(qs.filter(pk=self.tx_active.pk).exists())
        # Cannot see tx_viewer_only (only involves acc_b where they are viewer)
        self.assertFalse(qs.filter(pk=tx_viewer_only.pk).exists())

class TransactionAdminManagerValidation(BudgetBaseTestCase):
    pass
