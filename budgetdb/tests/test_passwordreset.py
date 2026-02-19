from .base import BudgetBaseTestCase
from budgetdb.models import Invitation
from crum import impersonate
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse

User = get_user_model()

class PasswordResetTest(BudgetBaseTestCase):
    def test_password_reset_email_sent(self):
        response = self.client.post(reverse('password_reset'), {'email': self.user_b.email})
        self.assertEqual(response.status_code, 302) # Redirect to 'done' page
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("passwort reset email", mail.outbox[0].body)
        # Check if the correct template was used
        self.assertTemplateUsed(response, 'registration/password_reset_subject.txt') 
        self.assertTemplateUsed(response, 'registration/password_reset_email.html')
        self.assertTemplateUsed(response, 'registration/password_reset_email.html')


