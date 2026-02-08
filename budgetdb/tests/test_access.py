# budgetdb/tests/test_access.py
from .base import BudgetBaseTestCase
from crum import impersonate
from budgetdb.models import Account

class AccessTests(BudgetBaseTestCase):
    def test_admin_manager_visibility(self):
        """Verify that AdminManager correctly filters by user/admin status."""
        # User B should see nothing initially
        with impersonate(self.user_b):
            self.assertEqual(Account.admin_objects.count(), 0)

        # Add User B as an admin
        self.acc_a.users_admin.add(self.user_b)

        # User B should now see the account
        with impersonate(self.user_b):
            self.assertEqual(Account.admin_objects.count(), 1)

    def test_soft_delete_flow(self):
        """Verify soft delete hides from view_objects but keeps in DB."""
        with impersonate(self.user_a):
            self.acc_a.soft_delete()
            self.assertTrue(self.acc_a.is_deleted)
            self.assertEqual(Account.view_objects.count(), 0)
            self.assertEqual(Account.view_deleted_objects.count(), 1)