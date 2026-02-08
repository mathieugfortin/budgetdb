from decimal import Decimal
from django.urls import reverse
from .base import BudgetBaseTestCase
from budgetdb.models import Transaction

class OFXImportTests(BudgetBaseTestCase):

    def test_confirm_import_saves_transactions(self):
        """Test that POSTing to confirm_import creates Transaction records."""
        # 1. Mock session data
        session = self.client.session
        session['ofx_import_data'] = [
            {'amount': -50.00, 'date': '2026-02-01', 'description': 'Grocery Store', 'fit_id':'1234'},
            {'amount': 1200.00, 'date': '2026-02-02', 'description': 'Paycheck', 'fit_id':'2345'}
        ]
        session['ofx_account_id'] = self.acc_b.ofx_acct_id

        session.save()

        # 2. Act: Confirm both transactions (indices 0 and 1)
        url = reverse('budgetdb:upload_transactions_OFX') # Or your specific confirm URL
        response = self.client.post(url, {
            'description': 'Test Transaction',  # Add this!
            'confirm_import': 'true',
            'import_idx': [0, 1],
            'verify_signage': 'on' # Test the flip logic
        })

        # 3. Assert: Signage should be flipped (-50 becomes 50, 1200 becomes -1200)
        self.assertEqual(Transaction.objects.count(), 2)
        grocery_tx = Transaction.objects.get(description='Grocery Store')
        self.assertEqual(grocery_tx.amount_actual, Decimal('50.00'))
        
        paycheck_tx = Transaction.objects.get(description='Paycheck')
        self.assertEqual(paycheck_tx.amount_actual, Decimal('-1200.00'))
