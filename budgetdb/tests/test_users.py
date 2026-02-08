from .base import BudgetBaseTestCase
from django.core import mail
from budgetdb.models import Invitation
from crum import impersonate

class UserTests(BudgetBaseTestCase):
    def test_invitation_email(self):
        """Test that creating an invitation triggers an email."""
        with impersonate(self.user_a):
            invite = Invitation.objects.create(
                email="friend@test.com",
                owner=self.user_a
            )
        invite.send_invite_email()



        # Check Django's outbox
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('friend@test.com', mail.outbox[0].to)        
        self.assertIn("Budget Invitation", mail.outbox[0].subject)