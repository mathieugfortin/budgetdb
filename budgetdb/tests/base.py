# budgetdb/tests/base.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from crum import impersonate
from budgetdb.models import Account, AccountHost, Currency, Preference, Cat1, Cat2, CatType
from datetime import date


User = get_user_model()

class BudgetBaseTestCase(TestCase):
    def setUp(self):
        # Note: We use .create() because your model has username=None
        self.user_a = User.objects.create(
            email='owner@example.com', 
            first_name='test_user_a_Owner',
            is_active=True,
            email_verified=True
        )
        self.user_a.set_password('secreta')
        self.user_a.save()

        self.user_b = User.objects.create(
            email='admin@example.com', 
            first_name='test_user_b_Admin'
        )
        self.user_b.set_password('secretb')
        self.user_b.save()

        self.user_bad = User.objects.create(
            email='nobody@example.com', 
            first_name='test_user_bad'
        )
        self.user_bad.set_password('secretbad')
        self.user_bad.save()


        # 2. Setup Hierarchical Data
        with impersonate(self.user_a):
            self.cad = Currency.objects.create(
                name="Canadian Dollar", 
                symbol="$", 
                priority=1
            )
            
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
                ofx_acct_id = '1234',
                ofx_org = 'orga',
                date_open=date(2026, 1, 1)
            )

            self.acc_b = Account.objects.create(
                name="Main Credit Card",
                account_host=self.host,
                currency=self.cad,
                owner=self.user_a,
                ofx_flip_sign=True,
                ofx_acct_id = '2345',
                ofx_org = 'orga',
                date_open=date(2026, 1, 1)
            )
            self.cat_type_a = CatType.objects.create(
                name="catType A",
                owner=self.user_a,
            )
            self.cat1_a = Cat1.objects.create(
                name="cat1 A", 
                owner=self.user_a,
                cattype=self.cat_type_a,
            )
            self.cat1_b = Cat1.objects.create(
                name="cat1 B", 
                owner=self.user_a,
                cattype=self.cat_type_a,
            )
            self.cat1_c = Cat1.objects.create(
                name="cat1 C", 
                owner=self.user_a,
                cattype=self.cat_type_a,
            )
            self.cat2_a1 = Cat2.objects.create(
                name="cat2 A1", 
                cat1=self.cat1_a, 
                cattype=self.cat_type_a,
                owner=self.user_a,
            )
            self.cat2_a2 = Cat2.objects.create(
                name="cat2 A2", 
                cat1=self.cat1_a, 
                cattype=self.cat_type_a,
                owner=self.user_a,
            )            
            self.cat2_a3 = Cat2.objects.create(
                name="cat2 A3", 
                cattype=self.cat_type_a,
                cat1=self.cat1_a, 
                owner=self.user_a,
            )            
            self.cat2_b1 = Cat2.objects.create(
                cattype=self.cat_type_a,
                name="cat2 B1", 
                cat1=self.cat1_b, 
                owner=self.user_a,
            )
            self.cat2_b2 = Cat2.objects.create(
                cattype=self.cat_type_a,
                name="cat2 B2", 
                cat1=self.cat1_b, 
                owner=self.user_a,
            ) 
            self.cat2_c1 = Cat2.objects.create(
                cattype=self.cat_type_a,
                name="cat2 C1", 
                cat1=self.cat1_c, 
                owner=self.user_a,
            )

        with impersonate(self.user_b):
            self.cad = Currency.objects.create(
                name="Canadian Dollar", 
                symbol="$", 
                priority=1
            )
            
            # Preference is required because your Account.__str__ looks it up
            self.pref = Preference.objects.create(
                user=self.user_b,
                slider_start=date(2026, 2, 1),
                slider_stop=date(2026, 11, 30),
                currency_prefered=self.cad
            )

        with impersonate(self.user_bad):
            self.cad = Currency.objects.create(
                name="Canadian Dollar", 
                symbol="$", 
                priority=1
            )
            
            # Preference is required because your Account.__str__ looks it up
            self.pref = Preference.objects.create(
                user=self.user_bad,
                slider_start=date(2026, 2, 1),
                slider_stop=date(2026, 11, 30),
                currency_prefered=self.cad
            )
