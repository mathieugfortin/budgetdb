from budgetdb.tests.base import BudgetBaseTestCase
from django.urls import reverse

class SystemHealthTest(BudgetBaseTestCase):
    
    def test_homepage_loads(self):
        """Verify the app is up, DB is connected, and ALLOWED_HOSTS is correct"""
        
        # 1. Login with the user created in BudgetBaseTestCase.setUp
        # We use the email because your custom User model uses email as the identifier.
        logged_in = self.client.login(email='owner@example.com', password='secreta')
        self.assertTrue(logged_in, "Client login failed - check user credentials in base.py")

        # 2. Hit the homepage
        # Using follow=True handles any minor redirects (like trailing slashes)
        response = self.client.get(reverse('budgetdb:home'), follow=True)

        # 3. Assertions
        # Should be 200 now that we are authenticated
        self.assertEqual(response.status_code, 200)

        # 4. Content Verification (Optional but recommended)
        # This proves the DB actually returned the data created in setUp
        self.assertContains(response, "test_user_a_Owner")
        #self.assertContains(response, "RBC")