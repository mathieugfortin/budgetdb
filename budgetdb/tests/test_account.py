import datetime
from datetime import date
import pytest

from django.test import TestCase
from django.utils import timezone
from django.test.client import Client

from budgetdb.models import *
from django.core.management import call_command

@pytest.fixture
def get_current_user():
    return 1


class AccountTests(TestCase):
    user = None
    account_host = None
    client = None

    def setUp(self):
        # Load fixtures
        self.client = Client()
        self.client.force_login(User.objects.get_or_create(email='1@1.me')[0])
        
        self.account_host = AccountHost(name='AccountHost1',owner=self.user)
        self.account_host.save()
                   #call_command('loaddata', 'budgetdb/tests/fixtures/user.json', verbosity=0)
        #call_command('loaddata', 'budgetdb/tests/fixtures/currency.json', verbosity=0)
        #call_command('loaddata', 'budgetdb/tests/fixtures/permissions.json', verbosity=0)
        #call_command('loaddata', 'budgetdb/tests/fixtures/accounthost.json', verbosity=0)

    #fixtures = ["budgetdb/tests/fixtures/user.json"]
    #fixtures = ["budgetdb/tests/fixtures/permissions.json"]
    #fixtures = ["budgetdb/tests/fixtures/currency.json"]
    #fixtures = ["budgetdb/tests/fixtures/accounthost.json"]

    def test_Account_Create(self):
        owner = User.objects.get(first_name='Him')
        owner.save()
        c = Currency.objects.get(name='Canadian')
        a1 = Account(account_host=ah, owner=owner, currency=c)
        a1.save()
        self.assertTrue(a1.account_host.name=='AccountHost1')