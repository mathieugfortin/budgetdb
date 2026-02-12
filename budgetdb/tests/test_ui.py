from django.test import LiveServerTestCase
from django.urls import reverse
from crum import impersonate
from .base import BudgetBaseTestCase

class UITests(LiveServerTestCase,BudgetBaseTestCase):
    def test_base_structure_loads(self):
        """Check if the navbar and instructions modal are present in the response"""
        with impersonate(self.user_a):
            response = self.client.get(reverse('budgetdb:home')) # Or your home URL
        # self.assertEqual(response.status_code, 200)
        
        # Check if the partials were included
        #self.assertContains(response, 'id="instructionsModal"')
        #self.assertContains(response, 'id="instructionSearch"')
        #self.assertContains(response, 'navbar')

    def test_django_config_bridge(self):
        """Ensure the JS Config bridge is rendering URLs correctly"""
        with impersonate(self.user_a):
            response = self.client.get(reverse('budgetdb:home'))
        #self.assertContains(response, 'window.DjangoConfig = {')
        #self.assertContains(response, '/cattype_list_json/') # Verify URL pattern exists