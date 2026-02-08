from .base import BudgetBaseTestCase
from django.test import TestCase
from budgetdb.utils import serialize_ofx
from crum import impersonate
from budgetdb.models import Transaction, Account, AccountHost, Currency, Preference
from budgetdb.utils import analyze_ofx_serialized_data
from django.contrib.auth import get_user_model
from datetime import datetime

User = get_user_model()


# Mocking an OFX object for testing without a real file
class MockOFX:
    def __init__(self, amount, institution=None):
        self.account = type('obj', (object,), {
            'number': '123',
            'statement': type('obj', (object,), {
                'transactions': [
                    type('obj', (object,), {
                        'id': 'fit1', 'amount': amount, 
                        'date': type('obj', (object,), {'strftime': lambda s, f: '2024-01-01'}),
                        'memo': 'Test Tx', 'payee': None
                    })
                ]
            })
        })
        if institution:
            self.institution = institution

class OFXLogicTest(BudgetBaseTestCase):
    def setUp(self):
        self.currency_a = Currency.objects.create(
            name="canadian", 
            name_short="CAD",
            symbol="$",
            priority=1
        ) 
        self.user_a = User.objects.create(
            email='user_a@example.com', 
            first_name='UserA',
            is_active=True
        )
        self.user_a.set_password('password123') # Manually hash the password
        self.user_a.save()
        self.preference_a = Preference.objects.create(
            user=self.user_a,
            slider_start=datetime(2026,1,1), 
            slider_stop=datetime(2026,2,1),
            timeline_start=datetime(2026,3,1),
            timeline_stop=datetime(2026,4,1),
            currency_prefered_id=self.currency_a.id
        ) 


        # Use impersonate so the manager allows the creation
        with impersonate(self.user_a):


            self.host_a = AccountHost.objects.create(
                name="Test Host", 
                owner=self.user_a
            ) 
            self.acc_a = Account.objects.create(
                name="Test Account", 
                account_host=self.host_a,
                currency=self.currency_a,
                owner=self.user_a
            )    

    def test_signage_flipping(self):
        """Test that amount is inverted when flip_ofx_sign is True"""
        acc = Account.objects.create(name="CC", flip_ofx_sign=True)
        mock_ofx = MockOFX(amount="50.00")
        
        data, _, _ = serialize_ofx(mock_ofx, acc)
        self.assertEqual(data[0]['amount'], -50.0)

    def test_metadata_extraction(self):
        """Test that ORG and FID are captured correctly"""
        inst = type('obj', (object,), {'organization': 'BankA', 'fid': '999'})
        mock_ofx = MockOFX(amount="10.00", institution=inst)
        
        _, org, fid = serialize_ofx(mock_ofx)
        self.assertEqual(org, "BankA")
        self.assertEqual(fid, "999")


    def test_manual_match_detection(self):
        """Existing manual tx without fit_id should be flagged as 'match'"""
        Transaction.objects.create(
            account_source=self.acc_a,
            amount_actual=-25.0,
            date_actual="2024-02-01",
            fit_id=None # Manual entry
        )
        
        serialized = [{
            'fit_id': 'BANK_ID_99',
            'amount': -25.0,
            'date': '2024-02-01',
            'description': 'Groceries'
        }]
        
        results = analyze_ofx_serialized_data(serialized, self.acc_a)
        self.assertEqual(results[0]['status'], "match")
        self.assertIsNotNone(results[0]['existing_id'])