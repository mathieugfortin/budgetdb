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
        with impersonate(self.user_friend):
            visible = Account.view_objects.all()
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
        with impersonate(self.user_a):
            visible = Account.view_objects.all()
            self.assertEqual(visible.count(), view_count + admin_count + owner_count)
            self.assertTrue(visible.filter(id=self.acc_a.id).exists())
            self.assertTrue(visible.filter(id=self.acc_b.id).exists())
            self.assertTrue(visible.filter(id=self.acc_c.id).exists())
            self.assertFalse(visible.filter(id=self.acc_da.id).exists())
            self.assertFalse(visible.filter(id=self.acc_db.id).exists())

class adminManagerValidation(BudgetBaseTestCase):
    def test_admin_manager_visibility_friend(self):
        admin_count = Account.objects.filter(users_admin=self.user_friend,is_deleted=False).count()
        with impersonate(self.user_friend):
            visible = Account.admin_objects.all()
            self.assertEqual(visible.count(), admin_count)
            self.assertTrue(visible.filter(id=self.acc_a.id).exists())
            self.assertFalse(visible.filter(id=self.acc_b.id).exists())
            self.assertFalse(visible.filter(id=self.acc_c.id).exists())
            self.assertFalse(visible.filter(id=self.acc_da.id).exists())
            self.assertFalse(visible.filter(id=self.acc_db.id).exists())

    def test_admin_manager_visibility_owner(self):
        admin_count = Account.objects.filter(users_admin=self.user_a,is_deleted=False).count()
        owner_count = Account.objects.filter(owner=self.user_a,is_deleted=False).count()
        with impersonate(self.user_a):
            visible = Account.view_objects.all()
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
        with impersonate(self.user_friend):
            visible = Account.view_deleted_objects.all()
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
        with impersonate(self.user_a):
            visible = Account.view_deleted_objects.all()
            self.assertEqual(visible.count(), view_count + admin_count + owner_count)
            self.assertFalse(visible.filter(id=self.acc_a.id).exists())
            self.assertFalse(visible.filter(id=self.acc_b.id).exists())
            self.assertFalse(visible.filter(id=self.acc_c.id).exists())
            self.assertTrue(visible.filter(id=self.acc_da.id).exists())
            self.assertTrue(visible.filter(id=self.acc_db.id).exists())

class TransactionViewerManagerValidation(BudgetBaseTestCase):
    pass

class TransactionDeletedViewerManagerValidation(BudgetBaseTestCase):
    pass

class TransactionViewerAllManagerValidation(BudgetBaseTestCase):
    pass

class TransactionAdminManagerValidation(BudgetBaseTestCase):
    pass