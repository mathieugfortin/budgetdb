# conftest.py
import pytest
from datetime import date
from crum import impersonate
from budgetdb.models import Account, AccountHost, Currency, Preference, Cat1, Cat2, CatType

@pytest.fixture
def base_assets(db, users):
    """Sets up the foundational objects (Currency, Host, Preferences)"""
    owner = users['owner']
    with impersonate(owner):
        cad = Currency.objects.create(name="Canadian Dollar", symbol="$", priority=1)
        
        Preference.objects.create(
            user=owner,
            slider_start=date(2026, 1, 1),
            slider_stop=date(2026, 12, 31),
            currency_prefered=cad
        )
        
        host = AccountHost.objects.create(name="RBC", owner=owner)
        
    return {'cad': cad, 'host': host}

@pytest.fixture
def hierarchy(db, users, base_assets):
    """Sets up the full complex Account and Category structure."""
    owner = users['owner']
    friend = users['friend']
    host = base_assets['host']
    cad = base_assets['cad']
    
    with impersonate(owner):
        # --- Accounts ---
        acc_a = Account.objects.create(
            name="account a", account_host=host, currency=cad, owner=owner,
            ofx_acct_id='1234', ofx_org='orga', date_open=date(2026, 1, 1)
        )
        acc_a.users_admin.add(friend)

        # --- Categories ---
        cat_type = CatType.objects.create(name="catType A", owner=owner)
        
        # Create Cat1s
        c1a = Cat1.objects.create(name="cat1 A", owner=owner, cattype=cat_type)
        c1b = Cat1.objects.create(name="cat1 B", owner=owner, cattype=cat_type)
        
        # Create Cat2s
        c2a1 = Cat2.objects.create(name="cat2 A1", cat1=c1a, cattype=cat_type, owner=owner)
        c2a2 = Cat2.objects.create(name="cat2 A2", cat1=c1a, cattype=cat_type, owner=owner)

    return {
        'acc_a': acc_a,
        'cat1_a': c1a,
        'cat2_a1': c2a1,
        'cat_type': cat_type
    }