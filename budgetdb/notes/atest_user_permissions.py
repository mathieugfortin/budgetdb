from django.test import TestCase
from crum import impersonate
from budgetdb.models import Transaction, Account
from budgetdb.utils import analyze_ofx_serialized_data
from django.contrib.auth import get_user_model

User = get_user_model()

class AdminManagerTest(TestCase):
    def setUp(self):
        # Create two distinct users
        self.user_a = User.objects.create_user(
            email='user_a@example.com', 
            first_name='UserA',
            password='password123'
        )
        self.user_b = User.objects.create_user(
            email='user_b@example.com', 
            first_name='UserB',
            password='password123'
        )   
        # We must use impersonate even during setup if the Manager 
        # filters during the .create() or subsequent saves.
        with impersonate(self.user_a):
            self.acc_a = Account.objects.create(name="Acc A", owner=self.user_a)
            
        with impersonate(self.user_b):
            self.acc_b = Account.objects.create(name="Acc B", owner=self.user_b)
            # Create a transaction belonging to User B
            self.tx_b = Transaction.objects.create(
                account_source=self.acc_b,
                fit_id="TRANS_UNIQUE_123",
                amount_actual=-10.0,
                date_actual="2024-01-01",
                owner=self.user_b
            )

    def test_duplicate_check_respects_crum_user(self):
        """
        Test that analyze_ofx_serialized_data doesn't see User B's 
        transaction when User A is 'current'.
        """
        serialized_list = [{
            'fit_id': 'TRANS_UNIQUE_123', # Same ID as User B's transaction
            'amount': -10.0,
            'date': '2024-01-01',
            'description': 'Test description'
        }]

        # Use CRUM to tell the Manager that User A is making the request
        with impersonate(self.user_a):
            # If analyze_ofx_serialized_data uses .view_objects (which uses AdminManager logic)
            # it should NOT find User B's transaction.
            results = analyze_ofx_serialized_data(serialized_list, self.acc_a)
            
            self.assertEqual(results[0]['status'], "new", 
                             "User A found User B's transaction but shouldn't have!")

    def test_admin_access_permission(self):
        """Test that a user in 'users_admin' CAN see the transaction."""
        # Add User A as an admin to User B's account
        self.acc_b.users_admin.add(self.user_a)
        
        serialized_list = [{
            'fit_id': 'TRANS_UNIQUE_123',
            'amount': -10.0,
            'date': '2024-01-01',
            'description': 'Test description'
        }]

        with impersonate(self.user_a):
            results = analyze_ofx_serialized_data(serialized_list, self.acc_b)
            # Because User A is now an admin of this account, they should see the duplicate
            self.assertEqual(results[0]['status'], "duplicate")