# budgetdb/tests/base.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from crum import impersonate
from budgetdb.models import Account, AccountHost, Currency, Preference
from datetime import date


User = get_user_model()

class BudgetBaseTestCase(TestCase):
    def setUp(self):
        # 1. Create User using your custom UserManager logic
        # Note: We use .create() because your model has username=None
        self.user_a = User.objects.create(
            email='owner@example.com', 
            first_name='test_user_a_Owner',
            is_active=True,
            email_verified=True
        )
        self.user_a.set_password('secret')
        self.user_a.save()

        self.user_b = User.objects.create(
            email='admin@example.com', 
            first_name='test_user_b_Admin'
        )

        # 2. Setup Hierarchical Data
        with impersonate(self.user_a):
            self.cad = Currency.objects.create(
                name="Canadian Dollar", 
                symbol="$", 
                priority=1
            )
            
            # Preference is required because your Account.__str__ looks it up
            self.pref = Preference.objects.create(
                user=self.user_a,
                slider_start=date(2026, 1, 1),
                slider_stop=date(2026, 12, 31),
                currency_prefered=self.cad
            )

            self.host = AccountHost.objects.create(
                name="RBC", 
                owner=self.user_a
            )

            self.acc_a = Account.objects.create(
                name="Main Checking",
                account_host=self.host,
                currency=self.cad,
                owner=self.user_a,
                ofx_account_id = '1234',
                ofx_org = 'orga',
                date_open=date(2026, 1, 1)
            )

            self.acc_b = Account.objects.create(
                name="Main Credit Card",
                account_host=self.host,
                currency=self.cad,
                owner=self.user_a,
                ofx_flip_sign=True,
                ofx_account_id = '2345',
                ofx_org = 'orga',
                date_open=date(2026, 1, 1)
            )