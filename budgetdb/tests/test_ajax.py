# test_ajax.py
import pytest
from django.urls import reverse
from django.conf import settings
from budgetdb.tests.base import BudgetBaseTestCase, BudgetBaseTestCase2
from decimal import Decimal
from crum import impersonate,get_current_user
from budgetdb.models import Transaction, Cat1, Cat2
import json
from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY
from django.conf import settings

@pytest.mark.django_db
class TestTransactionToggle_feature():
    def _get_urls(self):
        return {
            'receipt': reverse('budgetdb:togglereceipttransaction_json'),
            'verify': reverse('budgetdb:toggleverifytransaction_json')
        }

    def post_toggle(self, client, url, pk):
        return client.post(
            url, 
            {'transaction_id': pk},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

    def test_toggle_updates_database(self, client, user_a, acc_a, host_1, cad):
        urls = self._get_urls()
        client.force_login(user_a)
        with impersonate(user_a):
            tx = Transaction.objects.create(
                description="Toggle Test",
                receipt=False,
                verified=False,
                account_source=acc_a,
                amount_actual=Decimal('100.00'),
                date_actual=acc_a.date_open,
                currency=cad,
            )
   
        # receipt logic
        response = self.post_toggle(client, urls['receipt'], tx.id)
        assert response.status_code == 200
        tx.refresh_from_db()
        assert tx.receipt is True

        response = self.post_toggle(client, urls['receipt'], tx.id)
        assert response.status_code == 200
        tx.refresh_from_db()
        assert tx.receipt is False

        # Verified logic
        assert self.post_toggle(client, urls['verify'], tx.id).status_code == 200
        tx.refresh_from_db()
        assert tx.verified is True

        assert self.post_toggle(client, urls['verify'], tx.id).status_code == 200
        tx.refresh_from_db()
        assert tx.verified is False

    def test_toggle_unauthenticated(self, client, user_a, acc_a, cad):
        """Security: Anonymous users should get 401."""
        urls = self._get_urls()
        with impersonate(user_a):
            tx = Transaction.objects.create(
                description="Anon Test",
                receipt=False,
                verified=False,
                account_source=acc_a,
                amount_actual=Decimal('10.00'),
                date_actual=acc_a.date_open,
                currency=cad,
            )

        # receipt
        response = self.post_toggle(client, urls['receipt'], tx.id)
        assert response.status_code == 401
        tx.refresh_from_db()
        assert tx.receipt is False
        # Verified logic
        assert self.post_toggle(client, urls['verify'], tx.id)
        assert response.status_code == 401
        tx.refresh_from_db()
        assert tx.verified is False

    def test_toggle_receipt_invalid_id(self, client, user_a):
        """Edge Case: Sending an ID that doesn't exist."""
        urls = self._get_urls()
        client.force_login(user_a)

        # receipt
        response = self.post_toggle(client, urls['receipt'], 99999)
        assert response.status_code == 404
        
        # Verified logic
        response = self.post_toggle(client, urls['verify'], 99999)
        assert response.status_code == 404

    def test_toggle_receipt_by_impostor(self, client, user_a, user_bad, acc_a, cad):
        # User bad should not be able to toggle User A's transaction
        urls = self._get_urls()
        with impersonate(user_a):
            tx = Transaction.objects.create(
                description="Toggle Test",
                receipt=False,
                account_source=acc_a,
                amount_actual=Decimal('100.00'),
                date_actual=acc_a.date_open,
                currency=cad,
            )

        with impersonate(user_bad):
            client.force_login(user_bad)

            # toggle receipt
            response = self.post_toggle(client, urls['receipt'], tx.id)
            assert response.status_code == 401
            tx.refresh_from_db()
            assert tx.receipt is False # impostor should not toggle the receipt
            # toggle verified
            response = self.post_toggle(client, urls['verify'], tx.id)
            assert response.status_code == 401
            tx.refresh_from_db()
            assert tx.verified is False # impostor should not toggle the receipt


@pytest.mark.django_db
class Test_TransactionCategoryAJAXTests_feature():
    def test_update_cat1_resets_cat2(self, client, user_a, tx_a_cata, cat1_b):
        """Selecting a new Cat1 should save it and nullify Cat2."""
        client.force_login(user_a)
        url = reverse('budgetdb:update_transaction_category')

        response = client.post(url, {
            'transaction_id': tx_a_cata.id,
            'cat_level': 1,
            'category_id': cat1_b.id
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest') # AJAX call

        assert response.status_code == 200
        tx_a_cata.refresh_from_db()
        assert tx_a_cata.cat1 == cat1_b # cat1 is updated      
        assert tx_a_cata.cat2 == None # cat2 is empty

    def test_update_cat2(self, client, user_a, tx_a_cata, cat1_a, cat2_a2):
        """Selecting a new Cat1 should save it and nullify Cat2."""
        client.force_login(user_a)
        url = reverse('budgetdb:update_transaction_category')

        response = client.post(url, {
            'transaction_id': tx_a_cata.id,
            'cat_level': 2,
            'category_id': cat2_a2.id
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest') # AJAX call

        assert response.status_code == 200
        tx_a_cata.refresh_from_db()
        assert tx_a_cata.cat1 == cat1_a # cat1 hasn't changed      
        assert tx_a_cata.cat2 == cat2_a2 # cat2 is updated

    def test_cat2_admin_list_json_filtering(self, client, user_a, cat1_a, cat2_a1, cat2_a2, cat2_b1):
        """API should only return Cat2 objects belonging to the selected Cat1."""
        client.force_login(user_a)
        url = reverse('budgetdb:cat2_admin_list_json')
        response = client.get(url, {
            'cat1_id': cat1_a.id
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should find Bus and Train, but NOT Groceries
        cat2s = [opt['name'] for opt in data['cat2s']]

        assert cat2_a1.name in cat2s
        assert cat2_a2.name in cat2s
        assert cat2_b1.name not in cat2s

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

    def test_cat2_admin_list_json_filtering(self):
        """API should only return Cat2 objects belonging to the selected Cat1."""
        self.client.force_login(self.user_a)
        url = reverse('budgetdb:cat2_admin_list_json')
        response = self.client.get(url, {
            'cat1_id': self.cat1_a.id
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Should find Bus and Train, but NOT Groceries
        cat2s = [opt['name'] for opt in data['cat2s']]
        self.assertIn(self.cat2_a1.name, cat2s)
        self.assertIn(self.cat2_a2.name, cat2s)
        self.assertNotIn(self.cat2_b1.name, cat2s)

    def test_save_cat2_directly(self):
        """Selecting a Cat2 should save without affecting Cat1."""
        self.client.force_login(self.user_a)
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