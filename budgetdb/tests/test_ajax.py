from django.urls import reverse
from budgetdb.tests.base import BudgetBaseTestCase
from decimal import Decimal
from crum import impersonate,get_current_user
from budgetdb.models import Transaction, Cat1, Cat2
import json

class TransactionToggleTests(BudgetBaseTestCase):

    def test_toggle_receipt_updates_database(self):
        """
        Verify that calling the togglereceipt_json view 
        actually flips the boolean in the database.
        """
        # 1. Setup: Create a transaction that is initially NOT verified/received
        # Note: Using the field names we discussed (check your actual names!)
        with impersonate(self.user_a):
            self.client.login(email='owner@example.com', password='secreta')

            tx = Transaction.objects.create(
                description="Toggle Test",
                receipt=False,
                account_source=self.acc_a,
                amount_actual=Decimal('100.00'),
                date_actual=self.acc_a.date_open,
                currency=self.cad,
            )
            
            # 3. Simulate the AJAX POST request your JS makes
            url = reverse('budgetdb:togglereceipttransaction_json')
            response = self.client.post(url, {
                'transaction_id': tx.id
            }, HTTP_X_REQUESTED_WITH='XMLHttpRequest') # Tells Django it's an AJAX call

            # 4. Assertions
            self.assertEqual(response.status_code, 200)
            
            # Refresh the object from the DB to see the change
            tx.refresh_from_db()
            self.assertTrue(tx.receipt, "The receipt status did not flip to True in the DB")

            # 5. Toggle it back to False
            self.client.post(url, {'transaction_id': tx.id}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            tx.refresh_from_db()
            self.assertFalse(tx.receipt, "The receipt status did not flip back to False")

    def test_toggle_verify_updates_database(self):
        """
        Verify that calling the toggleverify_json view 
        actually flips the boolean in the database.
        """
        # 1. Setup: Create a transaction that is initially NOT verified/received
        # Note: Using the field names we discussed (check your actual names!)
        with impersonate(self.user_a):
            self.client.login(email='owner@example.com', password='secreta')
            
            tx = Transaction.objects.create(
                description="Toggle Test",
                verified=False,
                account_source=self.acc_a,
                amount_actual=Decimal('100.00'),
                date_actual=self.acc_a.date_open,
                currency=self.cad,
            )
            
            # 3. Simulate the AJAX POST request your JS makes
            url = reverse('budgetdb:toggleverifytransaction_json')
            response = self.client.post(url, {
                'transaction_id': tx.id
            }, HTTP_X_REQUESTED_WITH='XMLHttpRequest') # Tells Django it's an AJAX call

            # 4. Assertions
            self.assertEqual(response.status_code, 200)
            
            # Refresh the object from the DB to see the change
            tx.refresh_from_db()
            self.assertTrue(tx.verified, "The receipt status did not flip to True in the DB")

            # 5. Toggle it back to False
            self.client.post(url, {'transaction_id': tx.id}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            tx.refresh_from_db()
            self.assertFalse(tx.verified, "The receipt status did not flip back to False")            


    def test_toggle_receipt_by_impostor(self):
        """
        Verify that calling the togglereceipt_json checks permissions
        """

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


    def test_toggle_verify_by_impostor(self):
        """
        Verify that calling the togglereceipt_json checks permissions
        """
        with impersonate(self.user_a):
            tx = Transaction.objects.create(
                description="Toggle Test",
                verified=False,
                account_source=self.acc_a,
                amount_actual=Decimal('100.00'),
                date_actual=self.acc_a.date_open,
                currency=self.cad,
            )

        with impersonate(self.user_bad):
            self.client.login(email='nobody@example.com', password='secretbad')
            
            # 3. Simulate the AJAX POST request your JS makes
            url = reverse('budgetdb:toggleverifytransaction_json')
            response = self.client.post(url, {
                'transaction_id': tx.id
            }, HTTP_X_REQUESTED_WITH='XMLHttpRequest') # Tells Django it's an AJAX call

            # 4. Assertions
            self.assertEqual(response.status_code, 401)
            
            # Refresh the object from the DB to see the change
            tx.refresh_from_db()
            self.assertFalse(tx.verified, "The verified status was updated by an impostor!")



class TransactionCategoryAJAXTests(BudgetBaseTestCase):
    def setUp(self):
        super().setUp()
        # Create some categories for testing
        self.c1 = Cat1.objects.create(name="Transport", owner=self.user_a)
        self.c2_a = Cat2.objects.create(name="Bus", parent=self.c1, owner=self.user_a)
        self.c2_b = Cat2.objects.create(name="Train", parent=self.c1, owner=self.user_a)
        
        # A second Cat1 to test isolation
        self.c1_other = Cat1.objects.create(name="Food", owner=self.user_a)
        self.c2_food = Cat2.objects.create(name="Groceries", parent=self.c1_other, owner=self.user_a)

        self.tx = Transaction.objects.create(
            account_id=self.acc_a,
            value_amt=50.00,
            date_posted=self.acc_a.date_open,
            description="Test Category AJAX",
            owner=self.user_a
        )
        self.client.login(email='owner@example.com', password='secret')

    def test_update_cat1_resets_cat2(self):
        """Selecting a new Cat1 should save it and nullify Cat2."""
        # Pre-set a Cat2
        self.tx.cat1 = self.c1_other
        self.tx.cat2 = self.c2_food
        self.tx.save()

        url = reverse('budgetdb:update_transaction_category')
        response = self.client.post(url, {
            'transaction_id': self.tx.id,
            'cat_level': 1,
            'category_id': self.c1.id
        })

        self.assertEqual(response.status_code, 200)
        self.tx.refresh_from_db()
        self.assertEqual(self.tx.cat1, self.c1)
        self.assertIsNone(self.tx.cat2, "Cat2 should be reset when Cat1 changes")

    def test_get_cat2_options_filtering(self):
        """API should only return Cat2 objects belonging to the selected Cat1."""
        url = reverse('budgetdb:get_cat2_options')
        response = self.client.get(url, {'cat1_id': self.c1.id})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Should find Bus and Train, but NOT Groceries
        options = [opt['name'] for opt in data['options']]
        self.assertIn("Bus", options)
        self.assertIn("Train", options)
        self.assertNotIn("Groceries", options)

    def test_save_cat2_directly(self):
        """Selecting a Cat2 should save without affecting Cat1."""
        self.tx.cat1 = self.c1
        self.tx.save()

        url = reverse('budgetdb:update_transaction_category')
        response = self.client.post(url, {
            'transaction_id': self.tx.id,
            'cat_level': 2,
            'category_id': self.c2_a.id
        })

        self.tx.refresh_from_db()
        self.assertEqual(self.tx.cat2, self.c2_a)
        self.assertEqual(self.tx.cat1, self.c1)