# test_ajax.py
from django.urls import reverse
from django.conf import settings
from budgetdb.tests.base import BudgetBaseTestCase, BudgetBaseTestCase2
from decimal import Decimal
from crum import impersonate,get_current_user
from budgetdb.models import Transaction, Cat1, Cat2
import json
from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY
from django.conf import settings

class TransactionToggleTests(BudgetBaseTestCase2):
    def setUp(self):
        super().setUp()
        # Define URLs here so 'reverse' is called within the test context
        self.url_receipt = reverse('budgetdb:togglereceipttransaction_json')
        self.url_verify = reverse('budgetdb:toggleverifytransaction_json')

    def post_toggle(self, url, pk):
        return self.client.post(
                    url, 
                    {'transaction_id': pk},
                    HTTP_X_REQUESTED_WITH='XMLHttpRequest',
                    ) 

    def test_toggle_updates_database(self):
        
        self.client.force_login(self.user_a)
        with impersonate(self.user_a):
            tx = Transaction.objects.create(
                description="Toggle Test",
                receipt=False,
                verified=False,
                account_source=self.acc_a,
                amount_actual=Decimal('100.00'),
                date_actual=self.acc_a.date_open,
                currency=self.cad,
            )
   
        # receipt
        self.assertEqual(self.post_toggle(self.url_receipt, tx.id).status_code, 200)
        tx.refresh_from_db()
        self.assertTrue(tx.receipt)

        self.assertEqual(self.post_toggle(self.url_receipt, tx.id).status_code, 200)
        tx.refresh_from_db()
        self.assertFalse(tx.receipt)

        # Verified logic
        self.assertEqual(self.post_toggle(self.url_verify, tx.id).status_code, 200)
        tx.refresh_from_db()
        self.assertTrue(tx.verified)

        self.assertEqual(self.post_toggle(self.url_verify, tx.id).status_code, 200)
        tx.refresh_from_db()
        self.assertFalse(tx.verified)

    def test_toggle_unauthenticated(self):
        """Security: Anonymous users should get 401."""
        # Note: No self.client.login() here
        with impersonate(self.user_a):
            tx = Transaction.objects.create(
                description="Anon Test",
                receipt=False,
                verified=False,
                account_source=self.acc_a,
                amount_actual=Decimal('10.00'),
                date_actual=self.acc_a.date_open,
                currency=self.cad,
            )

        # receipt
        self.assertEqual(self.post_toggle(self.url_receipt, tx.id).status_code, 401)
        tx.refresh_from_db()
        self.assertFalse(tx.receipt)
        # Verified logic
        self.assertEqual(self.post_toggle(self.url_verify, tx.id).status_code, 401)
        tx.refresh_from_db()
        self.assertFalse(tx.verified)

    def test_toggle_receipt_invalid_id(self):
        """Edge Case: Sending an ID that doesn't exist."""
        self.client.force_login(self.user_a)

        # receipt
        self.assertEqual(self.post_toggle(self.url_receipt, 99999).status_code, 404)

        # Verified logic
        self.assertEqual(self.post_toggle(self.url_verify,99999).status_code, 404)



    def test_toggle_receipt_by_impostor(self):
        # User bad should not be able to toggle User A's transaction

        with impersonate(self.user_a):
            tx = Transaction.objects.create(
                description="Toggle Test",
                receipt=False,
                account_source=self.acc_a,
                amount_actual=Decimal('100.00'),
                date_actual=self.acc_a.date_open,
                currency=self.cad,
            )


        with impersonate(self.user_bad):
            self.client.login(email='owner@example.com', password='secreta')

            # 3. Simulate the AJAX POST request
            url = reverse('budgetdb:togglereceipttransaction_json')
            response = self.client.post(url, {
                'transaction_id': tx.id
            }, HTTP_X_REQUESTED_WITH='XMLHttpRequest') # Tells Django it's an AJAX call

            # 4. Assertions
            self.assertEqual(response.status_code, 401)
            
            # Refresh the object from the DB to see the change
            tx.refresh_from_db()
            self.assertFalse(tx.receipt, "The receipt status was updated by an impostor!")


class TransactionCategoryAJAXTests(BudgetBaseTestCase):
    def setUp(self):
        super().setUp()
        # Create some categories for testing
        with impersonate(self.user_a):
            self.tx = Transaction.objects.create(
                account_source=self.acc_a,
                amount_actual=Decimal('50.00'),
                date_actual=self.acc_a.date_open,
                description="Test Category AJAX",
                currency=self.cad,
                cat1=self.cat1_a,
                cat2=self.cat2_a1,
            )
            #self.client.login(email='owner@example.com', password='secret')

    def test_update_cat1_resets_cat2(self):
        """Selecting a new Cat1 should save it and nullify Cat2."""
        with impersonate(self.user_a):
            url = reverse('budgetdb:update_transaction_category')
            response = self.client.post(url, {
                'transaction_id': self.tx.id,
                'cat_level': 1,
                'category_id': self.cat1_b.id
            #}, HTTP_X_REQUESTED_WITH='XMLHttpRequest') # Tells Django it's an AJAX call
            })
        self.assertEqual(response.status_code, 200)
        self.tx.refresh_from_db()
        self.assertEqual(self.tx.cat1, self.cat1_b)
        self.assertIsNone(self.tx.cat2, "Cat2 should be reset when Cat1 changes")

    def test_get_cat2_options_filtering(self):
        """API should only return Cat2 objects belonging to the selected Cat1."""
        with impersonate(self.user_a):
            url = reverse('budgetdb:get_cat2_options')
            response = self.client.get(url, {'cat1_id': self.cat1_a.id})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Should find Bus and Train, but NOT Groceries
        options = [opt['name'] for opt in data['options']]
        self.assertIn(self.cat2_a1.name, options)
        self.assertIn(self.cat2_a2.name, options)
        self.assertNotIn(self.cat2_b1.name, options)

    def test_save_cat2_directly(self):
        """Selecting a Cat2 should save without affecting Cat1."""
        with impersonate(self.user_a):
            url = reverse('budgetdb:update_transaction_category')
            response = self.client.post(url, {
                'transaction_id': self.tx.id,
                'cat_level': 2,
                'category_id': self.cat2_a3.id
            })

        self.assertEqual(response.status_code, 200)
        self.tx.refresh_from_db()
        self.assertEqual(self.tx.cat1, self.cat1_a)
        self.assertEqual(self.tx.cat2, self.cat2_a3)