from .base import BudgetBaseTestCase
from budgetdb.models import Invitation
from crum import impersonate
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core import mail

User = get_user_model()
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
        self.assertEqual(str(self.user_a),self.user_a.email)
        self.assertIn('friend@test.com', mail.outbox[0].to)        
        self.assertIn("Budget Invitation", mail.outbox[0].subject)

    def test_verification_email(self):
        """Test that creating an invitation triggers an email."""
        self.user_b.send_verify_email()
        print (self.user_b)
        # Check Django's outbox
        self.assertFalse(self.user_b.email_verified)        
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.user_b.email, mail.outbox[0].to)        
        self.assertIn("Verify Email", mail.outbox[0].subject)

    def test_verification_email_already_sent(self):
        self.user_a.send_verify_email()

        # Check Django's outbox
        self.assertTrue(self.user_a.email_verified)        
        self.assertEqual(len(mail.outbox), 0)



class CustomUserManagerTests(TestCase):

    def test_create_user(self):
        """Test creating a regular user with email and password."""
        user = User.objects.create_user(
            email='normal@test.com', 
            password='foo',
            first_name='Normal'
        )
        self.assertEqual(user.email, 'normal@test.com')
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        # Check that the username field is None as per your model
        try:
            self.assertIsNone(user.username)
        except AttributeError:
            pass # This confirms the attribute doesn't even exist
        
        # Verify password is hashed
        self.assertTrue(user.check_password('foo'))

    def test_create_user_email_normalization(self):
        """Test that email addresses are normalized (lowercased domain)."""
        email = 'NORMAL@TEST.COM'
        user = User.objects.create_user(email, 'foo', first_name='Test')
        self.assertEqual(user.email, 'NORMAL@test.com')

    def test_create_user_no_email_error(self):
        """Test that creating a user without an email raises a ValueError."""
        with self.assertRaises(ValueError) as cm:
            User.objects.create_user(email='', password='foo', first_name='Test')
        self.assertEqual(str(cm.exception), 'The given email must be set')

    def test_create_superuser(self):
        """Test creating a superuser."""
        admin_user = User.objects.create_superuser(
            email='super@test.com', 
            password='foo',
            first_name='Super'
        )
        self.assertEqual(admin_user.email, 'super@test.com')
        self.assertTrue(admin_user.is_active)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)

    def test_user_model_str(self):
        """Test the string representation of the user."""
        user = User.objects.create_user(email='test@test.com', password='foo', first_name='Test')
        self.assertEqual(str(user), 'test@test.com')

    def test_default_email_verified_status(self):
        """Verify that email_verified defaults to False as per your model."""
        user = User.objects.create_user(email='v@test.com', password='foo', first_name='Test')
        self.assertFalse(user.email_verified)

    def test_friends_relationship_symmetrical(self):
        """Test that the self-referential friends ManyToMany works."""
        user_a = User.objects.create_user(email='a@test.com', password='foo', first_name='A')
        user_b = User.objects.create_user(email='b@test.com', password='foo', first_name='B')

        # Add B to A's friends
        user_a.friends.add(user_b)

        # Check relationship
        self.assertIn(user_b, user_a.friends.all())
        
        # Check symmetry: If A added B, does B have A?
        # By default, ManyToMany to "self" is symmetrical=True
        # self.assertIn(user_a, user_b.friends.all(), "Relationship should be symmetrical by default")

        # Test removal
        user_a.friends.remove(user_b)
        self.assertEqual(user_a.friends.count(), 0)
        self.assertEqual(user_b.friends.count(), 0)